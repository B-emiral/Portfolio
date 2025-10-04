# ./persistence/models/relationships.py
from sqlalchemy.orm import relationship

from persistence.models.document import Document
from persistence.models.sentence import SentimentAnalysisEntity

Document.sentences = relationship(
    "SentimentAnalysisEntity",
    back_populates="document",
    lazy="selectin",
)

SentimentAnalysisEntity.document = relationship(
    "Document",
    back_populates="sentences",
    lazy="selectin",
)
