# ./persistence/models/base.py
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel


class BaseEntityModel(SQLModel, table=False):
    """Common fields and methods shared by all DB entities."""

    created_at: datetime = SQLField(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = SQLField(default_factory=lambda: datetime.now(timezone.utc))

    def touch(self):
        self.updated_at = datetime.now(timezone.utc)

    pass


class BaseLLMResponseModel(BaseModel):
    class Config:
        from_attributes = True
