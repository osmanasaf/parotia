import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.core.tmdb_service import TMDBServiceFactory
from app.repositories.user_interaction_repository import (
    UserRatingRepository, UserWatchlistRepository
)
from app.schemas.movie import (
    UserRatingCreate, UserRatingResponse, UserWatchlistCreate, UserWatchlistResponse
)
from app.core.exceptions import UserNotFoundException
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class TVService:
    """Service for TV show operations with TMDB integration"""
    
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        
        # Initialize repositories
        self.rating_repo = UserRatingRepository(db)
        self.watchlist_repo = UserWatchlistRepository(db)
        
        # Initialize TMDB service
        self.tmdb_tv_service = TMDBServiceFactory.create_tv_service(
            api_key=self.settings.TMDB_API_KEY
        )
    
    def get_popular_tv_shows(self, page: int = 1) -> Dict[str, Any]:
        """Get popular TV shows from TMDB"""
        try:
            response = self.tmdb_tv_service.get_popular_tv_shows(page)
            
            if response.success:
                return {
                    "success": True,
                    "data": response.data,
                    "page": page
                }
            else:
                return {"success": False, "error": "Failed to fetch popular TV shows"}
        except Exception as e:
            logger.error(f"Error fetching popular TV shows: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_tv_show_details(self, tmdb_id: int) -> Dict[str, Any]:
        """Get TV show details from TMDB"""
        try:
            response = self.tmdb_tv_service.get_tv_show_details(tmdb_id)
            
            if response.success:
                return {
                    "success": True,
                    "data": response.data
                }
            else:
                return {"success": False, "error": "Failed to fetch TV show details"}
        except Exception as e:
            logger.error(f"Error fetching TV show details: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def search_tv_shows(self, query: str, page: int = 1) -> Dict[str, Any]:
        """Search TV shows on TMDB"""
        try:
            response = self.tmdb_tv_service.search_tv_shows(query, page)
            if response.success:
                return {
                    "success": True,
                    "data": response.data,
                    "query": query,
                    "page": page
                }
            else:
                return {"success": False, "error": "Failed to search TV shows"}
        except Exception as e:
            logger.error(f"Error searching TV shows: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def rate_tv_show(self, user_id: int, rating_data: UserRatingCreate) -> UserRatingResponse:
        """Rate a TV show"""
        try:
            rating = self.rating_repo.create_or_update_rating(
                user_id=user_id,
                tmdb_id=rating_data.tmdb_id,
                content_type="tv",
                rating=rating_data.rating,
                comment=rating_data.comment
            )
            return UserRatingResponse.from_orm(rating)
        except Exception as e:
            logger.error(f"Error rating TV show: {str(e)}")
            raise
    
    def get_user_tv_ratings(self, user_id: int) -> List[UserRatingResponse]:
        """Get user's TV show ratings"""
        try:
            ratings = self.rating_repo.get_user_ratings(user_id, "tv")
            return [UserRatingResponse.from_orm(rating) for rating in ratings]
        except Exception as e:
            logger.error(f"Error getting user TV ratings: {str(e)}")
            raise
    
    def add_tv_show_to_watchlist(self, user_id: int, watchlist_data: UserWatchlistCreate) -> UserWatchlistResponse:
        """Add TV show to user's watchlist"""
        try:
            watchlist_item = self.watchlist_repo.add_to_watchlist(
                user_id=user_id,
                tmdb_id=watchlist_data.tmdb_id,
                content_type="tv",
                status=watchlist_data.status
            )
            return UserWatchlistResponse.from_orm(watchlist_item)
        except Exception as e:
            logger.error(f"Error adding TV show to watchlist: {str(e)}")
            raise
    
    def get_user_tv_watchlist(self, user_id: int, status: Optional[str] = None) -> List[UserWatchlistResponse]:
        """Get user's TV show watchlist"""
        try:
            watchlist = self.watchlist_repo.get_user_watchlist(user_id, "tv", status)
            return [UserWatchlistResponse.from_orm(item) for item in watchlist]
        except Exception as e:
            logger.error(f"Error getting user TV watchlist: {str(e)}")
            raise
    
    def update_tv_watchlist_status(self, user_id: int, tmdb_id: int, status: str) -> Optional[UserWatchlistResponse]:
        """Update TV show watchlist item status"""
        try:
            item = self.watchlist_repo.update_watchlist_status(user_id, tmdb_id, "tv", status)
            if item:
                return UserWatchlistResponse.from_orm(item)
            return None
        except Exception as e:
            logger.error(f"Error updating TV watchlist status: {str(e)}")
            raise 