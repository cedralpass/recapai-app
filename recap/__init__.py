from flask import Flask
from recap.config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from redis import Redis
import rq

db = SQLAlchemy()
migrate = Migrate()



def create_app():
    app = Flask(__name__)
    configure_app(app, 'dev')
    
    #configure DB
    db.init_app(app)
    migrate.init_app(app, db)
    from recap.models import User, Article

    #configure redis
    app.redis = Redis.from_url(Config.RECAP_REDIS_URL)
    app.task_queue = rq.Queue(Config.RECAP_RQ_QUEUE, connection=app.redis)


    @app.route('/')
    @app.route('/index')
    def index():
        return "Hello, World!"
    
    @app.route('/job')
    def job():
        job = launch_task(name='recap.tasks.example', description='example', seconds=5)
        return 'Job is Executing ' + job.id + ' its status ' + job.get_status(refresh=True)
    
    # a url for showing a job_id
    @app.route('/job/<string:id>/show')
    def job_show(id):
        job = app.task_queue.fetch_job(job_id=id)
        
        return 'Job is Executing ' + job.id + ' its status ' + job.get_status(refresh=True)
    
    # TODO - understand args and kwargs better for dynamic params 
    def launch_task(name, description, *args, **kwargs):
        rq_job = app.task_queue.enqueue(name, description=description, args=args, kwargs=kwargs)
        return rq_job

    return app

def configure_app(app, env):
    app.config['API_KEY'] = Config.RECAP_SECRET_KEY
    app.config["SECRET_KEY"]=Config.RECAP_SECRET_KEY # set the key to secure Flask App
    app.config["SQLALCHEMY_DATABASE_URI"]=Config.SQLALCHEMY_DATABASE_URI