# # ./persistence/models/relationships.py
# from sqlalchemy.orm import relationship

# from persistence.models.document import Document
# from persistence.models.sentence import SentenceSentimentAnalysisEntity

# Document.sentences = relationship(
#     "SentenceSentimentAnalysisEntity",
#     back_populates="document",
#     lazy="selectin",
# )

# SentenceSentimentAnalysisEntity.document = relationship(
#     "Document",
#     back_populates="sentences",
#     lazy="selectin",
# )
