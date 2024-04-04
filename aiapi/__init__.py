import os

from flask import Flask, jsonify, logging
from logging.handlers import RotatingFileHandler
from logging.config import dictConfig
from environs import Env
from aiapi.config import AIAPIConfig

def create_app():
    # create and configure the app
    test_config = None
    #TODO: figure out better config
    env = Env()
    env.read_env()
    configure_loggging()
    app = Flask(__name__)
    configure_app(env, app)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # from . import classify
    # app.register_blueprint(classify.bp) #register the auth blueprint

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        json_obj ={"key":"Hello, World! in JSON"}
        return jsonify(json_obj)
    return app

def configure_loggging():
    log_level = AIAPIConfig.AI_API_LogLevel

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
                "filename": "aiapi_app.log",
                "maxBytes": 1024*1024,
                "backupCount": 2,
                "formatter": "default",
            }
            },
            "root": {"level": log_level, "handlers": ["console","file"]},
        }
    )

def configure_app(env, app):
    app.config["AI_API_OPENAI"]=AIAPIConfig.AI_API_OPENAI #OpenAI API Key
    app.config["AI_API_LogLevel"]=AIAPIConfig.AI_API_LogLevel # Set Log Level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    app.config["SECRET_KEY"]=AIAPIConfig.AI_API_SECRET_KEY # set the key to secure Flask App

    