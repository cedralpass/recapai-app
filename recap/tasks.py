import json
import time
from datetime import datetime, timezone

import sqlalchemy as sa
from flask_mail import Mail, Message
from rq import get_current_job

from recap import create_app, db
from recap.aiapi_helper import AiApiHelper
from recap.article_text import build_article_text
from recap.auth.email import send_password_reset_email
from recap.config import Config
from recap.models import Article, User

app = create_app()
app.app_context().push()
app.config["SERVER_NAME"] = Config.TASK_SERVER_NAME

SPARSE_THRESHOLD = 8
CATEGORY_CAP = 10
DEFAULT_CATEGORIES = [
    "Technology",
    "Software Engineering",
    "Artificial Intelligence",
    "Business Strategy",
    "Leadership & Management",
    "Science",
    "Design",
    "Health & Wellness",
    "Finance & Economics",
    "Culture & Society",
    "History & Politics",
    "Philosophy",
]


def _build_category_list(user_id):
    # Order by article count so the cap keeps the most-used categories.
    rows = db.session.execute(
        sa.select(Article.category, sa.func.count(Article.id).label("cnt"))
        .where(Article.user_id == user_id)
        .where(Article.category.isnot(None))
        .group_by(Article.category)
        .order_by(sa.func.count(Article.id).desc())
    ).all()
    user_categories = [cat for cat, _cnt in rows if cat]
    if len(user_categories) < SPARSE_THRESHOLD:
        merged = list(user_categories)
        for cat in DEFAULT_CATEGORIES:
            if cat not in merged:
                merged.append(cat)
        return merged[:CATEGORY_CAP]
    return user_categories[:CATEGORY_CAP]


# sample task
def example(seconds=20):
    app.logger.info("Running example Task for seconds %s ", seconds)
    job = get_current_job()
    print("Starting task")
    for i in range(seconds):
        job.meta["progress"] = 100.0 * i / seconds
        job.save_meta()
        print(i)
        time.sleep(1)
    job.meta["progress"] = 100
    job.save_meta()
    print("Task completed")


def send_password_reset_email_task(user_id):
    app.app_context().push()
    user = User.query.get(user_id)
    send_password_reset_email(user)


def classify_url(url, user_id):
    app.logger.debug("inside classify_url")
    classify_result = None
    try:
        # find article by url_ref for user
        app.logger.debug("finding article to classify for %s", url)
        article = Article.get_article_by_url_path(url, user_id)
        print(article)
        # classify artitle using  AiAPIHelper
        categories = _build_category_list(user_id)
        classify_result = AiApiHelper.ClassifyUrl(
            url, user_id, categories=categories
        )  # TODO : should be the article id, but using user-id for now
        site_down = classify_result.get("site_down")
        site_blocked = classify_result.get("site_blocked")
        # If the site is unreachable or blocking us and the article is already classified,
        # keep the existing data rather than overwriting with a URL-only guess.
        if (site_down or site_blocked) and article.classified is not None:
            if site_blocked:
                msg = f"The site at {url} is blocking our bot — your existing classification has been kept."
            else:
                msg = f"The site at {url} appears to be down — your existing classification has been kept."
            app.logger.warning(
                "classify_url: %s for already-classified article %s",
                "bot-blocked" if site_blocked else "site down",
                article.id,
            )
            app.redis.setex(f"user_flash:{user_id}", 300, msg)
            return None
        # For new articles where content couldn't be fetched, set a descriptive summary
        # and (for bot-blocked) a marked title so users understand the classification is URL-only.
        if site_down:
            classify_result["summary"] = "Site Down – Classifying by URL Only"
        elif site_blocked:
            from recap.aiapi_helper import _site_name_from_url

            classify_result["summary"] = "Bot Blocked – Classifying by URL Only"
            classify_result["blog_title"] = f"{_site_name_from_url(url)} Blocked – {url}"
        # save results to article found
        app.logger.debug("saving results to article")
        app.logger.debug(classify_result["summary"])
        save_classification_result(classify_result, article)
        text = build_article_text(article)
        if text:
            embedding = AiApiHelper.EmbedText(text)
            if embedding:
                article.embedding = embedding
                app.logger.debug("embedding generated and stored for article %s", article.id)
            else:
                app.logger.warning("embedding returned None for article %s", article.id)
        app.logger.debug("saving article")
        db.session.add(article)
        db.session.commit()
        app.logger.debug("article saved")
    except Exception as e:
        app.logger.debug("Error in Classification Service: %s", e)
    return classify_result


