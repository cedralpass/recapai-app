from datetime import datetime, timezone
from urllib.parse import urlsplit

import sqlalchemy as sa
from flask import Blueprint, current_app, flash, g, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from rq import Queue, Worker
from rq.worker_registration import clean_worker_registry

from recap import db, maybe_ping_aiapi
from recap.aiapi_helper import AiApiHelper
from recap.auth.email import send_password_reset_email
from recap.auth.forms import RegistrationForm
from recap.config import Config
from recap.forms import ArticleForm
from recap.models import Article, DigestRun, User

bp = Blueprint("routes", __name__)


@bp.route("/", methods=["GET", "POST"])
@bp.route("/index", methods=["GET", "POST"])
def index():
    maybe_ping_aiapi()
    if current_user.is_authenticated:
        pending_flash = current_app.redis.get(f"user_flash:{current_user.id}")
        if pending_flash:
            flash(pending_flash.decode("utf-8"), "error")
            current_app.redis.delete(f"user_flash:{current_user.id}")
    form = ArticleForm()
    if form.validate_on_submit():
        # TODO: Validate that the form.url_path is a valid url
        article = Article(url_path=form.url_path.data, user=current_user)
        db.session.add(article)
        db.session.commit()
        # TODO: Theroy is DB is asleep and task is fired off before its woken up.
        current_app.logger.debug("launching task to classify %s for article.id %s", article.url_path, article.id)
        job = launch_task(
            name="recap.tasks.classify_url",
            description="using AI to classify url",
            url=article.url_path,
            user_id=current_user.id,
        )
        current_app.logger.debug("task launched to classify %s for article.url_path %s", job.id, article.url_path)
        session["latest_job_id"] = job.id
        flash("Your article is being classified!")
        return redirect(url_for("routes.index"))

    page = request.args.get("page", 1, type=int)

    # get_articles(self,page=1, per_page=2)
    # set articles, next_url, prev_url to None
    articles = None
    next_url = None
    prev_url = None
    category = None
    groupings = None
    if current_user.is_authenticated:
        category = request.args.get("category")
        hide_read = request.args.get("hide_read", "false") == "true"
        articles_paginator = current_user.get_articles(
            page=page, per_page=Config.ARTICLES_PER_PAGE, category=category, include_read=not hide_read
        )
        articles = articles_paginator.items

        pagination_kwargs = {"category": category}
        if hide_read:
            pagination_kwargs["hide_read"] = "true"
        next_url = (
            url_for("routes.index", page=articles_paginator.next_num, **pagination_kwargs)
            if articles_paginator.has_next
            else None
        )
        prev_url = (
            url_for("routes.index", page=articles_paginator.prev_num, **pagination_kwargs)
            if articles_paginator.has_prev
            else None
        )

        # list grouping of categories for article for the given user
        groupings = current_user.get_categories()

        latest_completed = db.session.scalar(
            sa.select(DigestRun)
            .where(DigestRun.user_id == current_user.id, DigestRun.status == "completed")
            .order_by(DigestRun.created_at.desc())
        )
        digest_card_state = "fresh" if (latest_completed and latest_completed.opened_at is None) else "empty"
        recent_bookmark_count = min(
            db.session.scalar(sa.select(sa.func.count(Article.id)).where(Article.user_id == current_user.id)) or 0,
            25,
        )

    cta_form = RegistrationForm() if current_user.is_anonymous else None
    return render_template(
        "index.html",
        title="Home Page",
        form=form,
        articles=articles,
        next_url=next_url,
        prev_url=prev_url,
        groupings=groupings,
        active_category=category,
        hide_read=hide_read if current_user.is_authenticated else False,
        cta_form=cta_form,
        digest_card_state=digest_card_state if current_user.is_authenticated else None,
        recent_bookmark_count=recent_bookmark_count if current_user.is_authenticated else 0,
    )


@bp.route("/css", methods=["GET", "POST"])
def css():
    flash("Invalid username or password")
    if "Content-Type" in request.headers.keys() and request.headers["Content-Type"] == "application/json":
        return jsonify("css")
    return render_template("css.html", title="CSS")


@bp.route("/job")
@login_required
def job():
    job = launch_task(name="recap.tasks.example", description="example", seconds=5)
    return "Job is Executing " + job.id + " its status " + job.get_status(refresh=True)


# a url for showing a job_id
@bp.route("/job/<string:id>/show")
@login_required
def job_show(id):
    job = current_app.task_queue.fetch_job(job_id=id)
    status = job.get_status(refresh=True)
    response = {"id": job.id, "status": status, "description": job.description, "meta": job.meta}
    return response


