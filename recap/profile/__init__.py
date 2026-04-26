from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
)
from recap.profile.forms import EditProfileForm
from flask_login import current_user, login_user, logout_user, login_required
import sqlalchemy as sa
from recap import db
from recap.models import User, Article
from recap.config import Config 
from recap.aiapi_helper import AiApiHelper

bp = Blueprint('profile', __name__)

@bp.route('/user/<username>')
@login_required
def user(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    return render_template('profile/user.html', user=user)


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

    Returns:
        Rendered template with structured diff data for the new review UI.
    """
    categories = current_user.get_categories()
    categories_names = sorted(category[0] for category in categories)
    context_string = f"I am using this taxonomy to categorize content: {', '.join(categories_names)}."

    PROMPT = "Can you recommend a category list, consolidating similar categories? However, keep Artificial Intelligence and Software Architecture. Keep categories concise and understandable to a human reader."
    FORMAT = """Respond in a structured JSON message, mapping old categories to new categories. Can you also explain what topics changed as a single description element in the JSON. The description should be concise and understandable to a human reader. The final structure must be formatted in this structure:
        {\r\n    \"description\": \"A summary of the changes to the topics.\",\r\n    \"mappings\": [\r\n        {\r\n            \"new_category\": \"new_category_value\",\r\n            \"old_category\": \"old_category_value\"\r\n        },\r\n        {\r\n            \"new_category\": \"new_category_value\",\r\n            \"old_category\": \"old_category_value\"\r\n        }\r\n    ],\r\n    \"ref_key\": \"2\"\r\n}
        """

    json_response = AiApiHelper.PerformTask(context_string, PROMPT, FORMAT, current_user.id)

    description = json_response.get('description', '')
    mappings = json_response.get('mappings', [])

    # Full flat mapping (kept for backward-compat and session storage)
    category_mapping = create_category_mapping(mappings)
    current_counts = {cat.category: cat.count for cat in categories}

    # Build structured suggestions by grouping mappings by new_category.
    # A group of one where old == new is "unchanged" — skip it.
    from_groups = {}
    for m in mappings:
        from_groups.setdefault(m['new_category'], []).append(m['old_category'])

    suggestions = []
    suggestion_mappings = {}  # sid -> {old_cat: new_cat} used by apply_taxonomy
    for i, (new_cat, old_cats) in enumerate(from_groups.items()):
        if len(old_cats) == 1 and old_cats[0] == new_cat:
            continue  # truly unchanged — not a suggestion
        sid = f'merge_{i}'
        to_count = sum(current_counts.get(old, 0) for old in old_cats)
        suggestions.append({
            'id': sid,
            'type': 'merge',
            'from_categories': old_cats,
            'to_category': new_cat,
            'to_count': to_count,
            'reason': description,
        })
        suggestion_mappings[sid] = {old: new_cat for old in old_cats}

    # Annotate current categories with their change status
    merging_from = {cat for s in suggestions for cat in s['from_categories']}
    current_annotated = []
    for g in categories:
        cat_type = 'merging' if g.category in merging_from else 'unchanged'
        merge_id = next(
            (s['id'] for s in suggestions if g.category in s['from_categories']), None
        )
        current_annotated.append({
            'name': g.category,
            'count': g.count,
            'type': cat_type,
            'merge_id': merge_id,
            'is_new': g.category.startswith('New Category:'),
        })

    # Proposed taxonomy: unchanged categories + merge results
    unchanged_cats = [c for c in current_annotated if c['type'] == 'unchanged']
    merged_results = [
        {'name': s['to_category'], 'count': s['to_count'], 'type': 'merged', 'merge_id': s['id']}
        for s in suggestions
    ]
    proposed_annotated = unchanged_cats + merged_results

    # Backward-compat flat suggested list
    suggested_counts = {}
    for old, new in category_mapping.items():
        suggested_counts[new] = suggested_counts.get(new, 0) + current_counts.get(old, 0)
    new_categories = sorted(suggested_counts.items(), key=lambda x: x[1], reverse=True)

    session['category_mapping'] = category_mapping
    session['suggestion_mappings'] = suggestion_mappings

    return render_template(
        "profile/organize_taxonomy.html",
        title='Organise Taxonomy',
        categories=categories,
        suggested=new_categories,
        description=description,
        category_mapping=category_mapping,
        current_annotated=current_annotated,
        proposed_annotated=proposed_annotated,
        suggestions=suggestions,
    )

@bp.route('/apply_taxonomy', methods=['POST'])
@login_required
def apply_taxonomy():
    """
    Apply accepted taxonomy suggestions to all articles.

    The new UI submits accepted_<id>=1 for each accepted suggestion and
    accepted_<id>=0 for rejected ones.  When those fields are present we only
    apply the accepted subset.  When they are absent (e.g. older form or tests
    that POST without form data) we fall back to the full category_mapping
    stored in session.
    """
    category_mapping = session.get('category_mapping')
    if not category_mapping:
        flash('No category mapping found. Please generate suggestions first.')
        return redirect(url_for('profile.organize_taxonomy'))

    accepted_ids = [
        key.replace('accepted_', '')
        for key, val in request.form.items()
        if key.startswith('accepted_') and val == '1'
    ]

    if accepted_ids:
        suggestion_mappings = session.get('suggestion_mappings', {})
        mapping_to_apply = {}
        for sid in accepted_ids:
            mapping_to_apply.update(suggestion_mappings.get(sid, {}))
    else:
        mapping_to_apply = category_mapping

    for old_category, new_category in mapping_to_apply.items():
        articles = Article.query.filter_by(
            user_id=current_user.id,
            category=old_category
        ).all()
        for article in articles:
            article.category = new_category
            db.session.add(article)

    db.session.commit()
    session.pop('category_mapping', None)
    session.pop('suggestion_mappings', None)

    flash('Categories have been updated successfully.')
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
        