import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.user_interaction import UserRecommendation, UserWatchlist
from app.services.emotion_analysis_service import EmotionAnalysisService
from app.core.tmdb_service import TMDBServiceFactory

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for managing notifications and feedback requests"""
    
    def __init__(self, db: Session):
        self.db = db
        self.emotion_service = EmotionAnalysisService(db)
        self.tmdb_service = TMDBServiceFactory.create_service()
    
    def schedule_feedback_notifications(self) -> List[Dict[str, Any]]:
        """Schedule feedback notifications for users who watched recommendations"""
        try:
            # Get completed watchlist items that came from recommendations
            completed_recommendations = self.db.query(UserWatchlist).filter(
                and_(
                    UserWatchlist.status == "completed",
                    UserWatchlist.from_recommendation == True
                )
            ).all()
            
            scheduled_notifications = []
            for watchlist_item in completed_recommendations:
                # Check if notification already sent
                existing_feedback = self.db.query(PostViewingFeedback).filter(
                    and_(
                        PostViewingFeedback.user_id == watchlist_item.user_id,
                        PostViewingFeedback.tmdb_id == watchlist_item.tmdb_id,
                        PostViewingFeedback.content_type == watchlist_item.content_type,
                        PostViewingFeedback.notification_sent == True
                    )
                ).first()
                
                if existing_feedback:
                    continue  # Notification already sent
                
                # Create notification data
                notification_data = self._create_notification_data_from_watchlist(watchlist_item)
                
                # Mark as notified
                self._mark_recommendation_notified_from_watchlist(watchlist_item)
                
                scheduled_notifications.append(notification_data)
            
            return scheduled_notifications
            
        except Exception as e:
            logger.error(f"Error scheduling feedback notifications: {str(e)}")
            return []
    
    def _create_notification_data(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        """Create notification data with personalized message"""
        try:
            # Get content details from TMDB
            content_type = notification["content_type"]
            tmdb_id = notification["tmdb_id"]
            
            if content_type == "movie":
                content_data = self.tmdb_service.movie_service.get_movie_details(tmdb_id)
            else:
                content_data = self.tmdb_service.tv_service.get_tv_show_details(tmdb_id)
            
            # Create personalized message based on emotion
            emotion_state = notification.get("emotion_state", "")
            personalized_message = self._generate_personalized_message(
                emotion_state, content_data, content_type
            )
            
            return {
                "user_id": notification["user_id"],
                "tmdb_id": tmdb_id,
                "content_type": content_type,
                "title": content_data.get("title", "Unknown") if content_data else "Unknown",
                "message": personalized_message,
                "notification_type": "feedback_request",
                "scheduled_at": datetime.utcnow(),
                "emotion_state": emotion_state
            }
            
        except Exception as e:
            logger.error(f"Error creating notification data: {str(e)}")
            return {
                "user_id": notification["user_id"],
                "tmdb_id": notification["tmdb_id"],
                "content_type": notification["content_type"],
                "title": "Unknown",
                "message": "Film hakkında ne düşünüyorsun?",
                "notification_type": "feedback_request",
                "scheduled_at": datetime.utcnow(),
                "emotion_state": notification.get("emotion_state", "")
            }
    
    def _generate_personalized_message(self, emotion_state: str, content_data: Dict, content_type: str) -> str:
        """Generate personalized notification message based on emotion and content"""
        title = content_data.get("title", "bu film") if content_data else "bu film"
        
        # Emotion-based messages
        emotion_messages = {
            "sad": f"💙 {title} izledikten sonra kendini nasıl hissettin? Umudunuzu geri getirdi mi?",
            "happy": f"😊 {title} ile eğlenceniz devam etti mi? Beklentilerinizi karşıladı mı?",
            "excited": f"🎬 {title} heyecanınızı sürdürdü mü? Beklediğiniz gibi miydi?",
            "lonely": f"🤗 {title} size yalnızlığınızı unutturdu mu? Daha iyi hissettiniz mi?",
            "anxious": f"🧘 {title} kaygılarınızı azalttı mı? Rahatladınız mı?",
            "angry": f"😤 {title} öfkenizi yatıştırdı mı? Daha sakin hissettiniz mi?",
            "romantic": f"💕 {title} romantik ruh halinizi besledi mi? Beklentilerinizi karşıladı mı?",
            "inspired": f"✨ {title} ilhamınızı artırdı mı? Motivasyonunuzu yükseltti mi?",
            "calm": f"😌 {title} huzurunuzu korudu mu? Beklediğiniz gibi sakinleştirici miydi?",
            "nostalgic": f"📺 {title} nostalji duygularınızı tatmin etti mi? Geçmişe güzel bir yolculuk oldu mu?"
        }
        
        # Default message if emotion not found
        default_message = f"🎭 {title} hakkında ne düşünüyorsun? Duygularınızı paylaşır mısınız?"
        
        return emotion_messages.get(emotion_state.lower(), default_message)
    
    def _create_notification_data_from_watchlist(self, watchlist_item) -> Dict[str, Any]:
        """Create notification data from watchlist item"""
        try:
            # Get content details from TMDB
            content_type = watchlist_item.content_type
            tmdb_id = watchlist_item.tmdb_id
            
            if content_type == "movie":
                content_data = self.tmdb_service.movie_service.get_movie_details(tmdb_id)
            else:
                content_data = self.tmdb_service.tv_service.get_tv_show_details(tmdb_id)
            
            # Create personalized message based on recommendation type
            recommendation_type = watchlist_item.recommendation_type or "unknown"
            personalized_message = self._generate_personalized_message_from_recommendation(
                recommendation_type, content_data, content_type
            )
            
            return {
                "user_id": watchlist_item.user_id,
                "tmdb_id": tmdb_id,
                "content_type": content_type,
                "title": content_data.get("title", "Unknown") if content_data else "Unknown",
                "message": personalized_message,
                "notification_type": "feedback_request",
                "scheduled_at": datetime.utcnow(),
                "recommendation_type": recommendation_type,
                "recommendation_score": watchlist_item.recommendation_score
            }
            
        except Exception as e:
            logger.error(f"Error creating notification data from watchlist: {str(e)}")
            return {
                "user_id": watchlist_item.user_id,
                "tmdb_id": watchlist_item.tmdb_id,
                "content_type": watchlist_item.content_type,
                "title": "Unknown",
                "message": "Film hakkında ne düşünüyorsun?",
                "notification_type": "feedback_request",
                "scheduled_at": datetime.utcnow(),
                "recommendation_type": watchlist_item.recommendation_type or "unknown"
            }
    
    def _generate_personalized_message_from_recommendation(self, recommendation_type: str, content_data: Dict, content_type: str) -> str:
        """Generate personalized message based on recommendation type"""
        title = content_data.get("title", "bu film") if content_data else "bu film"
        
        # Recommendation type-based messages
        type_messages = {
            "emotion_based": f"😊 Duygu durumunuza göre önerdiğimiz {title} nasıldı? Beklentilerinizi karşıladı mı?",
            "history_based": f"📺 İzleme geçmişinize göre önerdiğimiz {title} beğendiniz mi?",
            "hybrid": f"🎯 Duygu durumunuz ve geçmişinizi birleştirerek önerdiğimiz {title} nasıldı?",
            "profile_based": f"👤 Profilinize göre önerdiğimiz {title} beklentilerinizi karşıladı mı?",
            "current_emotion": f"💭 Anlık duygu durumunuza göre önerdiğimiz {title} nasıldı?"
        }
        
        return type_messages.get(recommendation_type, f"🎬 {title} hakkında ne düşünüyorsun?")
    
    def _mark_recommendation_notified_from_watchlist(self, watchlist_item) -> None:
        """Mark recommendation as notified from watchlist item"""
        try:
            # Create or update PostViewingFeedback record
            existing_feedback = self.db.query(PostViewingFeedback).filter(
                and_(
                    PostViewingFeedback.user_id == watchlist_item.user_id,
                    PostViewingFeedback.tmdb_id == watchlist_item.tmdb_id,
                    PostViewingFeedback.content_type == watchlist_item.content_type
                )
            ).first()
            
            if not existing_feedback:
                feedback = PostViewingFeedback(
                    user_id=watchlist_item.user_id,
                    tmdb_id=watchlist_item.tmdb_id,
                    content_type=watchlist_item.content_type,
                    pre_viewing_emotion=watchlist_item.recommendation_type,  # Use recommendation type as emotion context
                    notification_sent=True,
                    notification_sent_at=datetime.utcnow()
                )
                self.db.add(feedback)
            else:
                existing_feedback.notification_sent = True
                existing_feedback.notification_sent_at = datetime.utcnow()
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error marking recommendation notified from watchlist: {str(e)}")
            self.db.rollback()
    
    def _mark_recommendation_notified(self, notification: Dict[str, Any]) -> None:
        """Mark recommendation as notified to avoid duplicate notifications"""
        try:
            # Create or update PostViewingFeedback record
            existing_feedback = self.db.query(PostViewingFeedback).filter(
                and_(
                    PostViewingFeedback.user_id == notification["user_id"],
                    PostViewingFeedback.tmdb_id == notification["tmdb_id"],
                    PostViewingFeedback.content_type == notification["content_type"]
                )
            ).first()
            
            if not existing_feedback:
                feedback = PostViewingFeedback(
                    user_id=notification["user_id"],
                    tmdb_id=notification["tmdb_id"],
                    content_type=notification["content_type"],
                    pre_viewing_emotion=notification.get("emotion_state"),
                    notification_sent=True,
                    notification_sent_at=datetime.utcnow()
                )
                self.db.add(feedback)
            else:
                existing_feedback.notification_sent = True
                existing_feedback.notification_sent_at = datetime.utcnow()
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error marking recommendation notified: {str(e)}")
            self.db.rollback()
    
    def send_feedback_reminder(self, user_id: int, tmdb_id: int, content_type: str) -> bool:
        """Send a reminder for feedback if user hasn't responded"""
        try:
            # Check if user has already provided feedback
            existing_feedback = self.db.query(PostViewingFeedback).filter(
                and_(
                    PostViewingFeedback.user_id == user_id,
                    PostViewingFeedback.tmdb_id == tmdb_id,
                    PostViewingFeedback.content_type == content_type,
                    PostViewingFeedback.feedback_provided == True
                )
            ).first()
            
            if existing_feedback:
                return False  # User already provided feedback
            
            # Check if reminder was sent recently (within 3 days)
            recent_reminder = self.db.query(PostViewingFeedback).filter(
                and_(
                    PostViewingFeedback.user_id == user_id,
                    PostViewingFeedback.tmdb_id == tmdb_id,
                    PostViewingFeedback.content_type == content_type,
                    PostViewingFeedback.notification_sent_at >= datetime.utcnow() - timedelta(days=3)
                )
            ).first()
            
            if recent_reminder:
                return False  # Reminder sent recently
            
            # Send reminder
            reminder_data = {
                "user_id": user_id,
                "tmdb_id": tmdb_id,
                "content_type": content_type,
                "message": "💭 Film hakkında düşüncelerinizi paylaşmak ister misiniz?",
                "notification_type": "feedback_reminder"
            }
            
            # Update notification timestamp
            feedback_record = self.db.query(PostViewingFeedback).filter(
                and_(
                    PostViewingFeedback.user_id == user_id,
                    PostViewingFeedback.tmdb_id == tmdb_id,
                    PostViewingFeedback.content_type == content_type
                )
            ).first()
            
            if feedback_record:
                feedback_record.notification_sent_at = datetime.utcnow()
                self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending feedback reminder: {str(e)}")
            return False
    
    def get_user_notification_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's notification history"""
        try:
            feedback_records = self.db.query(PostViewingFeedback).filter(
                PostViewingFeedback.user_id == user_id
            ).order_by(PostViewingFeedback.created_at.desc()).limit(limit).all()
            
            history = []
            for record in feedback_records:
                # Get content details
                content_type = record.content_type
                tmdb_id = record.tmdb_id
                
                if content_type == "movie":
                    content_data = self.tmdb_service.movie_service.get_movie_details(tmdb_id)
                else:
                    content_data = self.tmdb_service.tv_service.get_tv_show_details(tmdb_id)
                
                history.append({
                    "tmdb_id": tmdb_id,
                    "content_type": content_type,
                    "title": content_data.get("title", "Unknown") if content_data else "Unknown",
                    "pre_viewing_emotion": record.pre_viewing_emotion,
                    "post_viewing_emotion": record.post_viewing_emotion,
                    "emotional_impact_score": record.emotional_impact_score,
                    "recommendation_accuracy": record.recommendation_accuracy,
                    "mood_improvement": record.mood_improvement,
                    "feedback_provided": record.feedback_provided,
                    "notification_sent": record.notification_sent,
                    "created_at": record.created_at,
                    "feedback_at": record.feedback_at
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting user notification history: {str(e)}")
            return []
    
    def get_notification_statistics(self) -> Dict[str, Any]:
        """Get statistics about notifications and feedback"""
        try:
            total_notifications = self.db.query(PostViewingFeedback).filter(
                PostViewingFeedback.notification_sent == True
            ).count()
            
            total_feedback = self.db.query(PostViewingFeedback).filter(
                PostViewingFeedback.feedback_provided == True
            ).count()
            
            feedback_rate = (total_feedback / max(total_notifications, 1)) * 100
            
            # Average emotional impact score
            avg_impact = self.db.query(PostViewingFeedback.emotional_impact_score).filter(
                PostViewingFeedback.emotional_impact_score.isnot(None)
            ).scalar()
            
            # Average recommendation accuracy
            avg_accuracy = self.db.query(PostViewingFeedback.recommendation_accuracy).filter(
                PostViewingFeedback.recommendation_accuracy.isnot(None)
            ).scalar()
            
            # Mood improvement rate
            mood_improvements = self.db.query(PostViewingFeedback).filter(
                PostViewingFeedback.mood_improvement == True
            ).count()
            
            mood_improvement_rate = (mood_improvements / max(total_feedback, 1)) * 100
            
            return {
                "total_notifications_sent": total_notifications,
                "total_feedback_received": total_feedback,
                "feedback_rate_percentage": round(feedback_rate, 2),
                "average_emotional_impact": round(avg_impact, 2) if avg_impact else 0,
                "average_recommendation_accuracy": round(avg_accuracy, 2) if avg_accuracy else 0,
                "mood_improvement_rate_percentage": round(mood_improvement_rate, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting notification statistics: {str(e)}")
            return {}
    
    def create_feedback_survey(self, user_id: int, tmdb_id: int, content_type: str) -> Dict[str, Any]:
        """Create a feedback survey for user"""
        try:
            # Get content details
            if content_type == "movie":
                content_data = self.tmdb_service.movie_service.get_movie_details(tmdb_id)
            else:
                content_data = self.tmdb_service.tv_service.get_tv_show_details(tmdb_id)
            
            # Get user's pre-viewing emotion
            feedback_record = self.db.query(PostViewingFeedback).filter(
                and_(
                    PostViewingFeedback.user_id == user_id,
                    PostViewingFeedback.tmdb_id == tmdb_id,
                    PostViewingFeedback.content_type == content_type
                )
            ).first()
            
            pre_viewing_emotion = feedback_record.pre_viewing_emotion if feedback_record else "unknown"
            
            survey = {
                "content": {
                    "tmdb_id": tmdb_id,
                    "content_type": content_type,
                    "title": content_data.get("title", "Unknown") if content_data else "Unknown",
                    "overview": content_data.get("overview", "") if content_data else ""
                },
                "pre_viewing_emotion": pre_viewing_emotion,
                "questions": [
                    {
                        "id": "post_viewing_emotion",
                        "type": "emotion_select",
                        "question": "Film izledikten sonra kendinizi nasıl hissettiniz?",
                        "options": ["mutlu", "üzgün", "heyecanlı", "sakin", "ilham almış", "düşünceli", "rahatlamış", "diğer"]
                    },
                    {
                        "id": "emotional_impact_score",
                        "type": "rating",
                        "question": "Bu film duygularınızı ne kadar etkiledi? (1-10)",
                        "min": 1,
                        "max": 10
                    },
                    {
                        "id": "recommendation_accuracy",
                        "type": "rating",
                        "question": "Bu öneri beklentilerinizi ne kadar karşıladı? (1-10)",
                        "min": 1,
                        "max": 10
                    },
                    {
                        "id": "mood_improvement",
                        "type": "boolean",
                        "question": "Bu film ruh halinizi iyileştirdi mi?"
                    },
                    {
                        "id": "emotional_catharsis",
                        "type": "boolean",
                        "question": "Bu film size duygusal bir rahatlama sağladı mı?"
                    },
                    {
                        "id": "would_recommend_to_others",
                        "type": "boolean",
                        "question": "Bu filmi başkalarına önerir misiniz?"
                    },
                    {
                        "id": "additional_comments",
                        "type": "text",
                        "question": "Ek düşünceleriniz var mı? (İsteğe bağlı)"
                    }
                ]
            }
            
            return survey
            
        except Exception as e:
            logger.error(f"Error creating feedback survey: {str(e)}")
            return {} 