@bp.route("/add_article", methods=["GET", "POST"])
@login_required
def add_article():
    form = ArticleForm()
    if form.validate_on_submit():
        article = Article(url_path=form.url_path.data, user=current_user)
        db.session.add(article)
        db.session.commit()

        job = launch_task(
            name="recap.tasks.classify_url",
            description="using AI to classify url",
            url=article.url_path,
            user_id=current_user.id,
        )
        print(job.id)

        flash("Your article is being classified!")
        return redirect(url_for("routes.index"))
    else:
        return render_template("add_article.html", title="add_article", form=form)


@bp.route("/<int:id>/show", methods=("GET", "POST"))
@login_required
def show(id):
    article = None

    try:
        stmt = (
            sa.select(Article).where(Article.id == id, Article.user_id == current_user.id).order_by(Article.id.desc())
        )
        article = db.session.execute(stmt).scalar_one()
    except sa.exc.NoResultFound as nre:
        flash("Article not found", "error")
        print(nre)
    except Exception as ex:
        flash("General Exception", "error")
        print(ex)

    if article and not article.is_viewed:
        article.is_viewed = True
        db.session.commit()

    if "Content-Type" in request.headers.keys() and request.headers["Content-Type"] == "application/json":
        article_dict = {
            "id": article.id,
            "url_path": article.url_path,
            "summary": article.summary,
            "title": article.title,
            "author_name": article.author_name,
            "category": article.category,
            "key_topics": article.key_topics,
            "sub_categories": article.sub_categories,
        }
        return jsonify(article_dict)  # SqlAlchemy objects are not easily serialized to JSON.. have to build our own.

    prev_article = (
        Article.query.filter(
            Article.user_id == current_user.id, Article.created > article.created, Article.classified.isnot(None)
        )
        .order_by(Article.created.asc())
        .first()
    )

    next_article = (
        Article.query.filter(
            Article.user_id == current_user.id, Article.created < article.created, Article.classified.isnot(None)
        )
        .order_by(Article.created.desc())
        .first()
    )

    return render_template(
        "article/show.html",
        article=article,
        sub_categories=article.get_sub_categories_json(),
        prev_article=prev_article,
        next_article=next_article,
    )


@bp.route("/articles/<int:id>/read", methods=("GET",))
@login_required
def read_article(id):
    stmt = sa.select(Article).where(Article.id == id, Article.user_id == current_user.id)
    article = db.session.execute(stmt).scalar_one()
    if not article.is_read:
        article.is_read = True
        db.session.commit()
    return redirect(article.url_path)


@bp.route("/articles/<int:id>/toggle-read", methods=("POST",))
@login_required
def toggle_read(id):
    stmt = sa.select(Article).where(Article.id == id, Article.user_id == current_user.id)
    article = db.session.execute(stmt).scalar_one()
    article.is_read = not article.is_read
    db.session.commit()
    return redirect(request.referrer or url_for("routes.index"))


@bp.route("/<int:id>/reclassify", methods=("GET", "POST"))
@login_required
def reclassify(id):
    print("inside reclassify")
    stmt = sa.select(Article).where(Article.id == id, Article.user_id == current_user.id).order_by(Article.id.desc())
    article = db.session.execute(stmt).scalar_one()
    # current_app.logger.info("calling async Classification Service for article %s", article['url_path'])
    # recap.tasks.classify_url(url_path, g.user['id'])
    job = launch_task(
        name="recap.tasks.classify_url", description="url classification", url=article.url_path, user_id=current_user.id
    )
    print("Job is Executing " + job.id + " its status " + job.get_status(refresh=True))
    job_url = url_for("routes.job_show", id=job.id)
    flash(
        f'Article is being reclassified. Job <a href="{job_url}" class="underline font-mono text-sm">{job.id}</a> — will be classified within 20 seconds.'
    )
    # current_app.logger.info("Classification Service returned")
    return redirect(url_for("routes.index"))


@bp.route("/<int:id>/delete", methods=("GET",))
@login_required
def delete(id):
    stmt = sa.select(Article).where(Article.id == id, Article.user_id == current_user.id).order_by(Article.id.desc())
    article = db.session.execute(stmt).scalar_one()
    db.session.delete(article)
    db.session.commit()
    flash("Article is deteled")
    return redirect(url_for("routes.index"))


@bp.route("/debug/ping-status")
@login_required
def ping_status():
    return redirect(url_for("routes.health_ping_status"))


@bp.route("/health/ping-status")
@login_required
def health_ping_status():
    key = "aiapi:ping:last"
    exists = bool(current_app.redis.exists(key))
    ttl = current_app.redis.ttl(key)
    return jsonify(
        {
            "key_exists": exists,
            "ttl_seconds": ttl,
            "ai_api_url": Config.RECAP_AI_API_URL.rstrip("/") + "/hello",
        }
    )


