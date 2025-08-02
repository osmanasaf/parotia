import logging
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Text, ForeignKey, JSON, ARRAY, func
from sqlalchemy.orm import relationship

from app.db import Base

logger = logging.getLogger(__name__)

class UserRating(Base):
    __tablename__ = "user_ratings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tmdb_id = Column(Integer, nullable=False)
    content_type = Column(String, nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="ratings")

class UserWatchlist(Base):
    __tablename__ = "user_watchlists"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tmdb_id = Column(Integer, nullable=False)
    content_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    
    # Recommendation tracking
    from_recommendation = Column(Boolean, default=False)
    recommendation_id = Column(Integer, ForeignKey("user_recommendations.id"), nullable=True)
    recommendation_type = Column(String, nullable=True)
    recommendation_score = Column(Float, nullable=True)
    
    # Source and notification tracking
    source = Column(String, nullable=True)
    notification_sent = Column(Boolean, default=False)
    notification_sent_at = Column(DateTime(timezone=True))
    feedback_provided = Column(Boolean, default=False)
    feedback_provided_at = Column(DateTime(timezone=True))
    
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="watchlist")
    recommendation = relationship("UserRecommendation", foreign_keys=[recommendation_id])

class UserRecommendation(Base):
    __tablename__ = "user_recommendations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tmdb_id = Column(Integer, nullable=False)
    content_type = Column(String, nullable=False)
    recommendation_type = Column(String, nullable=False)
    emotion_state = Column(String)
    score = Column(Float)
    viewed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="recommendations")

class UserEmotionalProfile(Base):
    __tablename__ = "user_emotional_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    
    # Emotional embedding vector
    emotional_embedding = Column(ARRAY(Float), nullable=True)
    
    # Metadata
    total_watched_movies = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Preferences
    preferred_genres = Column(JSON, default=dict)
    emotional_tendencies = Column(JSON, default=dict)
    
    # Performance metrics
    profile_confidence = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="emotional_profile")

# ContentEmotionalTone tablosu gelecekte kullanılabilir
# class ContentEmotionalTone(Base):
#     """Emotional tone analysis for content"""
#     __tablename__ = "content_emotional_tones"
#     # ... gelecekte eklenecek

class RecommendationSelection(Base):
    __tablename__ = "recommendation_selections"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tmdb_id = Column(Integer, nullable=False)
    content_type = Column(String, nullable=False)
    
    # Recommendation context
    recommendation_session_id = Column(String, nullable=False)
    recommendation_type = Column(String, nullable=False)
    recommendation_score = Column(Float, nullable=True)
    selected_rank = Column(Integer, nullable=True)
    
    # Source information
    source = Column(String, nullable=False)
    
    # Notification tracking
    notification_scheduled = Column(Boolean, default=False)
    notification_scheduled_at = Column(DateTime(timezone=True))
    notification_sent = Column(Boolean, default=False)
    notification_sent_at = Column(DateTime(timezone=True))
    
    # Feedback tracking
    feedback_requested = Column(Boolean, default=False)
    feedback_requested_at = Column(DateTime(timezone=True))
    feedback_provided = Column(Boolean, default=False)
    feedback_provided_at = Column(DateTime(timezone=True))
    
    # User interaction
    added_to_watchlist = Column(Boolean, default=False)
    watched = Column(Boolean, default=False)
    watched_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="recommendation_selections") 