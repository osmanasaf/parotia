from typing import Optional, List
from sqlalchemy.orm import Session
from app.repositories.base_repository import BaseRepository
from app.models.user_interaction import UserRating, UserWatchlist, UserRecommendation

class UserRatingRepository(BaseRepository[UserRating]):
    """Repository for user ratings"""
    
    def __init__(self, db: Session):
        super().__init__(UserRating, db)
    
    def get_user_rating(self, user_id: int, tmdb_id: int, content_type: str) -> Optional[UserRating]:
        """Get user's rating for specific content"""
        return self.filter_one_by(
            user_id=user_id,
            tmdb_id=tmdb_id,
            content_type=content_type
        )
    
    def get_user_ratings(self, user_id: int, content_type: Optional[str] = None) -> List[UserRating]:
        """Get all ratings for a user"""
        filters = {"user_id": user_id}
        if content_type:
            filters["content_type"] = content_type
        return self.filter_by(**filters)
    
    def create_or_update_rating(self, user_id: int, tmdb_id: int, content_type: str, rating: int, comment: Optional[str] = None) -> UserRating:
        """Create or update user rating"""
        existing_rating = self.get_user_rating(user_id, tmdb_id, content_type)
        
        if existing_rating:
            # Update existing rating
            return self.update(existing_rating, {
                "rating": rating,
                "comment": comment
            })
        else:
            # Create new rating
            return self.create({
                "user_id": user_id,
                "tmdb_id": tmdb_id,
                "content_type": content_type,
                "rating": rating,
                "comment": comment
            })

class UserWatchlistRepository(BaseRepository[UserWatchlist]):
    """Repository for user watchlist"""
    
    def __init__(self, db: Session):
        super().__init__(UserWatchlist, db)
    
    def get_user_watchlist(self, user_id: int, content_type: Optional[str] = None, status: Optional[str] = None) -> List[UserWatchlist]:
        """Get user's watchlist"""
        filters = {"user_id": user_id}
        if content_type:
            filters["content_type"] = content_type
        if status:
            filters["status"] = status
        return self.filter_by(**filters)
    
    def add_to_watchlist(self, user_id: int, tmdb_id: int, content_type: str, status: str = "to_watch") -> UserWatchlist:
        """Add content to user's watchlist"""
        # Check if already exists
        existing = self.filter_one_by(
            user_id=user_id,
            tmdb_id=tmdb_id,
            content_type=content_type
        )
        
        if existing:
            # Update status
            return self.update(existing, {"status": status})
        else:
            # Create new watchlist item
            return self.create({
                "user_id": user_id,
                "tmdb_id": tmdb_id,
                "content_type": content_type,
                "status": status
            })
    
    def update_watchlist_status(self, user_id: int, tmdb_id: int, content_type: str, status: str) -> Optional[UserWatchlist]:
        """Update watchlist item status"""
        item = self.filter_one_by(
            user_id=user_id,
            tmdb_id=tmdb_id,
            content_type=content_type
        )
        
        if item:
            return self.update(item, {"status": status})
        return None

class UserRecommendationRepository(BaseRepository[UserRecommendation]):
    """Repository for user recommendations"""
    
    def __init__(self, db: Session):
        super().__init__(UserRecommendation, db)
    
    def save_recommendation(self, user_id: int, tmdb_id: int, content_type: str, recommendation_type: str, 
                          emotion_state: Optional[str] = None, score: Optional[float] = None) -> UserRecommendation:
        """Save a recommendation for user"""
        return self.create({
            "user_id": user_id,
            "tmdb_id": tmdb_id,
            "content_type": content_type,
            "recommendation_type": recommendation_type,
            "emotion_state": emotion_state,
            "score": score
        })
    
    def get_user_recommendations(self, user_id: int, recommendation_type: Optional[str] = None, 
                               viewed: Optional[bool] = None) -> List[UserRecommendation]:
        """Get user's recommendations"""
        filters = {"user_id": user_id}
        if recommendation_type:
            filters["recommendation_type"] = recommendation_type
        if viewed is not None:
            filters["viewed"] = viewed
        return self.filter_by(**filters)
    
    def mark_as_viewed(self, recommendation_id: int) -> bool:
        """Mark recommendation as viewed"""
        recommendation = self.get(recommendation_id)
        if recommendation:
            self.update(recommendation, {"viewed": True})
            return True
        return False 