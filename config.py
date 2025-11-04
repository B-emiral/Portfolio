# ./config.py
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        extra="ignore",
    )

    # Anthropic
    anthropic_api_key: str = Field(alias="ANTHROPIC_API_KEY")

    # Langfuse
    langfuse_host: str = Field(alias="LANGFUSE_HOST", default="http://localhost:3000")
    langfuse_public_key: Optional[str] = Field(
        alias="LANGFUSE_PUBLIC_KEY", default=None
    )
    langfuse_secret_key: Optional[str] = Field(
        alias="LANGFUSE_SECRET_KEY", default=None
    )

    # NoSQL - MongoDB
    mongo_uri: str = Field(alias="MONGO_URI_DEV")
    mongo_db: str = Field(alias="MONGO_DB_LLM_DEV")

    # SQL - SQLite (for dev)
    database_url: str = Field(
        alias="DATABASE_URL", default="sqlite+aiosqlite:///./app.db"
    )


settings = Settings()
