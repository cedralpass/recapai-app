from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
)
from recap.forms import LoginForm
from flask_login import current_user, login_user, logout_user, login_required
import sqlalchemy as sa
from recap import db
from recap.forms import RegistrationForm, EditProfileForm, ArticleForm, ResetPasswordRequestForm, ResetPasswordForm
from recap.models import User, Article
from urllib.parse import urlsplit
from recap.config import  Config
from recap.email import send_password_reset_email


bp = Blueprint('routes', __name__)

@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
def index():
    form = ArticleForm()
    if form.validate_on_submit():
        article = Article(url_path=form.url_path.data, user=current_user)
        db.session.add(article)
        db.session.commit()
        flash('Your article is being classified!')
        return redirect(url_for('routes.index'))
    
    page = request.args.get('page', 1, type=int)

    #get_articles(self,page=1, per_page=2)
    #set articles, next_url, prev_url to None
    articles = None
    next_url = None
    prev_url = None
    if current_user.is_authenticated:
        current_user.get_articles(page=page, per_page=Config.ARTICLES_PER_PAGE)
        articles_paginator = current_user.get_articles(page=page, per_page=Config.ARTICLES_PER_PAGE)
        articles = articles_paginator.items
        next_url = url_for('routes.index', page=articles_paginator.next_num) \
            if articles_paginator.has_next else None
        prev_url = url_for('routes.index', page=articles_paginator.prev_num) \
            if articles_paginator.has_prev else None
        
    return render_template("index.html", title='Home Page', form=form,
                           articles=articles, next_url=next_url, prev_url=prev_url)

 #TODO: move login to a blueprint requires, flash, render_template, redirect
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('routes.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('routes.login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('routes.index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('routes.index'))

@bp.route('/job')
@login_required
def job():
    job = launch_task(name='recap.tasks.example', description='example', seconds=5)
    return 'Job is Executing ' + job.id + ' its status ' + job.get_status(refresh=True)

# a url for showing a job_id
@bp.route('/job/<string:id>/show')
@login_required
def job_show(id):
    job = current_app.task_queue.fetch_job(job_id=id)
    
    return 'Job is Executing ' + job.id + ' its status ' + job.get_status(refresh=True)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('routes.login'))
    return render_template('register.html', title='Register', form=form)

@bp.route('/user/<username>')
@login_required
def user(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    page = request.args.get('page', 1, type=int)

    #get_articles(self,page=1, per_page=2)
    articles_paginator = current_user.get_articles(page=page, per_page=Config.ARTICLES_PER_PAGE)
    articles = articles_paginator.items
    next_url = url_for('routes.user',username=user.username, page=articles_paginator.next_num) \
        if articles_paginator.has_next else None
    prev_url = url_for('routes.user',username=user.username, page=articles_paginator.prev_num) \
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
        return redirect(url_for('routes.edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.phone.data = current_user.phone
        form.email.data = current_user.email
    return render_template('edit_profile.html', title='Edit Profile',
                           form=form)

@bp.route('/add_article', methods=['GET', 'POST'])
@login_required
def add_article():
    form = ArticleForm()
    if form.validate_on_submit():
        article = Article(url_path=form.url_path.data, user=current_user)
        db.session.add(article)
        db.session.commit()
        flash('Your article is being classified!')
        return redirect(url_for('routes.index'))
    else:
        return render_template('add_article.html', title='add_article',
                           form=form)
    

@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('routes.index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.email == form.email.data))
        if user:
            #send_password_reset_email(user)
            job = launch_task(name='recap.tasks.send_password_reset_email_task', description='reset password email', user_id=user.id)
            print(job)
        flash('Check your email for the instructions to reset your password')
        return redirect(url_for('routes.login'))
    return render_template('reset_password_request.html',
                           title='Reset Password', form=form)

@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('routes.index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('routes.index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('routes.login'))
    return render_template('reset_password.html', form=form)

# TODO - understand args and kwargs better for dynamic params 
def launch_task(name, description, *args, **kwargs):
    rq_job = current_app.task_queue.enqueue(name, description=description, args=args, kwargs=kwargs)
    return rq_job
    