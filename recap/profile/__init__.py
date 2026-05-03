from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
)
from recap.profile.forms import EditProfileForm
from flask_login import current_user, login_required
import json
import sqlalchemy as sa
from recap import db, maybe_ping_aiapi
from recap.models import User, Article
from recap.config import Config
from recap.aiapi_helper import AiApiHelper
from recap.taxonomy_helpers import build_rich_organize_context, build_split_context

bp = Blueprint('profile', __name__)


@bp.route('/user/<username>')
@login_required
def user(username):
    maybe_ping_aiapi()
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
    job = current_app.task_queue.enqueue(
        'recap.tasks.organize_taxonomy_task',
        current_user.id,
        job_timeout=300,
    )
    return render_template(
        'profile/taxonomy_processing.html',
        job_id=job.id,
        result_url=url_for('profile.organize_taxonomy_result', job_id=job.id),
        retry_url=url_for('profile.organize_taxonomy'),
        title='Organising Taxonomy…',
        show_progress=False,
    )


@bp.route('/organize_taxonomy/result/<job_id>')
@login_required
def organize_taxonomy_result(job_id):
    redis = current_app.redis
    data = redis.get(f'taxonomy:organize:{job_id}')
    if not data:
        flash('Result expired or not found. Please try again.')
        return redirect(url_for('profile.user', username=current_user.username))

    json_response = json.loads(data)
    categories = current_user.get_categories()
    description = json_response.get('description', '')
    mappings = json_response.get('mappings', [])

    category_mapping = create_category_mapping(mappings)
    current_counts = {cat.category: cat.count for cat in categories}

    from_groups = {}
    for m in mappings:
        if 'new_category' in m and 'old_category' in m:
            from_groups.setdefault(m['new_category'], []).append(m['old_category'])

    suggestions = []
    suggestion_mappings = {}
    for i, (new_cat, old_cats) in enumerate(from_groups.items()):
        if len(old_cats) == 1 and old_cats[0] == new_cat:
            continue
        sid = f'merge_{i}'
        to_count = sum(current_counts.get(old, 0) for old in old_cats)
        suggestions.append({
            'id': sid,
            'type': 'merge',
            'from_categories': old_cats,
            'from_counts': {old: current_counts.get(old, 0) for old in old_cats},
            'to_category': new_cat,
            'to_count': to_count,
            'reason': description,
        })
        suggestion_mappings[sid] = {old: new_cat for old in old_cats}

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

    unchanged_cats = [c for c in current_annotated if c['type'] == 'unchanged']
    merged_results = [
        {
            'name': s['to_category'], 'count': s['to_count'], 'type': 'merged', 'merge_id': s['id'],
            'from_categories': s['from_categories'], 'from_counts': s['from_counts'],
        }
        for s in suggestions
    ]
    proposed_annotated = unchanged_cats + merged_results

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

    # Distinguish between the new form (has accepted_* fields) and old callers
    # (tests that POST with no form data).  When the new form is present we
    # apply ONLY the explicitly accepted suggestions — rejecting all is valid
    # and should result in no changes being made.
    has_suggestion_fields = any(k.startswith('accepted_') for k in request.form)

    if has_suggestion_fields:
        accepted_ids = [
            key.replace('accepted_', '')
            for key, val in request.form.items()
            if key.startswith('accepted_') and val == '1'
        ]
        if not accepted_ids:
            flash('No changes applied — all suggestions were rejected.')
            return redirect(url_for('profile.user', username=current_user.username))
        suggestion_mappings = session.get('suggestion_mappings', {})
        mapping_to_apply = {}
        for sid in accepted_ids:
            mapping_to_apply.update(suggestion_mappings.get(sid, {}))
    else:
        # Backward-compat: tests POST without accepted_* fields
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

@bp.route('/user/<username>/suggest_splits', methods=['GET'])
@login_required
def suggest_splits(username):
    threshold = request.args.get('threshold', 12, type=int)
    job = current_app.task_queue.enqueue(
        'recap.tasks.suggest_splits_task',
        current_user.id,
        threshold,
        job_timeout=600,
    )
    return render_template(
        'profile/taxonomy_processing.html',
        job_id=job.id,
        result_url=url_for('profile.suggest_splits_result', job_id=job.id),
        retry_url=url_for('profile.suggest_splits', username=current_user.username),
        title='Splitting Categories…',
        show_progress=True,
    )


@bp.route('/suggest_splits/result/<job_id>')
@login_required
def suggest_splits_result(job_id):
    redis = current_app.redis
    data = redis.get(f'taxonomy:splits:{job_id}')
    if not data:
        flash('Result expired or not found. Please try again.')
        return redirect(url_for('profile.user', username=current_user.username))

    suggestions = json.loads(data)

    if not suggestions:
        flash('AI did not return usable split suggestions. Try again.')
        return redirect(url_for('profile.user', username=current_user.username))

    suggestion_list = [
        {
            'id': f'split_{i}',
            'category': cat_name,
            'original_count': data['original_count'],
            'description': data['description'],
            'sub_counts': data['sub_counts'],
        }
        for i, (cat_name, data) in enumerate(suggestions.items())
    ]
    large_cats = {s['category']: s for s in suggestion_list}

    session['split_assignments'] = {
        f'split_{i}': suggestions[cat_name]['assignments']
        for i, cat_name in enumerate(suggestions.keys())
    }

    all_categories = current_user.get_categories()

    return render_template(
        'profile/suggest_splits.html',
        title='Split Large Categories',
        suggestion_list=suggestion_list,
        all_categories=all_categories,
        large_cats=large_cats,
        threshold=12,
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

    # Selective apply: form submits accepted_split_N=1 for each accepted suggestion.
    # When those fields are absent (e.g. tests that POST with no form data) apply all.
    has_decision_fields = any(k.startswith('accepted_') for k in request.form)
    if has_decision_fields:
        accepted_sids = [
            k[len('accepted_'):]
            for k, v in request.form.items()
            if k.startswith('accepted_') and v == '1'
        ]
        if not accepted_sids:
            flash('No splits applied — all suggestions were rejected.')
            return redirect(url_for('profile.user', username=current_user.username))
        to_apply = {sid: split_assignments[sid] for sid in accepted_sids if sid in split_assignments}
    else:
        to_apply = split_assignments

    updated_count = 0
    for _sid, assignments in to_apply.items():
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
    return {
        mapping['old_category']: mapping['new_category']
        for mapping in mappings
        if 'old_category' in mapping and 'new_category' in mapping
    }


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
        