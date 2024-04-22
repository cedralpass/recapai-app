import environs

env = environs.Env()
env.read_env()

class Config:
    RECAP_Log_Level=env.str("RECAP_LogLevel")
    
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

    #configure postgres variables
    POSTGRES_USER=env.str("RECAP_POSTGRES_USER")
    POSTGRES_PASSWORD=env.str("RECAP_POSTGRES_PASSWORD")
    POSTGRES_HOST=env.str("RECAP_POSTGRES_HOST")
    POSTGRES_PORT=env.str("RECAP_POSTGRES_PORT")
    POSTGRES_DB=env.str("RECAP_POSTGRES_DB")
    #Sqllite DB
    #SQLALCHEMY_DATABASE_URI='sqlite:////Users/geoffreysmalling/development/instance/recap_sqla.sqlite'
   
    if "neon.tech" in POSTGRES_HOST:
        SQLALCHEMY_DATABASE_URI=f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}?sslmode=require"
    else:
        SQLALCHEMY_DATABASE_URI=f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    