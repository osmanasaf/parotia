from typing import Generic, TypeVar, Type, Optional, List, Any, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.db import Base

ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations"""
    
    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db
    
    def get(self, id: Any) -> Optional[ModelType]:
        """Get by ID"""
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get all with pagination"""
        return self.db.query(self.model).offset(skip).limit(limit).all()
    
    def create(self, obj_in: Dict[str, Any]) -> ModelType:
        """Create new object"""
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    def update(self, db_obj: ModelType, obj_in: Dict[str, Any]) -> ModelType:
        """Update object"""
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    def delete(self, id: Any) -> bool:
        """Delete by ID"""
        obj = self.db.query(self.model).get(id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
            return True
        return False
    
    def filter_by(self, **kwargs) -> List[ModelType]:
        """Filter by multiple conditions"""
        return self.db.query(self.model).filter_by(**kwargs).all()
    
    def filter_one_by(self, **kwargs) -> Optional[ModelType]:
        """Filter by multiple conditions and return first"""
        return self.db.query(self.model).filter_by(**kwargs).first()
    
    def exists(self, **kwargs) -> bool:
        """Check if object exists"""
        return self.db.query(self.model).filter_by(**kwargs).first() is not None 