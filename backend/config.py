from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://cortex:cortex@localhost:5432/cortex"
    REDIS_URL: str = "redis://localhost:6379/0"
    HUGGINGFACE_API_TOKEN: str = ""
    SLACK_BOT_TOKEN: str = ""
    CHROMA_PERSIST_DIR: str = "./chroma_data"
    LLM_MODEL: str = "meta-llama/Meta-Llama-3.1-8B-Instruct"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    model_config = {"env_file": ".env"}


settings = Settings()
