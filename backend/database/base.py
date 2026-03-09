"""
SQLAlchemy base classes and models.
Provides declarative base and utility base model for all ORM models.
"""

from sqlalchemy.orm import declarative_base, DeclarativeBase
from sqlalchemy import Column, DateTime, Integer
from datetime import datetime, timezone
from typing import Any


def utc_now():
    """Returns the current UTC time, as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


class BaseModel(Base):
    """
    Abstract base model providing common fields and functionality.
    
    Provides:
    - id: Primary key
    - created_at: Timestamp of creation
    - updated_at: Timestamp of last update
    """
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    
    def to_dict(self) -> dict:
        """
        Convert model instance to dictionary.
        
        Returns:
            dict: Dictionary representation of the model
        """
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def update(self, **kwargs) -> None:
        """
        Update model attributes.
        
        Args:
            **kwargs: Attribute names and values to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = utc_now()
    
    def __repr__(self) -> str:
        """String representation of model."""
        class_name = self.__class__.__name__
        id_val = getattr(self, "id", None)
        return f"<{class_name}(id={id_val})>"
