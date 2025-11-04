# ./persistence/repository/sentence_repo.py
from __future__ import annotations

from langops.persistence.models.document import DocumentEntity
from langops.persistence.models.sentence import SentenceEntity
from langops.persistence.repository.base_repo import BaseRepository


class SentenceRepository(BaseRepository):
    entity = SentenceEntity
    parent_entity = DocumentEntity
    fk_field = "doc_id"

    def __init__(self) -> None:
        super().__init__()
