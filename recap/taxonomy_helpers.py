import json
import sqlalchemy as sa
from recap import db
from recap.models import Article


def get_categories_with_subcats(user_id):
    """
    Returns [(category_name, count, subcats_list), ...] sorted by count descending.

    subcats_list is a de-duplicated, sorted list of sub-category strings aggregated
    across every classified article in that category.  Unclassified articles and
    null sub_categories are skipped safely.
    """
    rows = db.session.execute(
        sa.select(Article.category, Article.sub_categories)
        .where(Article.user_id == user_id)
        .where(Article.classified.isnot(None))
    ).all()

    data = {}
    for cat, subcats_json in rows:
        if cat is None:
            continue
        if cat not in data:
            data[cat] = {'count': 0, 'subcats': set()}
        data[cat]['count'] += 1
        if subcats_json:
            try:
                data[cat]['subcats'].update(json.loads(subcats_json))
            except (json.JSONDecodeError, TypeError):
                pass

    return [
        (cat, d['count'], sorted(d['subcats']))
        for cat, d in sorted(data.items(), key=lambda x: x[1]['count'], reverse=True)
    ]


def build_rich_organize_context(user_id):
    """
    Build the organize_taxonomy context string enriched with article counts and
    aggregated sub-categories per category.

    Example output line:
        - Artificial Intelligence (27 articles): Deep Learning, Fine-tuning, LLM, RAG
    """
    cats = get_categories_with_subcats(user_id)
    lines = ["I am using this taxonomy to categorize content:"]
    for cat, count, subcats in cats:
        article_word = "article" if count == 1 else "articles"
        if subcats:
            subcats_str = ", ".join(subcats[:4])
            lines.append(f"- {cat} ({count} {article_word}): {subcats_str}")
        else:
            lines.append(f"- {cat} ({count} {article_word})")
    return "\n".join(lines)


def build_split_context(category_name, articles):
    """
    Build the context string for splitting a single large category.

    articles: iterable of Row(id, title, sub_categories) from a SQLAlchemy query.
    """
    lines = [
        f'Category "{category_name}" has grown large and needs splitting into smaller groups.',
        "Here are the articles with their content themes:",
        "",
    ]
    for article_id, title, subcats_json in articles:
        subcats = []
        if subcats_json:
            try:
                subcats = json.loads(subcats_json)
            except (json.JSONDecodeError, TypeError):
                pass
        subcats_str = ", ".join(subcats) if subcats else "none"
        lines.append(
            f"[id:{article_id}] {title or 'Untitled'} | themes: {subcats_str}"
        )
    return "\n".join(lines)
