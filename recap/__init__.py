from flask import Flask
from recap.config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()



def create_app():
    app = Flask(__name__)
    configure_app(app, 'dev')
    
    db.init_app(app)
    migrate.init_app(app, db)
    from recap.models import User, Article

    @app.route('/')
    @app.route('/index')
    def index():
        return "Hello, World!"
    return app

def configure_app(app, env):
    app.config['API_KEY'] = Config.RECAP_SECRET_KEY
    app.config["SECRET_KEY"]=Config.RECAP_SECRET_KEY # set the key to secure Flask App
    app.config["SQLALCHEMY_DATABASE_URI"]=Config.SQLALCHEMY_DATABASE_URI