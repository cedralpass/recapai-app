def build_article_text(article):
    """Build a plain-text string from article fields for embedding."""
    topics = ", ".join(article.get_key_topics_json() or [])
    subs = ", ".join(article.get_sub_categories_json() or [])
    parts = [
        article.title or "",
        article.summary or "",
        f"Category: {article.category}" if article.category else "",
        f"Sub-categories: {subs}" if subs else "",
        f"Topics: {topics}" if topics else "",
    ]
    return ". ".join(p for p in parts if p).strip()
