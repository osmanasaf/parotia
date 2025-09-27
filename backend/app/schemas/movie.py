from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# TMDB Response Schemas
class TMDBMovie(BaseModel):
    """TMDB Movie data structure"""
    id: int
    title: str
    overview: Optional[str] = None
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    release_date: Optional[str] = None
    vote_average: Optional[float] = None
    vote_count: Optional[int] = None
    genre_ids: Optional[List[int]] = None
    popularity: Optional[float] = None

class TMDBTVShow(BaseModel):
    """TMDB TV Show data structure"""
    id: int
    name: str
    overview: Optional[str] = None
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    first_air_date: Optional[str] = None
    vote_average: Optional[float] = None
    vote_count: Optional[int] = None
    genre_ids: Optional[List[int]] = None
    popularity: Optional[float] = None

class TMDBWatchProvider(BaseModel):
    """TMDB Watch Provider data structure"""
    provider_id: int
    provider_name: str
    logo_path: Optional[str] = None
    display_priority: Optional[int] = None

class TMDBWatchProviders(BaseModel):
    """TMDB Watch Providers response"""
    results: dict  # Country code -> providers mapping

# User Interaction Schemas
class UserRatingCreate(BaseModel):
    """Create user rating"""
    tmdb_id: int = Field(..., description="TMDB movie/show ID")
    content_type: str = Field(..., description="'movie' or 'tv'")
    rating: int = Field(..., ge=1, le=10, description="Rating from 1 to 10")
    comment: Optional[str] = None

class UserRatingResponse(BaseModel):
    """User rating response"""
    id: int
    user_id: int
    tmdb_id: int
    content_type: str
    rating: int
    comment: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class UserWatchlistCreate(BaseModel):
    """Create user watchlist item"""
    tmdb_id: int = Field(..., description="TMDB movie/show ID")
    content_type: str = Field(..., description="'movie' or 'tv'")
    status: str = Field(..., description="'to_watch', 'watching', or 'completed'")

class UserWatchlistResponse(BaseModel):
    """User watchlist response"""
    id: int
    user_id: int
    tmdb_id: int
    content_type: str
    status: str
    added_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class UserWatchlistWithRatingResponse(BaseModel):
    """User watchlist item enriched with user's rating if exists"""
    id: int
    user_id: int
    tmdb_id: int
    content_type: str
    status: str
    added_at: datetime
    updated_at: Optional[datetime] = None
    user_rating: Optional[int] = None
    user_comment: Optional[str] = None
    
    class Config:
        from_attributes = True

# Recommendation Schemas
class EmotionBasedRecommendation(BaseModel):
    """Emotion-based recommendation request"""
    emotion: str = Field(..., description="User's current emotion")
    content_type: str = Field("movie", description="'movie', 'tv', or 'all'")
    page: int = Field(1, ge=1, description="Page number")

class HistoryBasedRecommendation(BaseModel):
    """History-based recommendation request"""
    content_type: str = Field("movie", description="'movie' or 'tv'")
    page: int = Field(1, ge=1, description="Page number")

class HybridRecommendation(BaseModel):
    """Hybrid recommendation request"""
    emotion: Optional[str] = Field(None, description="User's current emotion")
    content_type: str = Field("movie", description="'movie' or 'tv'")
    page: int = Field(1, ge=1, description="Page number")

class HybridRecommendationRequest(BaseModel):
    """Hybrid recommendation request with emotion text in body"""
    emotion_text: str = Field(..., description="User's emotional state text")
    content_type: str = Field("movie", description="Content type: 'movie', 'tv', or 'all'")
    page: int = Field(1, ge=1, description="Page number (1-4)")

class RecommendationResponse(BaseModel):
    """Recommendation response with TMDB data"""
    tmdb_id: int
    content_type: str
    recommendation_type: str
    score: float
    emotion_state: Optional[str] = None
    tmdb_data: Optional[TMDBMovie | TMDBTVShow] = None

# Emotion Analysis Schemas
class EmotionAnalysisRequest(BaseModel):
    """Emotion analysis request"""
    emotion_text: str = Field(..., description="Text to analyze for emotions")

class EmotionAnalysisResponse(BaseModel):
    """Emotion analysis response"""
    primary_emotion: str
    emotion_scores: Dict[str, float]
    emotional_intensity: float
    emotional_tone: str
    confidence: float

class ContentEmotionalToneRequest(BaseModel):
    """Content emotional tone analysis request"""
    tmdb_id: int = Field(..., description="TMDB content ID")
    content_type: str = Field(..., description="'movie' or 'tv'")

class ContentEmotionalToneResponse(BaseModel):
    """Content emotional tone analysis response"""
    primary_emotion: str
    secondary_emotions: List[str]
    emotional_intensity: float
    mood_improving: bool
    emotionally_cathartic: bool
    thought_provoking: bool
    confidence_score: float

# Feedback Schemas
class FeedbackStatsResponse(BaseModel):
    """Feedback statistics response schema"""
    total_feedbacks: int
    avg_emotional_impact: float
    avg_recommendation_accuracy: float
    mood_improvement_rate: float
    recommendation_rate: float

# Notification Schemas
class NotificationData(BaseModel):
    """Notification data structure"""
    user_id: int
    tmdb_id: int
    content_type: str
    title: str
    message: str
    notification_type: str
    scheduled_at: datetime
    emotion_state: Optional[str] = None

class NotificationHistoryItem(BaseModel):
    """Notification history item"""
    tmdb_id: int
    content_type: str
    title: str
    pre_viewing_emotion: Optional[str]
    post_viewing_emotion: Optional[str]
    emotional_impact_score: Optional[int]
    recommendation_accuracy: Optional[int]
    mood_improvement: Optional[bool]
    feedback_provided: bool
    notification_sent: bool
    created_at: datetime
    feedback_at: Optional[datetime]

class FeedbackSurveyQuestion(BaseModel):
    """Feedback survey question"""
    id: str
    type: str  # "emotion_select", "rating", "boolean", "text"
    question: str
    options: Optional[List[str]] = None  # For emotion_select
    min: Optional[int] = None  # For rating
    max: Optional[int] = None  # For rating

class FeedbackSurvey(BaseModel):
    """Feedback survey structure"""
    content: Dict[str, Any]
    pre_viewing_emotion: str
    questions: List[FeedbackSurveyQuestion]

# Emotion Profile Schemas
class EmotionInsightsResponse(BaseModel):
    """User emotion insights response"""
    success_rate: float
    total_recommendations: int
    successful_recommendations: int
    top_emotions: List[tuple]
    top_emotional_tones: List[tuple]
    recent_feedback_count: int
    learning_rate: float

class EmotionProfileUpdate(BaseModel):
    """Emotion profile update request"""
    learning_rate: float = Field(0.1, ge=0.01, le=1.0, description="Learning rate for preference updates")

# Statistics Schemas
class NotificationStatistics(BaseModel):
    """Notification and feedback statistics"""
    total_notifications_sent: int
    total_feedback_received: int
    feedback_rate_percentage: float
    average_emotional_impact: float
    average_recommendation_accuracy: float
    mood_improvement_rate_percentage: float 