@bp.route("/health/workers")
@login_required
def health_workers():
    conn = current_app.redis
    queue = Queue(current_app.task_queue.name, connection=conn)
    if request.args.get("clean") == "true":
        clean_worker_registry(queue)
    workers = Worker.all(connection=conn)

    worker_data = [
        {
            "name": w.name,
            "state": w.get_state(),
            "current_job_id": w.get_current_job_id(),
            "queues": w.queue_names(),
        }
        for w in workers
    ]

    return jsonify(
        {
            "workers": worker_data,
            "worker_count": len(worker_data),
            "queue": queue.name,
            "queued_jobs": queue.count,
        }
    )


@bp.route("/health/workers/clean", methods=["POST"])
@login_required
def health_workers_clean():
    conn = current_app.redis
    queue = Queue(current_app.task_queue.name, connection=conn)
    clean_worker_registry(queue)
    workers_after = Worker.all(connection=conn)
    flash(f"Registry cleaned — {len(workers_after)} active worker(s) remaining.")
    return redirect(url_for("routes.health"))


@bp.route("/health")
@login_required
def health():
    conn = current_app.redis
    queue = Queue(current_app.task_queue.name, connection=conn)
    workers = Worker.all(connection=conn)

    ping_key = "aiapi:ping:last"
    ping_data = {
        "key_exists": bool(conn.exists(ping_key)),
        "ttl_seconds": conn.ttl(ping_key),
        "ai_api_url": Config.RECAP_AI_API_URL.rstrip("/") + "/hello",
    }

    worker_data = [
        {
            "name": w.name,
            "state": w.get_state(),
            "current_job_id": w.get_current_job_id(),
        }
        for w in workers
    ]

    return render_template(
        "health.html",
        title="System Health",
        workers=worker_data,
        queue_name=queue.name,
        queued_jobs=queue.count,
        ping=ping_data,
    )


@bp.route("/search")
@login_required
def search():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip() or None
    results = []

    if q:
        query_vec = AiApiHelper.EmbedText(q)
        if query_vec:
            results = current_user.search_articles(query_vec, limit=20, category=category)

    return render_template(
        "search.html",
        query=q,
        results=results,
        active_category=category,
        categories=current_user.get_categories(),
    )


@bp.route("/digest")
@login_required
def digest():
    digest_run = db.session.scalar(
        sa.select(DigestRun)
        .where(DigestRun.user_id == current_user.id, DigestRun.status == "completed")
        .order_by(DigestRun.created_at.desc())
    )
    if digest_run is None:
        flash("No digest yet — generate one from your home page.")
        return redirect(url_for("routes.index"))
    if digest_run.opened_at is None:
        digest_run.opened_at = datetime.now(timezone.utc)
        db.session.commit()
    bookmarks_since_digest = (
        db.session.scalar(
            sa.select(sa.func.count(Article.id)).where(
                Article.user_id == current_user.id,
                Article.created > digest_run.completed_at,
            )
        )
        or 0
    )
    show_regenerate_banner = bookmarks_since_digest >= Config.DIGEST_REGENERATE_THRESHOLD
    return render_template(
        "digest.html",
        digest_run=digest_run,
        show_regenerate_banner=show_regenerate_banner,
        bookmarks_since_digest=bookmarks_since_digest,
    )


@bp.route("/digest/generate", methods=["POST"])
@login_required
def digest_generate():
    job = current_app.task_queue.enqueue(
        "recap.tasks.weekly_digest_task",
        current_user.id,
        False,
        job_timeout=600,
    )
    return jsonify({"status": "queued", "job_id": job.id})


@bp.route("/digest/<int:digest_id>/regenerate", methods=["POST"])
@login_required
def digest_regenerate(digest_id):
    digest_run = db.session.get(DigestRun, digest_id)
    if digest_run is None or digest_run.user_id != current_user.id:
        return jsonify({"error": "not found"}), 404
    job = current_app.task_queue.enqueue(
        "recap.tasks.weekly_digest_task",
        current_user.id,
        False,
        job_timeout=600,
    )
    return jsonify({"status": "queued", "job_id": job.id})


@bp.route("/digest/job/<job_id>")
@login_required
def digest_job_status(job_id):
    job = current_app.task_queue.fetch_job(job_id=job_id)
    if job is None:
        return jsonify({"status": "not_found"}), 404
    status = str(job.get_status(refresh=True))
    return jsonify({"status": status, "view_url": url_for("routes.digest")})


# TODO - understand args and kwargs better for dynamic params
def launch_task(name, description, *args, **kwargs):
    rq_job = current_app.task_queue.enqueue(name, description=description, args=args, kwargs=kwargs)
    return rq_job
