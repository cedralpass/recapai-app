from environs import Env

# a class to load configurations for development, staging, and produciton cleanly
env = Env()
env.read_env()

class AIAPIConfig:
    AI_API_LogLevel= env.str("AI_API_LogLevel")
    AI_API_OPENAI= env.str("AI_API_OPENAI")
    AI_API_SECRET_KEY= env.str("AI_API_SECRET_KEY")
    AI_OPEN_AI_MODEL= env.str("AI_OPEN_AI_MODEL")
    