import json
from datetime import datetime, timezone

import sqlalchemy as sa

from .state import ArticleData, Cluster, SynthesisState

SYNTHESISE_PROMPT = (
    "Write 2-3 sentences capturing the key insight or theme from these articles. "
    "Be specific — name concepts, technologies, or ideas, not just 'several articles about X'."
)
SYNTHESISE_FORMAT = 'Respond with JSON: {"narrative": "2-3 sentence insight"}'

QUALITY_PROMPT = (
    "Review this weekly digest email. "
    "Approve if the narratives are specific and insightful, not generic. "
    "Request retry if any narrative is vague, repetitive, or just restates article titles."
)
QUALITY_FORMAT = (
    "Respond with JSON:\n"
    '{"verdict": "approved or retry", '
    '"notes": "if retry: specific improvement instructions; if approved: empty string"}'
)

LABEL_PROMPT = "Give this group of articles a concise thematic label (2-4 words)."
LABEL_FORMAT = 'Respond with JSON: {"label": "short theme name"}'


def _recap_detail_url(article_id: int) -> str:
    from recap.config import Config

    host = Config.TASK_SERVER_NAME
    scheme = "http" if host.startswith("localhost") or host.startswith("127.") else "https"
    return f"{scheme}://{host}/{article_id}/show"


def _to_article_data(article) -> ArticleData:
    key_topics = []
    if article.key_topics:
        try:
            key_topics = json.loads(article.key_topics)
        except (json.JSONDecodeError, TypeError):
            pass
    return {
        "id": article.id,
        "title": article.title or "",
        "summary": article.summary or "",
        "category": article.category or "",
        "key_topics": key_topics,
        "url_path": article.url_path,
        "recap_url": _recap_detail_url(article.id),
        "is_read": article.is_read,
        "embedding": [float(x) for x in article.embedding] if article.embedding is not None else None,
    }


def _cluster_by_category(articles: list) -> list[Cluster]:
    groups: dict[str, list] = {}
    for article in articles:
        cat = article.get("category") or "Uncategorised"
        groups.setdefault(cat, []).append(article)
    return [{"label": cat, "articles": arts, "narrative": ""} for cat, arts in groups.items()]


def _label_cluster(articles: list) -> str:
    # Single-article clusters: use the existing category rather than asking the
    # model to infer a theme from one title — it hallucinates unrelated labels.
    if len(articles) == 1 and articles[0].get("category"):
        return articles[0]["category"]

    from recap.aiapi_helper import AiApiHelper

    titles = "\n".join(f"- {a['title']}" for a in articles[:10])
    result = AiApiHelper.PerformTask(titles, LABEL_PROMPT, LABEL_FORMAT, "system")
    return result.get("label", "Mixed Topics") if result else "Mixed Topics"


