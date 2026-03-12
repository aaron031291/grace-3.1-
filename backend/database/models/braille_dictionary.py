from sqlalchemy import Column, String, Text, Boolean, Integer, JSON
from database.base import BaseModel

class BrailleDictionaryMapping(BaseModel):
    """
    Dynamic Braille Semantic Dictionary.
    Maps human words and semantic meanings directly to raw Braille encodings.
    Allows Spindle to auto-update and learn new vocabulary dynamically.
    """
    __tablename__ = "braille_semantic_dictionary"

    word = Column(String(255), unique=True, index=True, nullable=False)
    braille_encoding = Column(String(50), nullable=False)
    semantic_meaning = Column(Text, nullable=True)
    master_loop = Column(String(50), index=True, nullable=True) # E.g., "COGNITION", "GOVERNANCE"
    metadata_json = Column(JSON, nullable=True) # e.g. usage statistics, contextual relations
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<BrailleDictionaryMapping(word='{self.word}', encoding='{self.braille_encoding}')>"
