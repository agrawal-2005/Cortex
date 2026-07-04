from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://cortex:cortex@localhost:5432/cortex"
    REDIS_URL: str = "redis://localhost:6379/0"
    HUGGINGFACE_API_TOKEN: str = ""
    SLACK_BOT_TOKEN: str = ""
    CHROMA_PERSIST_DIR: str = "./chroma_data"
    # LLM backend: "huggingface", "ollama", or "groq".
    LLM_PROVIDER: str = "huggingface"
    LLM_MODEL: str = "meta-llama/Llama-3.1-8B-Instruct"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    # Larger Groq model used for on-demand ("live") extraction at query
    # time, where one cluster is extracted while the user waits.
    GROQ_LIVE_MODEL: str = "llama-3.3-70b-versatile"
    OLLAMA_MODEL: str = "llama3.1"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ── Lazy extraction ───────────────────────────────────────────────────
    # After ingestion every document is clustered (cheap), but only the
    # largest PRE_EXTRACT_TOP_N clusters are extracted immediately. The
    # rest are stored as pending clusters and extracted on demand at query
    # time.
    PRE_EXTRACT_TOP_N: int = 6

    # ── Security ──────────────────────────────────────────────────────────
    # "development" or "production" — controls CORS strictness.
    ENVIRONMENT: str = "development"
    # Comma-separated allowed origins. Required in production; defaults to
    # localhost dev servers otherwise.
    CORS_ORIGINS: str = ""
    # Fernet key (44-char urlsafe base64) for encrypting stored source
    # tokens. If empty, an ephemeral key is generated at startup — stored
    # tokens then become unreadable after a restart, so set it in prod.
    TOKEN_ENCRYPTION_KEY: str = ""
    # Per-API-key rate limits.
    RATE_LIMIT_INGEST_PER_HOUR: int = 10
    RATE_LIMIT_QUERY_PER_HOUR: int = 100
    # Upload cap in megabytes.
    MAX_UPLOAD_MB: int = 50

    model_config = {"env_file": ".env"}

    def cors_origins_list(self) -> list[str]:
        """Resolve allowed CORS origins for the current environment."""
        configured = [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        if configured:
            return configured
        if self.ENVIRONMENT == "production":
            # Never fall back to permissive defaults in production.
            raise RuntimeError(
                "CORS_ORIGINS must be set explicitly when ENVIRONMENT=production"
            )
        return [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]


settings = Settings()
