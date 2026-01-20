# ./persistence/models/base.py
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel


class BaseEntityModel(SQLModel, table=False):
    created_at: datetime = SQLField(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = SQLField(default_factory=lambda: datetime.now(timezone.utc))
    process_id: str | None = SQLField(default=None)

    def touch(self):
        self.updated_at = datetime.now(timezone.utc)


class BaseLLMResponseModel(BaseModel):
    class Config:
        from_attributes = True
