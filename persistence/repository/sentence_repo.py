# ./persistence/repository/sentence_repo.py
from __future__ import annotations

from persistence.models.document import DocumentEntity
from persistence.models.sentence import SentenceEntity
from persistence.repository.base_repo import BaseRepository


class SentenceRepository(BaseRepository):
    entity = SentenceEntity
    parent_entity = DocumentEntity
    fk_field = "doc_id"

    def __init__(self) -> None:
        super().__init__()
