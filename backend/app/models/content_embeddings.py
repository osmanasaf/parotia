from sqlalchemy import Column, Integer, String, DateTime, Float, ARRAY, JSON, Text
from sqlalchemy.sql import func
from app.db import Base
from datetime import datetime

class ContentEmbedding(Base):
    """Content embeddings stored in database for fast access"""
    __tablename__ = "content_embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    tmdb_id = Column(Integer, nullable=False, index=True)
    content_type = Column(String, nullable=False)  # "movie" or "tv"
    
    # Content metadata (from TMDB)
    title = Column(String, nullable=False)
    overview = Column(Text)
    genres = Column(JSON)  # List of genre names
    release_date = Column(String)  # YYYY-MM-DD format
    poster_path = Column(String)
    vote_average = Column(Float)
    vote_count = Column(Integer)
    
    # Embedding vector (384 dimensions for all-MiniLM-L6-v2)
    embedding_vector = Column(ARRAY(Float), nullable=False)
    
    # Additional metadata
    popularity = Column(Float)
    original_language = Column(String)
    original_title = Column(String)
    
    # Index for fast lookups
    __table_args__ = (
        # Composite index for fast content lookups
        # {'postgresql_partition_by': 'LIST (content_type)'}  # Removed partitioning for now
    )
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) 