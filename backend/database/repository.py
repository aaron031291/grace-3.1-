from sqlalchemy.orm import Session
from sqlalchemy import select, desc, asc
from typing import TypeVar, Generic, Type, Optional, List, Any
import logging

T = TypeVar('T')  # Define TypeVar before using it

logger = logging.getLogger(__name__)

class BaseRepository(Generic[T]):
    """
    Base repository class providing common CRUD operations.
    
    Can be extended for specific models:
        class UserRepository(BaseRepository[User]):
            def __init__(self, session: Session):
                super().__init__(session, User)
    """
    
    def __init__(self, session: Session, model: Type[T]):
        """
        Initialize repository.
        
        Args:
            session: SQLAlchemy session
            model: SQLAlchemy model class
        """
        self.session = session
        self.model = model
    
    def create(self, **kwargs) -> T:
        """
        Create and store a new model instance.
        
        Args:
            **kwargs: Model attributes
            
        Returns:
            T: Created model instance
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        self.session.commit()
        self.session.refresh(instance)
        logger.debug(f"Created {self.model.__name__}: {instance}")
        return instance
    
    def get(self, id: Any) -> Optional[T]:
        """
        Get model by primary key.
        
        Args:
            id: Primary key value
            
        Returns:
            Optional[T]: Model instance or None if not found
        """
        return self.session.query(self.model).filter(self.model.id == id).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """
        Get all models with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List[T]: List of model instances
        """
        return self.session.query(self.model).offset(skip).limit(limit).all()
    
    def update(self, id: Any, **kwargs) -> Optional[T]:
        """
        Update a model instance.
        
        Args:
            id: Primary key value
            **kwargs: Attributes to update
            
        Returns:
            Optional[T]: Updated model instance or None if not found
        """
        instance = self.get(id)
        if instance:
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            self.session.commit()
            self.session.refresh(instance)
            logger.debug(f"Updated {self.model.__name__}: {instance}")
            return instance
        return None
    
    def delete(self, id: Any) -> bool:
        """
        Delete a model instance.
        
        Args:
            id: Primary key value
            
        Returns:
            bool: True if deleted, False if not found
        """
        instance = self.get(id)
        if instance:
            self.session.delete(instance)
            self.session.commit()
            logger.debug(f"Deleted {self.model.__name__}: {instance}")
            return True
        return False
    
    def filter(self, **kwargs) -> List[T]:
        """
        Filter models by attributes.
        
        Args:
            **kwargs: Attributes to filter by
            
        Returns:
            List[T]: List of matching model instances
        """
        query = self.session.query(self.model)
        for key, value in kwargs.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)
        return query.all()
    
    def filter_first(self, **kwargs) -> Optional[T]:
        """
        Filter and get first result.
        
        Args:
            **kwargs: Attributes to filter by
            
        Returns:
            Optional[T]: First matching model instance or None
        """
        query = self.session.query(self.model)
        for key, value in kwargs.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)
        return query.first()
    
    def count(self) -> int:
        """
        Count total records.
        
        Returns:
            int: Total number of records
        """
        return self.session.query(self.model).count()
    
    def exists(self, **kwargs) -> bool:
        """
        Check if a record exists.
        
        Args:
            **kwargs: Attributes to filter by
            
        Returns:
            bool: True if record exists, False otherwise
        """
        return self.filter_first(**kwargs) is not None
    
    def bulk_create(self, instances: List[T]) -> List[T]:
        """
        Create multiple instances at once.
        
        Args:
            instances: List of model instances
            
        Returns:
            List[T]: Created instances
        """
        self.session.add_all(instances)
        self.session.commit()
        logger.debug(f"Created {len(instances)} {self.model.__name__} instances")
        return instances
    
    def bulk_delete(self, ids: List[Any]) -> int:
        """
        Delete multiple instances by ID.
        
        Args:
            ids: List of primary key values
            
        Returns:
            int: Number of deleted records
        """
        count = self.session.query(self.model).filter(self.model.id.in_(ids)).delete()
        self.session.commit()
        logger.debug(f"Deleted {count} {self.model.__name__} instances")
        return count
    
    def clear(self) -> int:
        """
        Delete all records.
        
        Returns:
            int: Number of deleted records
        """
        count = self.session.query(self.model).delete()
        self.session.commit()
        logger.debug(f"Cleared all {self.model.__name__} records ({count} deleted)")
        return count
