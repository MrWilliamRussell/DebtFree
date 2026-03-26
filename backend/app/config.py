from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://finance:finance_secret@localhost:5432/finance_db"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6334
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "mistral"
    discord_webhook_url: str = ""
    plaid_client_id: str = ""
    plaid_secret: str = ""
    plaid_env: str = "sandbox"
    secret_key: str = "change-me-in-production"
    redis_url: str = "redis://redis:6379/0"

    class Config:
        env_file = ".env"


settings = Settings()
