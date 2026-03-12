from sqlalchemy import Column, String, Text, Boolean
from database.base import BaseModel

class BrailleSandboxNode(BaseModel):
    """
    Stores Python files as deterministic Braille nodes in the Sandbox.
    Mapped directly to the GRACE DETERMINISTIC LANGUAGE SPECIFICATION v1.0.
    """
    __tablename__ = "braille_sandbox_nodes"

    genesis_key = Column(String(50), unique=True, index=True, nullable=False)
    braille_encoding = Column(String(50), nullable=True)
    master_loop = Column(String(50), index=True, nullable=False)
    file_path = Column(String(500), unique=True, index=True, nullable=False)
    ast_content = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<BrailleSandboxNode(key='{self.genesis_key}', loop='{self.master_loop}')>"
