# config.py
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    langfuse_host: str = Field(alias="LANG_FUSE_HOST", default="http://localhost:3000")
    langfuse_public_key: str = Field(alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(alias="LANGFUSE_SECRET_KEY")
    anthropic_api_key: str = Field(alias="ANTHROPIC_API_KEY")

    model_config = SettingsConfigDict(
        env_file=".env",  # Project root
        env_file_encoding="utf-8",
        env_prefix="",  # No forced prefix
    )


settings = Settings()
