# config.py
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Required for Anthropic
    anthropic_api_key: str = Field(alias="ANTHROPIC_API_KEY")

    # Langfuse: make optional; hooks will no-op if missing
    langfuse_host: str = Field(alias="LANGFUSE_HOST", default="http://localhost:3000")
    langfuse_public_key: Optional[str] = Field(
        alias="LANGFUSE_PUBLIC_KEY", default=None
    )
    langfuse_secret_key: Optional[str] = Field(
        alias="LANGFUSE_SECRET_KEY", default=None
    )

    # Mongo: give sensible defaults so Settings() doesn't crash in dev
    mongo_uri: str = Field(alias="MONGO_URI_DEV")
    mongo_db: str = Field(alias="MONGO_DB_LLM_DEV")
    mongo_collection: str = Field(alias="MONGO_COLLECTION_LLM_DEV")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        extra="ignore",
    )


settings = Settings()
