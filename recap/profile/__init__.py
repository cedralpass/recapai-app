from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
)
from recap.profile.forms import EditProfileForm
from flask_login import current_user, login_user, logout_user, login_required
import sqlalchemy as sa
from recap import db
from recap.models import User
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
    categories = current_user.get_categories()

    prompt_string = "Can you recommend a category list, consolidating similar categories? However, keep Artificial Intelligence and Software Architecture."
    format_string = """Respond in a structured JSON message, mapping old categories to new categories. Can you also explain what topics changed as a single description element in the JSON. The description should be concise and understandable to a human reader. The final structure must be formatted in this structure:
        {\r\n    \"description\": \"A summary of the changes to the topics.\",\r\n    \"mappings\": [\r\n        {\r\n            \"new_category\": \"new_category_value\",\r\n            \"old_category\": \"old_category_value\"\r\n        },\r\n        {\r\n            \"new_category\": \"new_category_value\",\r\n            \"old_category\": \"old_category_value\"\r\n        }\r\n    ],\r\n    \"ref_key\": \"2\"\r\n}
        """
  
     #loop through current_categories and build a context
    categories_names = []
    for category in categories:
        categories_names.append(category[0])
    categories_text = ", ".join(categories_names)

    context_string = "I am using this taxonomy to categorize content: " + categories_text + "."
    
    json_response = AiApiHelper.PerformTask(context_string, prompt_string, format_string, current_user.id)
    current_app.logger.debug('AiApiHelper: json_response: %s', json_response)

    description = json_response['description']
    mappings = json_response['mappings']

    new_categories = []

    extract_suggested_categories(mappings, new_categories)
    
    return render_template("profile/organize_taxonomy.html", title='Organize Taxonomy', categories=categories, suggested=new_categories, description=description)

def extract_suggested_categories(mappings, new_categories):
    for mapping in mappings:
        if mapping['new_category'] not in new_categories:
            new_categories.append(mapping['new_category'])
        