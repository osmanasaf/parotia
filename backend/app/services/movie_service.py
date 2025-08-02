import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.core.tmdb_service import TMDBServiceFactory
from app.repositories.user_interaction_repository import (
    UserRatingRepository, UserWatchlistRepository, UserRecommendationRepository
)
from app.schemas.movie import (
    UserRatingCreate, UserRatingResponse, UserWatchlistCreate, UserWatchlistResponse,
    EmotionBasedRecommendation, HistoryBasedRecommendation, HybridRecommendation
)
from app.core.exceptions import UserNotFoundException
from app.core.config import get_settings
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

class MovieService:
    """Service for movie operations with TMDB integration"""
    
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        
        # Initialize repositories
        self.rating_repo = UserRatingRepository(db)
        self.watchlist_repo = UserWatchlistRepository(db)
        
        # Initialize TMDB service
        self.tmdb_movie_service = TMDBServiceFactory.create_movie_service(
            api_key=self.settings.TMDB_API_KEY
        )
    
    def get_popular_movies(self, page: int = 1) -> Dict[str, Any]:
        """Get popular movies from TMDB"""
        try:
            response = self.tmdb_movie_service.get_popular_movies(page)
            
            if response.success:
                return {
                    "success": True,
                    "data": response.data,
                    "page": page
                }
            else:
                return {"success": False, "error": "Failed to fetch popular movies"}
        except Exception as e:
            logger.error(f"Error fetching popular movies: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_movie_details(self, tmdb_id: int) -> Dict[str, Any]:
        """Get movie details from TMDB"""
        try:
            response = self.tmdb_movie_service.get_movie_details(tmdb_id)
            
            if response.success:
                return {
                    "success": True,
                    "data": response.data
                }
            else:
                return {"success": False, "error": "Failed to fetch movie details"}
        except Exception as e:
            logger.error(f"Error fetching movie details: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def search_movies(self, query: str, page: int = 1) -> Dict[str, Any]:
        """Search movies on TMDB"""
        try:
            response = self.tmdb_movie_service.search_movies(query, page)
            if response.success:
                return {
                    "success": True,
                    "data": response.data,
                    "query": query,
                    "page": page
                }
            else:
                return {"success": False, "error": "Failed to search movies"}
        except Exception as e:
            logger.error(f"Error searching movies: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_movie_watch_providers(self, tmdb_id: int) -> Dict[str, Any]:
        """Get movie watch providers from TMDB"""
        try:
            response = self.tmdb_movie_service.get_movie_watch_providers(tmdb_id)
            if response.success:
                return {
                    "success": True,
                    "data": response.data
                }
            else:
                return {"success": False, "error": "Failed to fetch watch providers"}
        except Exception as e:
            logger.error(f"Error fetching watch providers: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def rate_movie(self, user_id: int, rating_data: UserRatingCreate) -> UserRatingResponse:
        """Rate a movie"""
        try:
            rating = self.rating_repo.create_or_update_rating(
                user_id=user_id,
                tmdb_id=rating_data.tmdb_id,
                content_type="movie",
                rating=rating_data.rating,
                comment=rating_data.comment
            )
            return UserRatingResponse.from_orm(rating)
        except Exception as e:
            logger.error(f"Error rating movie: {str(e)}")
            raise
    
    def get_user_movie_ratings(self, user_id: int) -> List[UserRatingResponse]:
        """Get user's movie ratings"""
        try:
            ratings = self.rating_repo.get_user_ratings(user_id, "movie")
            return [UserRatingResponse.from_orm(rating) for rating in ratings]
        except Exception as e:
            logger.error(f"Error getting user movie ratings: {str(e)}")
            raise
    
    def add_movie_to_watchlist(self, user_id: int, watchlist_data: UserWatchlistCreate) -> UserWatchlistResponse:
        """Add movie to user's watchlist"""
        try:
            watchlist_item = self.watchlist_repo.add_to_watchlist(
                user_id=user_id,
                tmdb_id=watchlist_data.tmdb_id,
                content_type="movie",
                status=watchlist_data.status
            )
            return UserWatchlistResponse.from_orm(watchlist_item)
        except Exception as e:
            logger.error(f"Error adding movie to watchlist: {str(e)}")
            raise
    
    def get_user_movie_watchlist(self, user_id: int, status: Optional[str] = None) -> List[UserWatchlistResponse]:
        """Get user's movie watchlist"""
        try:
            watchlist = self.watchlist_repo.get_user_watchlist(user_id, "movie", status)
            return [UserWatchlistResponse.from_orm(item) for item in watchlist]
        except Exception as e:
            logger.error(f"Error getting user movie watchlist: {str(e)}")
            raise
    
    def update_movie_watchlist_status(self, user_id: int, tmdb_id: int, status: str) -> Optional[UserWatchlistResponse]:
        """Update movie watchlist item status"""
        try:
            item = self.watchlist_repo.update_watchlist_status(user_id, tmdb_id, "movie", status)
            if item:
                return UserWatchlistResponse.from_orm(item)
            return None
        except Exception as e:
            logger.error(f"Error updating movie watchlist status: {str(e)}")
            raise
    
 