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
        Rendered template with current categories, suggested new categories,
        category mappings, and a description of the changes.
    """
    # Get current user categories
    categories = current_user.get_categories()
    
    # Prepare AI request context - using a single string join operation
    categories_names = sorted(category[0] for category in categories)
    context_string = f"I am using this taxonomy to categorize content: {', '.join(categories_names)}."
    
    # Define AI prompts as constants to avoid string recreation
    PROMPT = "Can you recommend a category list, consolidating similar categories? However, keep Artificial Intelligence and Software Architecture. Keep categories concise and understandable to a human reader."
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
        