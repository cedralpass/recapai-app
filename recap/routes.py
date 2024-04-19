from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
)
from flask_login import current_user, login_user, logout_user, login_required
import sqlalchemy as sa
from recap import db
from recap.forms import  ArticleForm
from recap.models import User, Article
from urllib.parse import urlsplit
from recap.config import  Config
from recap.auth.email import send_password_reset_email


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

@bp.route('/css', methods=['GET', 'POST'])
def css():
    flash('Invalid username or password')
    return render_template("css.html", title='CSS')


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


# TODO - understand args and kwargs better for dynamic params 
def launch_task(name, description, *args, **kwargs):
    rq_job = current_app.task_queue.enqueue(name, description=description, args=args, kwargs=kwargs)
    return rq_job
    