from flask import Flask, redirect, flash, render_template, url_for
from recap.config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from redis import Redis
import rq
from flask_login import LoginManager


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    configure_app(app, 'dev')
    
    #configure DB
    db.init_app(app)
    migrate.init_app(app, db)
    from recap.models import User, Article
    

    #configure login manager
    login_manager.init_app(app)
    login_manager.login_view = 'routes.login' #view for required login

    #configure redis
    app.redis = Redis.from_url(Config.RECAP_REDIS_URL)
    app.task_queue = rq.Queue(Config.RECAP_RQ_QUEUE, connection=app.redis)

    from . import routes
    app.register_blueprint(routes.bp) #register the routes blueprint
    from . import errors
    app.register_blueprint(errors.bp) #register the errors blueprint


    return app

def configure_app(app, env):
    app.config['API_KEY'] = Config.RECAP_SECRET_KEY
    app.config["SECRET_KEY"]=Config.RECAP_SECRET_KEY # set the key to secure Flask App
    app.config["SQLALCHEMY_DATABASE_URI"]=Config.SQLALCHEMY_DATABASE_URI