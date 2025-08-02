from app.db import Base
from .movie import Movie
from .user import User
from .comment import Comment
from .watchlist import Watchlist
from .feedback import RecommendationFeedback
from .content_embeddings import ContentEmbedding
from .user_interaction import (
    UserRating, UserWatchlist, UserRecommendation, 
    UserEmotionalProfile, RecommendationSelection
)

__all__ = [
    'Movie', 'User', 'Comment', 'Watchlist', 'RecommendationFeedback', 
    'ContentEmbedding', 'UserRating', 'UserWatchlist', 'UserRecommendation', 
    'UserEmotionalProfile', 'RecommendationSelection'
] 