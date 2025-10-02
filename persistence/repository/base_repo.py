# ./persistence/repository/base_repo.py
"""Base repository for common database operations."""

from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel, select

T = TypeVar("T", bound=SQLModel)


class BaseRepository(Generic[T]):
    """Base repository with common CRUD operations."""

    def __init__(self, model: type[T]):
        self.model = model

    async def create(self, session: AsyncSession, **kwargs) -> T:
        """Create a new entity."""
        entity = self.model(**kwargs)
        session.add(entity)
        await session.commit()
        await session.refresh(entity)
        return entity

    async def get_by_id(self, session: AsyncSession, id: int) -> T | None:
        """Get entity by ID."""
        result = await session.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def update(self, session: AsyncSession, entity: T) -> T:
        """Update an entity."""
        session.add(entity)
        await session.commit()
        await session.refresh(entity)
        return entity
