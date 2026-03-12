import logging
from typing import Optional, Dict, Any, List
from database.session import get_session_factory
from database.models.braille_dictionary import BrailleDictionaryMapping

logger = logging.getLogger(__name__)

class DynamicDictionaryManager:
    """
    Manages the live, auto-updating semantic dictionary for Spindle.
    Maps human words to strict deterministic Braille constraints.
    """
    
    @classmethod
    def learn_word(cls, word: str, braille_encoding: str, semantic_meaning: str = "", master_loop: str = "COGNITION") -> Dict[str, Any]:
        """
        Teaches Spindle a new semantic mapping or updates an existing one.
        """
        word = word.lower().strip()
        
        with get_session_factory()() as session:
            existing = session.query(BrailleDictionaryMapping).filter(BrailleDictionaryMapping.word == word).first()
            if existing:
                existing.braille_encoding = braille_encoding
                existing.semantic_meaning = semantic_meaning
                logger.info(f"[Semantic Dictionary] Updated mapping for '{word}' -> {braille_encoding}")
                session.commit()
                return {"status": "updated", "word": word, "encoding": braille_encoding}
            else:
                new_mapping = BrailleDictionaryMapping(
                    word=word,
                    braille_encoding=braille_encoding,
                    semantic_meaning=semantic_meaning,
                    master_loop=master_loop
                )
                session.add(new_mapping)
                session.commit()
                logger.info(f"[Semantic Dictionary] Learned new mapping for '{word}' -> {braille_encoding}")
                return {"status": "created", "word": word, "encoding": braille_encoding}

    @classmethod
    def lookup_word(cls, word: str) -> Optional[str]:
        """
        Returns the raw Braille encoding for a specific semantic word.
        """
        word = word.lower().strip()
        with get_session_factory()() as session:
            mapping = session.query(BrailleDictionaryMapping).filter(
                BrailleDictionaryMapping.word == word,
                BrailleDictionaryMapping.is_active == True
            ).first()
            return mapping.braille_encoding if mapping else None

    @classmethod
    def get_full_dictionary(cls, master_loop: str = None) -> List[Dict[str, Any]]:
        """
        Dumps the entire semantic dictionary context.
        Used to feed Spindle its deterministic vocabulary range before logic assembly.
        """
        with get_session_factory()() as session:
            query = session.query(BrailleDictionaryMapping).filter(BrailleDictionaryMapping.is_active == True)
            if master_loop:
                query = query.filter(BrailleDictionaryMapping.master_loop == master_loop)
            
            return [
                {
                    "word": m.word,
                    "encoding": m.braille_encoding,
                    "meaning": m.semantic_meaning
                } for m in query.all()
            ]

def get_dynamic_dictionary() -> DynamicDictionaryManager:
    return DynamicDictionaryManager()