def save_classification_result(classify_result, article):
    article.summary = classify_result["summary"]
    article.title = classify_result["blog_title"]
    article.author_name = classify_result["author"]
    article.category = classify_result["category"]
    if "key_topics" not in classify_result.keys():
        classify_result["key_topics"] = []
    if "sub_categories" not in classify_result.keys():
        classify_result["sub_categories"] = []
    article.key_topics = json.dumps(classify_result["key_topics"])
    article.sub_categories = json.dumps(classify_result["sub_categories"])
    # set classified to datetime now in utc timezone
    article.classified = datetime.now(timezone.utc)


def organize_taxonomy_task(user_id):
    from recap.taxonomy_helpers import build_rich_organize_context

    app.logger.info("organize_taxonomy_task starting for user_id=%s", user_id)

    user = db.session.get(User, user_id)
    context_string = build_rich_organize_context(user_id)
    if user and user.taxonomy_preferences:
        context_string += f"\n\nUser preferences: {user.taxonomy_preferences}"

    PROMPT = (
        "Can you recommend a consolidated category list? "
        "Merge similar or related categories, especially small ones with 1-3 articles. "
        "Keep category names concise and understandable to a human reader."
    )
    FORMAT = (
        "Respond with JSON in this exact structure:\n"
        "{\n"
        '  "description": "A concise summary of the changes made.",\n'
        '  "mappings": [\n'
        '    {"new_category": "New Name", "old_category": "Old Name"},\n'
        '    {"new_category": "New Name", "old_category": "Old Name"}\n'
        "  ]\n"
        "}"
    )

    json_response = AiApiHelper.PerformTask(context_string, PROMPT, FORMAT, user_id)
    app.logger.info(
        "organize_taxonomy_task AI response keys: %s", list(json_response.keys()) if json_response else "empty"
    )

    if not json_response or "mappings" not in json_response:
        raise RuntimeError("AI did not return a usable taxonomy response — mappings key missing")

    job = get_current_job()
    app.redis.setex(f"taxonomy:organize:{job.id}", 3600, json.dumps(json_response))


def suggest_splits_task(user_id, threshold=12):
    from recap.taxonomy_helpers import build_split_context

    app.logger.info("suggest_splits_task starting for user_id=%s threshold=%s", user_id, threshold)

    job = get_current_job()

    rows = db.session.execute(
        sa.select(Article.category, sa.func.count(Article.id).label("cnt"))
        .where(Article.user_id == user_id)
        .where(Article.classified.isnot(None))
        .group_by(Article.category)
        .having(sa.func.count(Article.id) >= threshold)
        .order_by(sa.func.count(Article.id).desc())
    ).all()
    large_categories = [(cat, cnt) for cat, cnt in rows if cat]

    if not large_categories:
        app.redis.setex(f"taxonomy:splits:{job.id}", 3600, json.dumps({}))
        return

    user = db.session.get(User, user_id)
    user_prefs = user.taxonomy_preferences if user and user.taxonomy_preferences else None

    SPLIT_PROMPT = (
        "Split these articles into 2-4 distinct, meaningful groups based on their themes. "
        "Name each group clearly (2-4 words). "
        "Assign every article to exactly one group."
    )
    SPLIT_FORMAT = (
        "Respond with JSON in this exact structure:\n"
        "{\n"
        '  "description": "Brief rationale for the groupings",\n'
        '  "assignments": [\n'
        '    {"article_id": 42, "new_category": "Group Name"},\n'
        '    {"article_id": 43, "new_category": "Group Name"}\n'
        "  ]\n"
        "}"
    )

    total = len(large_categories)
    suggestions = {}

    for done, (category_name, count) in enumerate(large_categories):
        article_rows = db.session.execute(
            sa.select(Article.id, Article.title, Article.sub_categories, Article.summary)
            .where(Article.user_id == user_id)
            .where(Article.category == category_name)
            .order_by(Article.id)
        ).all()

        context = build_split_context(category_name, article_rows)
        if user_prefs:
            context += f"\n\nUser preferences: {user_prefs}"
        result = AiApiHelper.PerformTask(context, SPLIT_PROMPT, SPLIT_FORMAT, user_id)

        if result and "assignments" in result:
            assignments = {
                str(a["article_id"]): a["new_category"]
                for a in result["assignments"]
                if "article_id" in a and "new_category" in a
            }
            sub_counts = {}
            for new_cat in assignments.values():
                sub_counts[new_cat] = sub_counts.get(new_cat, 0) + 1

            suggestions[category_name] = {
                "original_count": count,
                "description": result.get("description", ""),
                "assignments": assignments,
                "sub_counts": sorted(sub_counts.items(), key=lambda x: x[1], reverse=True),
            }

        job.meta["progress"] = f"{done + 1} of {total} categories processed"
        job.save_meta()

    app.redis.setex(f"taxonomy:splits:{job.id}", 3600, json.dumps(suggestions))


