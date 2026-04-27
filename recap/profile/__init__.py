from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
)
from recap.profile.forms import EditProfileForm
from flask_login import current_user, login_user, logout_user, login_required
import json
import sqlalchemy as sa
from recap import db
from recap.models import User, Article
from recap.config import Config
from recap.aiapi_helper import AiApiHelper

bp = Blueprint('profile', __name__)


# ---------------------------------------------------------------------------
# Taxonomy helpers
# ---------------------------------------------------------------------------

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
            # Cap at 8 sub-cats to avoid token bloat while keeping signal density
            subcats_str = ", ".join(subcats[:8])
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


@bp.route('/user/<username>')
@login_required
def user(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    page = request.args.get('page', 1, type=int)

    #get_articles(self,page=1, per_page=2)
    articles_paginator = current_user.get_articles(page=page, per_page=Config.ARTICLES_PER_PAGE)
    articles = articles_paginator.items
    next_url = url_for('profile.user',username=user.username, page=articles_paginator.next_num) \
        if articles_paginator.has_next else None
    prev_url = url_for('profile.user',username=user.username, page=articles_paginator.prev_num) \
        if articles_paginator.has_prev else None
    
    # list grouping of categories for article for the given user
    groupings = current_user.get_categories()

    return render_template('profile/user.html', user=user, articles=articles,
                           next_url=next_url, prev_url=prev_url,  groupings=groupings)


@bp.route('/edit_profile', methods=['GET', 'POST'])

@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.phone = form.phone.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('profile.edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.phone.data = current_user.phone
        form.email.data = current_user.email
    return render_template('profile/edit_profile.html', title='Edit Profile',
                           form=form)

@bp.route('/organize_taxonomy', methods=['GET'])
@login_required
def organize_taxonomy():
    """
    Organize and suggest improvements to the user's content categories using AI.

    Uses a richer context that includes article counts and aggregated sub-categories
    so the AI can make better merge decisions — especially for small (1-3 article)
    categories whose names alone don't reveal whether they overlap.

    Returns:
        Rendered template with current categories, suggested new categories,
        category mappings, and a description of the changes.
    """
    # Get current user categories
    categories = current_user.get_categories()

    # Build enriched context: counts + aggregated sub-categories per category
    context_string = build_rich_organize_context(current_user.id)

    # Prompt explicitly targets small categories for merging
    PROMPT = (
        "Can you recommend a consolidated category list? "
        "Merge similar or related categories, especially small ones with 1-3 articles. "
        "Keep Artificial Intelligence and Software Architecture as separate categories. "
        "Keep category names concise and understandable to a human reader."
    )
    FORMAT = """Respond in a structured JSON message, mapping old categories to new categories. Can you also explain what topics changed as a single description element in the JSON. The description should be concise and understandable to a human reader. The final structure must be formatted in this structure:
        {\r\n    \"description\": \"A summary of the changes to the topics.\",\r\n    \"mappings\": [\r\n        {\r\n            \"new_category\": \"new_category_value\",\r\n            \"old_category\": \"old_category_value\"\r\n        },\r\n        {\r\n            \"new_category\": \"new_category_value\",\r\n            \"old_category\": \"old_category_value\"\r\n        }\r\n    ],\r\n    \"ref_key\": \"2\"\r\n}
        """
    
    # Get AI suggestions
    json_response = AiApiHelper.PerformTask(
        context_string, 
        PROMPT, 
        FORMAT, 
        current_user.id
    )
    
    # Process AI response
    description = json_response.get('description', '')
    mappings = json_response.get('mappings', [])
    
    # Create category mapping and compute projected article counts for each new category
    category_mapping = create_category_mapping(mappings)
    current_counts = {cat.category: cat.count for cat in categories}
    suggested_counts = {}
    for old, new in category_mapping.items():
        suggested_counts[new] = suggested_counts.get(new, 0) + current_counts.get(old, 0)
    # Sort descending by count, same order as current categories
    new_categories = sorted(suggested_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Store mapping in session for later use
    session['category_mapping'] = category_mapping
    
    return render_template(
        "profile/organize_taxonomy.html",
        title='Organize Taxonomy',
        categories=categories,
        suggested=new_categories,
        description=description,
        category_mapping=category_mapping
    )

@bp.route('/apply_taxonomy', methods=['POST'])
@login_required
def apply_taxonomy():
    """
    Apply the suggested category changes to all articles.
    Updates article categories based on the mapping stored in session.
    """
    # Get category mapping from session
    category_mapping = session.get('category_mapping')
    if not category_mapping:
        flash('No category mapping found. Please generate suggestions first.')
        return redirect(url_for('profile.organize_taxonomy'))
    
    # Update categories for all articles
    for old_category, new_category in category_mapping.items():
        # Find all articles with the old category
        articles = Article.query.filter_by(
            user_id=current_user.id,
            category=old_category
        ).all()
        
        # Update each article's category
        for article in articles:
            article.category = new_category
            db.session.add(article)
    
    # Commit all changes
    db.session.commit()
    
    # Clear the mapping from session
    session.pop('category_mapping', None)
    
    flash('Categories have been updated successfully.')
    return redirect(url_for('profile.user', username=current_user.username))

@bp.route('/user/<username>/suggest_splits', methods=['GET'])
@login_required
def suggest_splits(username):
    """
    Phase 2: For each category that exceeds *threshold* articles, ask the AI to
    split it into 2-4 meaningful sub-groups and store the per-article assignments
    in the session for preview/apply.

    Query parameters:
        threshold (int, default 12): minimum article count to consider for splitting
    """
    threshold = request.args.get('threshold', 12, type=int)

    categories = current_user.get_categories()
    large_categories = [(cat, count) for cat, count in categories if count >= threshold]

    if not large_categories:
        flash(f'No categories exceed {threshold} articles — nothing to split.')
        return redirect(url_for('profile.user', username=current_user.username))

    SPLIT_PROMPT = (
        "Split these articles into 2-4 distinct, meaningful groups based on their themes. "
        "Name each group clearly (2-4 words). "
        "Assign every article to exactly one group."
    )
    SPLIT_FORMAT = (
        'Respond with JSON in this exact structure:\n'
        '{\n'
        '  "description": "Brief rationale for the groupings",\n'
        '  "assignments": [\n'
        '    {"article_id": 42, "new_category": "Group Name"},\n'
        '    {"article_id": 43, "new_category": "Group Name"}\n'
        '  ]\n'
        '}'
    )

    suggestions = {}
    for category_name, count in large_categories:
        article_rows = db.session.execute(
            sa.select(Article.id, Article.title, Article.sub_categories)
            .where(Article.user_id == current_user.id)
            .where(Article.category == category_name)
            .order_by(Article.id)
        ).all()

        context = build_split_context(category_name, article_rows)
        result = AiApiHelper.PerformTask(context, SPLIT_PROMPT, SPLIT_FORMAT, current_user.id)

        if result and 'assignments' in result:
            # Flatten to {article_id_str: new_category} for session storage
            assignments = {
                str(a['article_id']): a['new_category']
                for a in result['assignments']
                if 'article_id' in a and 'new_category' in a
            }
            # Compute projected sub-category counts for preview
            sub_counts = {}
            for new_cat in assignments.values():
                sub_counts[new_cat] = sub_counts.get(new_cat, 0) + 1

            suggestions[category_name] = {
                'original_count': count,
                'description': result.get('description', ''),
                'assignments': assignments,
                'sub_counts': sorted(sub_counts.items(), key=lambda x: x[1], reverse=True),
            }

    if not suggestions:
        flash('AI did not return usable split suggestions. Try again.')
        return redirect(url_for('profile.user', username=current_user.username))

    # Store flat per-article assignments in session keyed by article_id string
    session['split_assignments'] = {
        cat: data['assignments']
        for cat, data in suggestions.items()
    }

    return render_template(
        'profile/suggest_splits.html',
        title='Split Large Categories',
        suggestions=suggestions,
        threshold=threshold,
    )


@bp.route('/apply_splits', methods=['POST'])
@login_required
def apply_splits():
    """
    Phase 2: Apply the per-article category reassignments stored in the session
    by the suggest_splits route.

    Each entry in split_assignments is {str(article_id): new_category}.
    Only articles owned by the current user are updated (ownership check).
    """
    split_assignments = session.get('split_assignments')
    if not split_assignments:
        flash('No split assignments found. Please generate suggestions first.')
        return redirect(url_for('profile.user', username=current_user.username))

    updated_count = 0
    for _category_name, assignments in split_assignments.items():
        for article_id_str, new_category in assignments.items():
            article = db.session.get(Article, int(article_id_str))
            if article and article.user_id == current_user.id:
                article.category = new_category
                db.session.add(article)
                updated_count += 1

    db.session.commit()
    session.pop('split_assignments', None)

    flash(f'Split complete — {updated_count} articles reassigned.')
    return redirect(url_for('profile.user', username=current_user.username))


def create_category_mapping(mappings):
    """
    Convert a list of category mappings to a dictionary where keys are old categories
    and values are new categories.

    Args:
        mappings (list): List of dictionaries containing 'old_category' and 'new_category' pairs

    Returns:
        dict: Dictionary mapping old categories to new categories
    """
    return {mapping['old_category']: mapping['new_category'] for mapping in mappings}


@bp.route('/settings/api-token', methods=['GET', 'POST'])
@login_required
def api_token():
    """Display and optionally regenerate the current user's API token."""
    if request.method == 'POST':
        import secrets
        current_user.api_token = secrets.token_urlsafe(32)
        db.session.commit()
        flash('API token regenerated.')
        return redirect(url_for('profile.api_token'))

    token = current_user.get_or_create_api_token()
    return render_template('profile/api_token.html', title='API Token', token=token)
        