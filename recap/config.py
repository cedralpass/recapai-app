import environs

env = environs.Env()
env.read_env()

class Config:
    RECAP_Log_Level=env.str("RECAP_LogLevel")
    SQLALCHEMY_DATABASE_URI='sqlite:////Users/geoffreysmalling/development/instance/recap_sqla.sqlite'
    RECAP_SECRET_KEY=env.str("SECRET_KEY")