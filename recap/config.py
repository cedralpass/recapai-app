import environs

env = environs.Env()
env.read_env()

class Config:
    RECAP_Log_Level=env.str("RECAP_LogLevel")
    SQLALCHEMY_DATABASE_URI='sqlite:////Users/geoffreysmalling/development/instance/recap_sqla.sqlite'
    RECAP_SECRET_KEY=env.str("SECRET_KEY")
    RECAP_REDIS_URL=env.str("RECAP_REDIS_URL")
    RECAP_RQ_QUEUE=env.str("RECAP_RQ_QUEUE")
    ARTICLES_PER_PAGE=env.int("ARTICLES_PER_PAGE")
    MAIL_SERVER= env.str("MAIL_SERVER")
    MAIL_PORT= env.str("MAIL_PORT")
    MAIL_USE_TLS= env.str("MAIL_USE_TLS")
    MAIL_USERNAME= env.str("MAIL_USERNAME")
    MAIL_PASSWORD= env.str("MAIL_PASSWORD")
    MAIL_DEFUALT_FROM= env.str("MAIL_DEFUALT_FROM")
    TASK_SERVER_NAME= env.str("TASK_SERVER_NAME")
    RECAP_AI_API_URL= env.str("RECAP_AI_API_URL") #config for calling classification service
    