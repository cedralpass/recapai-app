from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
)
from recap.profile.forms import EditProfileForm
from flask_login import current_user, login_user, logout_user, login_required
import sqlalchemy as sa
from recap import db
from recap.models import User
from recap.config import Config 

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

    return render_template('user.html', user=user, articles=articles,
                           next_url=next_url, prev_url=prev_url)


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
    return render_template('edit_profile.html', title='Edit Profile',
                           form=form)