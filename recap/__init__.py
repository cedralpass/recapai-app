from flask import Flask, redirect, flash, render_template, url_for
from recap.config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from redis import Redis
import rq
from flask_login import LoginManager
from flask_mail import Mail
from logging.handlers import RotatingFileHandler
from logging.config import dictConfig


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail( )


def create_app():
    app = Flask(__name__)
    configure_app(app, 'dev')
    
    #configure DB
    #set the pool timeout to 10 seconds
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_timeout': 27,  # Set your desired timeout value in seconds,
    'pool_pre_ping':True # Set to True to enable pre-ping
}
    db.init_app(app)
    migrate.init_app(app, db)
    from recap.models import User, Article

    configure_loggging()
    #configure login manager
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login' #view for required login

    #configure redis
    app.redis = Redis.from_url(Config.RECAP_REDIS_URL)
    app.task_queue = rq.Queue(Config.RECAP_RQ_QUEUE, connection=app.redis)

    #configure mail
    mail.init_app(app)
   


    from . import routes
    app.register_blueprint(routes.bp) #register the routes blueprint
    # from . import errors
    # app.register_blueprint(errors.bp) #register the errors blueprint
    from recap.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    from recap.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from recap.profile import bp as profile_bp 
    app.register_blueprint(profile_bp)


    return app

def configure_app(app, env):
    app.config['API_KEY'] = Config.RECAP_SECRET_KEY
    app.config["SECRET_KEY"]=Config.RECAP_SECRET_KEY # set the key to secure Flask App
    app.config["SQLALCHEMY_DATABASE_URI"]=Config.SQLALCHEMY_DATABASE_URI
    
    #setup app.config for mail server variables
    app.config['MAIL_SERVER'] = Config.MAIL_SERVER
    app.config['MAIL_PORT'] = Config.MAIL_PORT
    app.config['MAIL_USE_TLS'] = Config.MAIL_USE_TLS
    app.config['MAIL_USERNAME'] = Config.MAIL_USERNAME
    app.config['MAIL_PASSWORD'] = Config.MAIL_PASSWORD

def configure_loggging():
    log_level = Config.RECAP_Log_Level

    # good example of logging from here: https://betterstack.com/community/guides/logging/how-to-start-logging-with-flask/
    # this must be configured before loading the app context
    dictConfig(
        {
            "version": 1,
            "formatters": {
                "default": {
                    "format": "[%(asctime)s] %(process)d %(levelname)s in %(module)s: %(message)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                    "formatter": "default",
                },
                "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "recap.log",
                "maxBytes": 1024*1024,
                "backupCount": 2,
                "formatter": "default",
            }
            },
            "root": {"level": log_level, "handlers": ["console","file"]},
        }
    )