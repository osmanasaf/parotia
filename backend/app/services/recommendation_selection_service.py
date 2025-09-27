import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.user_interaction import RecommendationSelection, UserWatchlist
from app.services.emotion_analysis_service import EmotionAnalysisService

logger = logging.getLogger(__name__)

class RecommendationSelectionService:
    """Service for managing recommendation selections (notification kaldırıldı)"""
    
    def __init__(self, db: Session):
        self.db = db
        self.emotion_service = EmotionAnalysisService(db)
    
    def select_recommendation(self, user_id: int, tmdb_id: int, content_type: str, 
                            recommendation_type: str, source: str, recommendation_score: float = None,
                            selected_rank: int = None) -> Dict[str, Any]:
        """User selects a recommendation - creates tracking and adds to watchlist"""
        try:
            # Generate unique session ID
            session_id = str(uuid.uuid4())
            
            # Create recommendation selection record
            selection = RecommendationSelection(
                user_id=user_id,
                tmdb_id=tmdb_id,
                content_type=content_type,
                recommendation_session_id=session_id,
                recommendation_type=recommendation_type,
                source=source,
                recommendation_score=recommendation_score,
                selected_rank=selected_rank
            )
            
            self.db.add(selection)
            
            # Add to watchlist
            watchlist_item = UserWatchlist(
                user_id=user_id,
                tmdb_id=tmdb_id,
                content_type=content_type,
                status="to_watch",
                from_recommendation=True,
                recommendation_type=recommendation_type,
                recommendation_score=recommendation_score
            )
            
            self.db.add(watchlist_item)
            self.db.commit()
            
            # Update selection with watchlist info
            selection.added_to_watchlist = True
            self.db.commit()
            
            logger.info(f"User {user_id} selected recommendation {tmdb_id} (type: {recommendation_type})")
            
            return {
                "success": True,
                "message": "Film seçildi ve watchlist'e eklendi",
                "data": {
                    "selection_id": selection.id,
                    "session_id": session_id,
                    "tmdb_id": tmdb_id,
                    "recommendation_type": recommendation_type,
                    "source": source,
                    "added_to_watchlist": True
                }
            }
            
        except Exception as e:
            logger.error(f"Error selecting recommendation: {str(e)}")
            self.db.rollback()
            return {"success": False, "error": str(e)}
    
    # Notification akışı kaldırıldı
    
    # Notification akışı kaldırıldı
    
    def mark_as_watched(self, user_id: int, tmdb_id: int, content_type: str) -> bool:
        """Mark a selected recommendation as watched"""
        try:
            # Find the selection
            selection = self.db.query(RecommendationSelection).filter(
                and_(
                    RecommendationSelection.user_id == user_id,
                    RecommendationSelection.tmdb_id == tmdb_id,
                    RecommendationSelection.content_type == content_type
                )
            ).first()
            
            if selection:
                selection.watched = True
                selection.watched_at = datetime.utcnow()
                self.db.commit()
                
                # Update watchlist status
                watchlist_item = self.db.query(UserWatchlist).filter(
                    and_(
                        UserWatchlist.user_id == user_id,
                        UserWatchlist.tmdb_id == tmdb_id,
                        UserWatchlist.content_type == content_type
                    )
                ).first()
                
                if watchlist_item:
                    watchlist_item.status = "completed"
                    self.db.commit()
                
                logger.info(f"Marked selection {selection.id} as watched")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error marking as watched: {str(e)}")
            return False
    
    def provide_feedback(self, selection_id: int, feedback_data: Dict[str, Any]) -> bool:
        """Provide feedback for a recommendation selection"""
        try:
            selection = self.db.query(RecommendationSelection).filter(
                RecommendationSelection.id == selection_id
            ).first()
            
            if not selection:
                return False
            
            # Update selection with feedback
            selection.feedback_provided = True
            selection.feedback_provided_at = datetime.utcnow()
            
            # Store feedback data (you can extend this based on your needs)
            # For now, we'll just mark it as provided
            
            self.db.commit()
            
            # Update emotion profile based on feedback
            self.emotion_service.update_user_emotion_profile_realtime(
                selection.user_id, selection.tmdb_id, selection.content_type
            )
            
            logger.info(f"Feedback provided for selection {selection_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error providing feedback: {str(e)}")
            return False
    
    def get_user_selections(self, user_id: int, limit: int = 20) -> list:
        """Get user's recommendation selections"""
        try:
            selections = self.db.query(RecommendationSelection).filter(
                RecommendationSelection.user_id == user_id
            ).order_by(RecommendationSelection.created_at.desc()).limit(limit).all()
            
            return selections
            
        except Exception as e:
            logger.error(f"Error getting user selections: {str(e)}")
            return []
    
    def get_selection_stats(self, user_id: int) -> Dict[str, Any]:
        """Get statistics about user's recommendation selections"""
        try:
            selections = self.db.query(RecommendationSelection).filter(
                RecommendationSelection.user_id == user_id
            ).all()
            
            if not selections:
                return {
                    "total_selections": 0,
                    "watched_count": 0,
                    "feedback_provided": 0,
                    "by_recommendation_type": {}
                }
            
            total = len(selections)
            watched = sum(1 for s in selections if s.watched)
            feedback = sum(1 for s in selections if s.feedback_provided)
            
            # Group by recommendation type
            type_stats = {}
            for selection in selections:
                rec_type = selection.recommendation_type
                if rec_type not in type_stats:
                    type_stats[rec_type] = {"total": 0, "watched": 0, "feedback": 0}
                
                type_stats[rec_type]["total"] += 1
                if selection.watched:
                    type_stats[rec_type]["watched"] += 1
                if selection.feedback_provided:
                    type_stats[rec_type]["feedback"] += 1
            
            return {
                "total_selections": total,
                "watched_count": watched,
                "feedback_provided": feedback,
                "watch_rate": round((watched / total) * 100, 2),
                "feedback_rate": round((feedback / total) * 100, 2),
                "by_recommendation_type": type_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting selection stats: {str(e)}")
            return {} 