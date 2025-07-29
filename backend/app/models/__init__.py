from app.db import Base
from .movie import Movie
from .user import User
from .comment import Comment
from .watchlist import Watchlist
from .feedback import RecommendationFeedback

__all__ = ['Movie', 'User', 'Comment', 'Watchlist', 'RecommendationFeedback'] 