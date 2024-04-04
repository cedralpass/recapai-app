import environs

env = environs.Env()
env.read_env()

class Config:
    RECAP_Log_Level=env.str("RECAP_LogLevel")
    SQLALCHEMY_DATABASE_URI='sqlite:////Users/geoffreysmalling/development/instance/recap_sqla.sqlite'
    RECAP_SECRET_KEY=env.str("SECRET_KEY")
    RECAP_REDIS_URL=env.str("RECAP_REDIS_URL")
    RECAP_RQ_QUEUE=env.str("RECAP_RQ_QUEUE")
    