def weekly_digest_task(user_id: int, send_email_flag: bool = False):
    from datetime import timedelta

    from langgraph.checkpoint.memory import MemorySaver

    from aiapi.agents.synthesis.graph import build_synthesis_graph
    from recap.models import DigestRun

    user = db.session.get(User, user_id)
    if not user or not user.email:
        return

    now = datetime.now(timezone.utc)
    week_start = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)

    job = get_current_job()
    run = DigestRun(
        user_id=user_id,
        week_start=week_start,
        week_end=now,
        status="running",
        job_id=job.id if job else None,
    )
    db.session.add(run)
    db.session.commit()

    initial_state = {
        "user_id": user_id,
        "user_email": user.email,
        "user_name": user.username,
        "week_start": week_start,
        "week_end": now,
        "articles": [],
        "clusters": [],
        "clustering_strategy": "category",
        "skip_reason": None,
        "retry_count": 0,
        "quality_verdict": "",
        "quality_notes": "",
        "digest_html": "",
        "digest_text": "",
        "sent": False,
        "sent_at": None,
        "send_email_flag": send_email_flag,
        "run_id": run.id,
    }

    try:
        checkpointer = MemorySaver()
        graph = build_synthesis_graph(checkpointer=checkpointer)
        thread = {"configurable": {"thread_id": f"digest:{user_id}:{week_start.date()}"}}
        final_state = graph.invoke(initial_state, config=thread)

        run.status = "completed" if final_state.get("digest_html") else "skipped"
        run.article_count = len(final_state.get("articles", []))
        run.clustering_strategy = final_state.get("clustering_strategy")
        run.skip_reason = final_state.get("skip_reason")
        run.retry_count = final_state.get("retry_count", 0)
        run.quality_verdict = final_state.get("quality_verdict")
        run.quality_notes = final_state.get("quality_notes")
        run.digest_html = final_state.get("digest_html")
        run.digest_text = final_state.get("digest_text")
        run.sent = final_state.get("sent", False)
        run.cluster_count = len(final_state.get("clusters", []))
        run.completed_at = datetime.now(timezone.utc)
        db.session.commit()
    except Exception:
        app.logger.exception("weekly_digest_task: exception for user_id=%s run_id=%s", user_id, run.id)
        run.status = "failed"
        run.completed_at = datetime.now(timezone.utc)
        db.session.commit()
        raise

    app.logger.info("weekly_digest_task: completed for user_id=%s run_id=%s", user_id, run.id)


def schedule_weekly_digests_task():
    """Coordinator: enqueue weekly_digest_task for all opted-in users.

    Triggered daily by the bash scheduler loop in initialize_render_run.sh
    (or manually via `flask digest run-now`).  Does NOT self-reschedule — the
    bash loop is the sole scheduling mechanism, which avoids dependence on
    RQ's --with-scheduler flag and its Redis lock-acquisition quirks.
    """
    import sqlalchemy as sa

    from recap.models import User

    app.logger.info("schedule_weekly_digests_task: starting coordinator run")

    users = db.session.scalars(
        sa.select(User).where(User.digest_enabled == True)  # noqa: E712
    ).all()

    app.logger.info("schedule_weekly_digests_task: enqueuing digest for %d users", len(users))
    for user in users:
        job = app.task_queue.enqueue(
            "recap.tasks.weekly_digest_task",
            user.id,
            True,  # send_email_flag
            job_timeout=1800,  # 30 min — large accounts with many articles need more time
        )
        app.logger.info(
            "schedule_weekly_digests_task: enqueued user_id=%s job_id=%s",
            user.id,
            job.id,
        )
    app.logger.info("schedule_weekly_digests_task: completed coordinator run for %d users", len(users))


def ping_aiapi():
    import urllib.request

    url = Config.RECAP_AI_API_URL.rstrip("/") + "/hello"
    app.logger.debug("ping_aiapi: pinging %s", url)
    try:
        response = urllib.request.urlopen(url, timeout=30)
        app.logger.debug("ping_aiapi: success — HTTP %s from %s", response.status, url)
    except Exception as e:
        app.logger.debug("ping_aiapi: failed — %s — url=%s", e, url)
