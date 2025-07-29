from sqlalchemy import Column, Integer, ForeignKey, String, DateTime
from app.db import Base
from datetime import datetime

class RecommendationFeedback(Base):
    __tablename__ = "recommendation_feedbacks"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    feedback = Column(String, nullable=False)  # e.g. 'like', 'dislike', 'neutral'
    created_at = Column(DateTime, default=datetime.utcnow) 