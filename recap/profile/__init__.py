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
    description = json_response['description']
    mappings = json_response['mappings']
    
    # Create category mapping and get new categories in a single pass
    category_mapping = create_category_mapping(mappings)
    new_categories = list(set(category_mapping.values()))
    
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
        