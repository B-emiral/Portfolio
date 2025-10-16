# ./persistence/repository/base_repo.py
"""Base repository for common database operations."""

from __future__ import annotations

import hashlib

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from persistence.models.base import BaseEntityModel


class BaseRepository:
    entity: type[BaseEntityModel]
    parent_entity: type[BaseEntityModel] | None
    fk_field: str | None

    def __init__(self):
        pass

    @staticmethod
    def compute_hash(text: str) -> str:
        """Compute MD5 hash of text."""
        return hashlib.md5(text.encode()).hexdigest()

    @classmethod
    async def get_unprocessed(
        cls, session: AsyncSession, limit: int = 100
    ) -> list[BaseEntityModel] | None:
        if not cls.parent_entity or not cls.fk_field:
            raise NotImplementedError(
                f"GUARD: {cls.__name__} does not support get_unprocessed(), "
                f"because it has no parent entity."
            )

        stmt = (
            select(cls.parent_entity)
            .outerjoin(
                cls.entity,
                getattr(cls.entity, cls.fk_field) == cls.parent_entity.id,
            )
            .where(getattr(cls.entity, "id").is_(None))
            .limit(limit)
        )

        result = await session.exec(stmt)
        return result.all()

    async def get_by_id(self, session: AsyncSession, id: int) -> BaseEntityModel | None:
        result = await session.exec(select(self.entity).where(self.entity.id == id))
        return result.scalar_one_or_none()

    async def create(
        self, session: AsyncSession, entity: BaseEntityModel
    ) -> BaseEntityModel:
        session.add(entity)
        await session.flush()
        await session.refresh(entity)
        return entity

    async def update(
        self, session: AsyncSession, entity: BaseEntityModel
    ) -> BaseEntityModel | None:
        entity = await self.get_by_id(session, entity.id)
        if not entity:
            return None
        session.add(entity)
        await session.flush()
        await session.refresh(entity)
        return entity

    async def update_partial(
        self,
        session: AsyncSession,
        entity_id: int,
        **fields,
    ) -> BaseEntityModel | None:
        entity = await self.get_by_id(session, entity_id)
        if not entity:
            return None

        for key, value in fields.items():
            if hasattr(entity, key):
                setattr(entity, key, value)

        session.add(entity)
        await session.flush()
        await session.refresh(entity)
        return entity

    async def delete(self, session: AsyncSession, entity: BaseEntityModel) -> bool:
        if not entity:
            return False
        await session.delete(entity)
        await session.flush()
        return True
