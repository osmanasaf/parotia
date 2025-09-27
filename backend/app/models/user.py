from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    ratings = relationship("UserRating", back_populates="user", cascade="all, delete-orphan")
    watchlist = relationship("UserWatchlist", back_populates="user", cascade="all, delete-orphan")
    recommendations = relationship("UserRecommendation", back_populates="user", cascade="all, delete-orphan")
    emotional_profile = relationship("UserEmotionalProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    recommendation_selections = relationship("RecommendationSelection", back_populates="user", cascade="all, delete-orphan")

class EmailVerification(Base):
    __tablename__ = "email_verifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    verification_code = Column(String(6), nullable=False)  # 6 haneli kod
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False)
    # Yeni alanlar: e-posta değişimi için hedef email ve amaç bilgisi
    target_email = Column(String, nullable=True)
    purpose = Column(String, nullable=False, default="verify_email")  # verify_email | email_change
    created_at = Column(DateTime(timezone=True), server_default=func.now()) 