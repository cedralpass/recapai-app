from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
)
from recap.forms import LoginForm
from flask_login import current_user, login_user, logout_user, login_required
import sqlalchemy as sa
from recap import db
from recap.models import User
from urllib.parse import urlsplit

bp = Blueprint('routes', __name__)

@bp.route('/')
@bp.route('/index')
def index():
    return render_template("index.html", title='Home Page')

 #TODO: move login to a blueprint requires, flash, render_template, redirect
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
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

# TODO - understand args and kwargs better for dynamic params 
def launch_task(name, description, *args, **kwargs):
    rq_job = current_app.task_queue.enqueue(name, description=description, args=args, kwargs=kwargs)
    return rq_job
    