def _cluster_by_embedding(articles: list) -> list[Cluster]:
    try:
        import numpy as np
        from sklearn.cluster import AgglomerativeClustering
    except ImportError:
        return _cluster_by_category(articles)

    embedded = [a for a in articles if a.get("embedding") is not None]
    unembedded = [a for a in articles if a.get("embedding") is None]

    if len(embedded) < 2:
        return _cluster_by_category(articles)

    embeddings = np.array([a["embedding"] for a in embedded])
    # Target ~2 articles per cluster so labels have enough context to be meaningful.
    # min(5) caps visual clusters; max(1) avoids n_clusters=0 for tiny sets.
    n_clusters = min(5, max(1, len(embedded) // 2))
    labels = AgglomerativeClustering(n_clusters=n_clusters).fit_predict(embeddings)

    groups: dict[int, list] = {}
    for i, article in enumerate(embedded):
        groups.setdefault(int(labels[i]), []).append(article)

    if unembedded:
        first_key = next(iter(groups))
        groups[first_key].extend(unembedded)

    return [{"label": _label_cluster(arts), "articles": arts, "narrative": ""} for arts in groups.values()]


def _build_cluster_context(cluster: dict, quality_notes: str = "") -> str:
    lines = [f"Theme: {cluster['label']}", ""]
    for a in cluster["articles"]:
        lines.append(f"Title: {a['title']}")
        if a.get("summary"):
            lines.append(f"Summary: {a['summary']}")
        if a.get("key_topics"):
            lines.append(f"Topics: {', '.join(a['key_topics'][:5])}")
        lines.append("")
    context = "\n".join(lines).strip()
    if quality_notes:
        context += f"\n\nImprovement notes from previous attempt: {quality_notes}"
    return context


def _render_plain_text(user_name: str, week_start, clusters: list, article_count: int) -> str:
    lines = [
        f"Your Recap — Week of {week_start.strftime('%B %d, %Y')}",
        f"Hi {user_name}, here's what you read this week ({article_count} articles).",
        "",
    ]
    for cluster in clusters:
        lines.append(f"## {cluster['label']}")
        if cluster.get("narrative"):
            lines.append(cluster["narrative"])
        lines.append("")
        for a in cluster["articles"]:
            lines.append(f"  - {a['title']}")
            lines.append(f"    {a['recap_url']}")
        lines.append("")
    lines += ["---", "You're receiving this because you use Recap."]
    return "\n".join(lines)


# ── Graph nodes ───────────────────────────────────────────────────────────────


def gather(state: SynthesisState) -> SynthesisState:
    from recap import db
    from recap.models import Article

    articles = (
        db.session.execute(
            sa.select(Article)
            .where(Article.user_id == state["user_id"])
            .where(Article.created >= state["week_start"])
            .where(Article.created <= state["week_end"])
            .where(Article.classified.isnot(None))
            .order_by(Article.category, Article.created.desc())
        )
        .scalars()
        .all()
    )

    state["articles"] = [_to_article_data(a) for a in articles]
    return state


def assess(state: SynthesisState) -> SynthesisState:
    count = len(state["articles"])
    if count < 3:
        state["skip_reason"] = f"Only {count} article(s) this week — skipping digest."
        return state

    embedded = sum(1 for a in state["articles"] if a.get("embedding") is not None)
    state["clustering_strategy"] = "embedding" if count > 0 and embedded / count >= 0.8 else "category"
    return state


def cluster(state: SynthesisState) -> SynthesisState:
    if state.get("clustering_strategy") == "embedding":
        state["clusters"] = _cluster_by_embedding(state["articles"])
    else:
        state["clusters"] = _cluster_by_category(state["articles"])
    return state


def synthesise(state: SynthesisState) -> SynthesisState:
    from recap.aiapi_helper import AiApiHelper

    quality_notes = state.get("quality_notes", "")
    for cluster_obj in state["clusters"]:
        context = _build_cluster_context(cluster_obj, quality_notes)
        result = AiApiHelper.PerformTask(context, SYNTHESISE_PROMPT, SYNTHESISE_FORMAT, state["user_id"])
        cluster_obj["narrative"] = result.get("narrative", "") if result else ""
    return state


def compose(state: SynthesisState) -> SynthesisState:
    from flask import render_template

    state["digest_html"] = render_template(
        "email/weekly_digest.html",
        user_name=state["user_name"],
        week_start=state["week_start"],
        clusters=state["clusters"],
        article_count=len(state["articles"]),
    )
    state["digest_text"] = _render_plain_text(
        state["user_name"],
        state["week_start"],
        state["clusters"],
        len(state["articles"]),
    )
    return state


def quality_check(state: SynthesisState) -> SynthesisState:
    from recap.aiapi_helper import AiApiHelper

    if state.get("retry_count", 0) >= 2:
        state["quality_verdict"] = "best_effort"
        return state

    result = AiApiHelper.PerformTask(
        state.get("digest_text", ""),
        QUALITY_PROMPT,
        QUALITY_FORMAT,
        state["user_id"],
    )
    verdict = result.get("verdict", "approved") if result else "approved"
    if verdict not in ("approved", "retry"):
        verdict = "approved"

    state["quality_verdict"] = verdict
    state["quality_notes"] = result.get("notes", "") if result else ""
    state["retry_count"] = state.get("retry_count", 0) + 1
    return state


def send_email_node(state: SynthesisState) -> SynthesisState:
    if state.get("send_email_flag"):
        from recap.config import Config
        from recap.email import send_email

        send_email(
            subject=f"Your Recap for the week of {state['week_start'].strftime('%B %d')}",
            sender=Config.MAIL_USERNAME,
            recipients=[state["user_email"]],
            text_body=state["digest_text"],
            html_body=state["digest_html"],
        )
        state["sent"] = True
    else:
        state["sent"] = False
    state["sent_at"] = datetime.now(timezone.utc)
    return state
