import logging
import numpy as np
from typing import Dict, List, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.user_interaction import (
    UserRating, UserWatchlist, UserRecommendation, UserEmotionalProfile, RecommendationSelection
)  # PostViewingFeedback kaldır
from app.core.tmdb_service import TMDBServiceFactory

logger = logging.getLogger(__name__)

class EmotionAnalysisService:
    def __init__(self, db: Session):
        self.db = db
        self.tmdb_service = TMDBServiceFactory.create_service()
        self.embedding_service = None
    
    def analyze_user_emotion(self, emotion_text: str) -> Dict[str, Any]:
        try:
            self._ensure_embedding_service()
            # Model supports Turkish and 50+ languages natively - no translation needed
            emotion_embedding = self.embedding_service.encode_text(emotion_text)
            similar_content = self.embedding_service.search_similar_content(
                query_embedding=emotion_embedding,
                top_k=10,
                content_type="movie"
            )
            emotional_profile = self._calculate_emotional_profile_from_content(similar_content)
            
            return {
                "emotion_embedding": emotion_embedding.tolist(),
                "similar_content_count": len(similar_content),
                "emotional_profile": emotional_profile,
                "confidence": min(1.0, len(similar_content) / 10.0)
            }
        except Exception as e:
            logger.error(f"Error analyzing user emotion: {str(e)}")
            return self._get_default_emotion_analysis()
    
    def _calculate_emotional_profile_from_content(self, similar_content: List[Dict]) -> Dict[str, Any]:
        if not similar_content:
            return {}
        
        # Items returned from EmbeddingService carry 'embedding_vector' when cached.
        embeddings = [item.get('embedding_vector', []) for item in similar_content if item.get('embedding_vector')]
        if not embeddings:
            return {}
        
        avg_embedding = np.mean(embeddings, axis=0)
        emotional_characteristics = {
            "intensity": self._calculate_content_intensity(similar_content),
            "complexity": self._calculate_content_complexity(similar_content),
            "mood_improving": self._calculate_mood_improving_score(similar_content),
            "thought_provoking": self._calculate_thought_provoking_score(similar_content)
        }
        
        return {
            "average_embedding": avg_embedding.tolist(),
            "characteristics": emotional_characteristics,
            "content_count": len(similar_content)
        }
    
    def get_user_emotion_from_watched_content(self, user_id: int, content_type: str = "movie") -> Dict[str, Any]:
        try:
            from app.repositories.user_interaction_repository import UserRatingRepository, UserWatchlistRepository
            rating_repo = UserRatingRepository(self.db)
            watchlist_repo = UserWatchlistRepository(self.db)
            
            # Get rated content
            rated_content = rating_repo.get_user_ratings(user_id, content_type)
            
            # Get completed watchlist items
            completed_watchlist = watchlist_repo.get_user_watchlist(user_id, content_type, "completed")
            
            # Combine both sources
            watched_content = []
            
            # Add rated content
            for content in rated_content:
                watched_content.append({
                    'tmdb_id': content.tmdb_id,
                    'content_type': content.content_type,
                    'rating': content.rating,
                    'comment': content.comment
                })
            
            # Add completed watchlist items (with default rating 7.0)
            for item in completed_watchlist:
                # Check if not already in rated content
                if not any(c['tmdb_id'] == item.tmdb_id for c in watched_content):
                    watched_content.append({
                        'tmdb_id': item.tmdb_id,
                        'content_type': item.content_type,
                        'rating': 7.0,  # Default rating for completed items
                        'comment': 'Completed from watchlist'
                    })
            
            if not watched_content:
                return self._get_empty_watched_content_response()
            
            self._ensure_embedding_service()
            content_embeddings, weighted_embeddings = self._extract_content_embeddings(watched_content, content_type)
            
            if not content_embeddings:
                return self._get_no_embeddings_response()
            
            avg_emotion_embedding = self._calculate_weighted_average_embedding(weighted_embeddings, content_embeddings)
            emotional_profile = self._calculate_emotional_profile_from_watched_content(watched_content)
            
            return {
                "emotion_embedding": avg_emotion_embedding.tolist(),
                "emotional_profile": emotional_profile,
                "confidence": min(1.0, len(content_embeddings) / 20.0),
                "watched_content_count": len(watched_content),
                "content_type": content_type
            }
            
        except Exception as e:
            logger.error(f"Error getting user emotion from watched content: {str(e)}")
            return self._get_error_response(str(e))
    
    def _calculate_emotional_profile_from_watched_content(self, watched_content: List[Dict]) -> Dict[str, Any]:
        """Calculate emotional profile from user's watched content"""
        if not watched_content:
            return {}
        
        # Calculate average rating
        ratings = [content.get('rating', 5.0) for content in watched_content]
        avg_rating = np.mean(ratings) if ratings else 5.0
        
        # Calculate content diversity (different genres, years, etc.)
        genres = set()
        years = set()
        
        for content in watched_content:
            if content.get('genres'):
                genres.update(content['genres'])
            if content.get('release_year'):
                years.add(content['release_year'])
        
        diversity_score = min(1.0, (len(genres) + len(years)) / 20.0)
        
        # Calculate emotional characteristics
        characteristics = {
            "average_rating": avg_rating,
            "content_diversity": diversity_score,
            "preference_intensity": self._calculate_preference_intensity(ratings),
            "content_count": len(watched_content)
        }
        
        return characteristics
    
    def _ensure_embedding_service(self) -> None:
        if not self.embedding_service:
            from app.services.embedding_service import EmbeddingService
            self.embedding_service = EmbeddingService()
    
    def _extract_content_embeddings(self, watched_content: List[Dict], content_type: str) -> tuple:
        content_embeddings = []
        weighted_embeddings = []
        
        for content in watched_content:
            tmdb_id = content.get('tmdb_id')
            rating = content.get('rating', 5.0)
            content_embedding = self.embedding_service.get_content_embedding(tmdb_id, content_type)
            
            if content_embedding is not None:
                content_embeddings.append(content_embedding)
                weighted_embeddings.append(content_embedding * (rating / 10.0))
        
        return content_embeddings, weighted_embeddings
    
    def _calculate_weighted_average_embedding(self, weighted_embeddings: List, content_embeddings: List) -> np.ndarray:
        if weighted_embeddings:
            return np.mean(weighted_embeddings, axis=0)
        return np.mean(content_embeddings, axis=0)
    
    def _get_default_emotion_analysis(self) -> Dict[str, Any]:
            return {
            "emotion_embedding": [],
            "similar_content_count": 0,
            "emotional_profile": {},
                "confidence": 0.0
            }
    
    def _get_empty_watched_content_response(self) -> Dict[str, Any]:
        return {
            "emotion_embedding": [],
            "emotional_profile": {},
            "confidence": 0.0,
            "message": "No watched content found"
        }
    
    def _get_no_embeddings_response(self) -> Dict[str, Any]:
        return {
            "emotion_embedding": [],
            "emotional_profile": {},
            "confidence": 0.0,
            "message": "No content embeddings found"
        }
    
    def _get_error_response(self, error: str) -> Dict[str, Any]:
        return {
            "emotion_embedding": [],
            "emotional_profile": {},
            "confidence": 0.0,
            "error": error
        }
    
    def _get_empty_profile_response(self) -> Dict[str, Any]:
        return {
            "emotion_embedding": [],
            "emotional_profile": {},
            "confidence": 0.0,
            "message": "No profile found"
        }
    
    def _build_profile_response(self, profile: UserEmotionalProfile, content_type: str) -> Dict[str, Any]:
        emotion_embedding = profile.emotional_embedding if profile.emotional_embedding is not None else []
        
        return {
            "emotion_embedding": emotion_embedding,
            "emotional_profile": {
                "preferred_genres": profile.preferred_genres,
                "emotional_tendencies": profile.emotional_tendencies,
                "total_watched_movies": profile.total_watched_movies,
                "profile_confidence": profile.profile_confidence
            },
            "confidence": profile.profile_confidence,
            "content_type": content_type
        }
    
    def _has_existing_feedback(self, recommendation: UserRecommendation) -> bool:
        existing_feedback = self.db.query(RecommendationSelection).filter(
            and_(
                RecommendationSelection.user_id == recommendation.user_id,
                RecommendationSelection.tmdb_id == recommendation.tmdb_id,
                RecommendationSelection.content_type == recommendation.content_type
            )
        ).first()
        return existing_feedback is not None
    
    def _calculate_content_intensity(self, content_list: List[Dict]) -> float:
        if not content_list:
            return 0.5
        
        intensity_scores = []
        for content in content_list:
            score = 0.5
            genres = content.get('genres', [])
            
            if any(genre in ['Action', 'Thriller', 'Horror'] for genre in genres):
                score += 0.3
            elif any(genre in ['Comedy', 'Romance'] for genre in genres):
                score += 0.1
            elif any(genre in ['Drama', 'War'] for genre in genres):
                score += 0.2
            
            intensity_scores.append(score)
        
        return np.mean(intensity_scores) if intensity_scores else 0.5
    
    def _calculate_content_complexity(self, content_list: List[Dict]) -> float:
        if not content_list:
            return 0.5
        
        complexity_scores = []
        for content in content_list:
            score = 0.5
            genres = content.get('genres', [])
            
            if any(genre in ['Documentary', 'Drama', 'War'] for genre in genres):
                score += 0.3
            elif any(genre in ['Comedy', 'Animation'] for genre in genres):
                score -= 0.2
            
            complexity_scores.append(score)
        
        return np.mean(complexity_scores) if complexity_scores else 0.5
    
    def _calculate_mood_improving_score(self, content_list: List[Dict]) -> float:
        if not content_list:
            return 0.5
        
        mood_scores = []
        for content in content_list:
            score = 0.5
            genres = content.get('genres', [])
            
            if any(genre in ['Comedy', 'Romance', 'Animation'] for genre in genres):
                score += 0.3
            elif any(genre in ['Horror', 'War'] for genre in genres):
                score -= 0.2
            
            mood_scores.append(score)
        
        return np.mean(mood_scores) if mood_scores else 0.5
    
    def _calculate_thought_provoking_score(self, content_list: List[Dict]) -> float:
        if not content_list:
            return 0.5
        
        thought_scores = []
        for content in content_list:
            score = 0.5
            genres = content.get('genres', [])
            
            if any(genre in ['Documentary', 'Drama', 'War'] for genre in genres):
                score += 0.3
            elif any(genre in ['Comedy', 'Animation'] for genre in genres):
                score -= 0.2
            
            thought_scores.append(score)
        
        return np.mean(thought_scores) if thought_scores else 0.5
    
    def _calculate_preference_intensity(self, ratings: List[float]) -> float:
        if not ratings:
            return 0.5
        
        std_dev = np.std(ratings)
        return max(0.0, 1.0 - (std_dev / 5.0))
    
    def analyze_content_emotional_tone(self, tmdb_id: int, content_type: str) -> Dict[str, Any]:
        try:
            self._ensure_embedding_service()
            content_embedding = self.embedding_service.get_content_embedding(tmdb_id, content_type)
            
            if content_embedding is None:
                return self._get_default_emotional_tone()
            
            content_data = self._get_content_data(tmdb_id, content_type)
            if not content_data:
                return self._get_default_emotional_tone()
            
            similar_content = self.embedding_service.search_similar_content(
                query_embedding=content_embedding,
                top_k=5,
                content_type=content_type
            )
            
            emotional_characteristics = self._calculate_content_emotional_characteristics(
                content_data, similar_content
            )
            
            return {
                "content_embedding": content_embedding.tolist(),
                "similar_content_count": len(similar_content),
                "emotional_characteristics": emotional_characteristics,
                "confidence_score": min(1.0, len(similar_content) / 5.0)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing content emotional tone: {str(e)}")
            return self._get_default_emotional_tone()
    
    def _calculate_content_emotional_characteristics(self, content_data: Dict, similar_content: List[Dict]) -> Dict[str, Any]:
        characteristics = {}
        genres = content_data.get('genres', [])
        genre_names = [genre.get('name', '') for genre in genres]
        
        characteristics["intensity"] = self._calculate_content_intensity([{"genres": genre_names}])
        characteristics["complexity"] = self._calculate_content_complexity([{"genres": genre_names}])
        characteristics["mood_improving"] = self._calculate_mood_improving_score([{"genres": genre_names}])
        characteristics["thought_provoking"] = self._calculate_thought_provoking_score([{"genres": genre_names}])
        
        if similar_content:
            characteristics["embedding_similarity"] = np.mean([item.get('similarity', 0) for item in similar_content])
            characteristics["content_cluster_size"] = len(similar_content)
        else:
            characteristics["embedding_similarity"] = 0.0
            characteristics["content_cluster_size"] = 0
        
        return characteristics
    
    def _get_content_data(self, tmdb_id: int, content_type: str) -> Dict:
        try:
            if content_type == "movie":
                content_data = self.tmdb_service.movie_service.get_movie_details(tmdb_id)
            else:
                content_data = self.tmdb_service.tv_service.get_tv_show_details(tmdb_id)
            
            # Convert TMDBResponse to dict
            if hasattr(content_data, 'data'):
                return content_data.data
            else:
                return content_data.__dict__ if hasattr(content_data, '__dict__') else dict(content_data)
        except Exception as e:
            logger.error(f"Error getting content data: {str(e)}")
            return {}
    
    def _get_default_emotional_tone(self) -> Dict[str, Any]:
        return {
            "content_embedding": [],
            "similar_content_count": 0,
            "emotional_characteristics": {
                "intensity": 0.5,
                "complexity": 0.5,
                "mood_improving": 0.5,
                "thought_provoking": 0.5,
                "embedding_similarity": 0.0,
                "content_cluster_size": 0
            },
            "confidence_score": 0.0
        }
    
    def update_user_emotion_profile(self, user_id: int, new_feedback: Dict[str, Any]) -> None:
        """Update user's emotional profile based on new feedback"""
        try:
            # Get or create user emotion profile
            profile = self.db.query(UserEmotionalProfile).filter(
                UserEmotionalProfile.user_id == user_id
            ).first()
            
            if not profile:
                profile = UserEmotionalProfile(
                    user_id=user_id,
                    preferred_emotions={},
                    emotional_tone_preferences={},
                    emotion_content_mapping={}
                )
                self.db.add(profile)
            
            # Update preferences based on feedback
            self._update_emotional_preferences(profile, new_feedback)
            
            # Update success rate
            profile.total_recommendations += 1
            if new_feedback.get("liked", False):
                profile.successful_recommendations += 1
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error updating user emotion profile: {str(e)}")
            self.db.rollback()
    
    def _update_emotional_preferences(self, profile: UserEmotionalProfile, feedback: Dict[str, Any]) -> None:
        """Update emotional preferences based on user feedback using embedding approach"""
        learning_rate = profile.learning_rate
        
        # Update embedding-based preferences
        if "content_embedding" in feedback:
            content_embedding = feedback["content_embedding"]
            
            # Get current average embedding
            current_embedding = profile.emotion_content_mapping.get("average_embedding", [])
            
            if current_embedding and content_embedding:
                # Update average embedding based on feedback
                if feedback.get("liked", False):
                    # Positive feedback: move towards this embedding
                    new_embedding = np.array(current_embedding) * (1 - learning_rate) + np.array(content_embedding) * learning_rate
                else:
                    # Negative feedback: move away from this embedding
                    new_embedding = np.array(current_embedding) * (1 + learning_rate) - np.array(content_embedding) * learning_rate
                
                profile.emotion_content_mapping["average_embedding"] = new_embedding.tolist()
        
        # Update emotional characteristics preferences
        if "emotional_characteristics" in feedback:
            characteristics = feedback["emotional_characteristics"]
            
            for char_name, char_value in characteristics.items():
                current_pref = profile.emotional_tone_preferences.get(char_name, 0.5)
                
            if feedback.get("liked", False):
                new_pref = current_pref + learning_rate * (char_value - current_pref)
            else:
                new_pref = current_pref - learning_rate * (char_value - current_pref)
            
            profile.emotional_tone_preferences[char_name] = max(0.0, min(1.0, new_pref))
    
    def update_user_emotion_profile_realtime(self, user_id: int, tmdb_id: int, rating: float, content_type: str = "movie") -> bool:
        try:
            profile = self._get_or_create_user_profile(user_id)
            content_embedding = self._get_content_embedding(tmdb_id, content_type)
            
            if content_embedding is None:
                return False
            
            self._update_profile_embedding(profile, content_embedding, rating)
            self._update_emotional_characteristics_realtime(profile, tmdb_id, content_type, rating)
            
            # Update success metrics
            # Update success metrics (already incremented total_watched_movies in _update_profile_embedding)
            profile.profile_confidence = min(1.0, profile.total_watched_movies / 20.0)
            
            # Update learning rate (simplified)
            if profile.total_watched_movies < 10:
                profile.profile_confidence = profile.total_watched_movies / 10.0
            
            self.db.commit()
            logger.info(f"Updated emotion profile for user {user_id} with {tmdb_id} (rating: {rating})")
            return True
            
        except Exception as e:
            logger.error(f"Error updating user emotion profile in real-time: {str(e)}")
            self.db.rollback()
            return False
    
    def _get_or_create_user_profile(self, user_id: int) -> UserEmotionalProfile:
        profile = self.db.query(UserEmotionalProfile).filter(
            UserEmotionalProfile.user_id == user_id
        ).first()
        
        if not profile:
            profile = UserEmotionalProfile(
                user_id=user_id,
                emotional_embedding=None,
                total_watched_movies=0,
                preferred_genres={},
                emotional_tendencies={},
                profile_confidence=0.0
            )
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
        
        return profile
    
    def _get_content_embedding(self, tmdb_id: int, content_type: str) -> np.ndarray:
        self._ensure_embedding_service()
        return self.embedding_service.get_content_embedding(tmdb_id, content_type)
    
    def _update_profile_embedding(self, profile: UserEmotionalProfile, content_embedding: np.ndarray, rating: float) -> None:
        current_embedding = profile.emotional_embedding
        current_content_count = profile.total_watched_movies
        
        if current_embedding is not None and current_content_count > 0:
            # Convert current embedding to numpy array
            current_embedding_array = np.array(current_embedding)
            weighted_new_embedding = content_embedding * (rating / 10.0)
            new_average = (current_embedding_array * current_content_count + weighted_new_embedding) / (current_content_count + 1)
            profile.emotional_embedding = [float(x) for x in new_average.tolist()]
        else:
            profile.emotional_embedding = [float(x) for x in content_embedding.tolist()]
        
        profile.total_watched_movies += 1
        profile.last_updated = datetime.utcnow()
    

    
    def _update_emotional_characteristics_realtime(self, profile: UserEmotionalProfile, tmdb_id: int, content_type: str, rating: float) -> None:
        try:
            content_data = self._get_content_data(tmdb_id, content_type)
            if not content_data:
                return
            
            genres = content_data.get('genres', [])
            genre_names = [genre.get('name', '') for genre in genres]
            
            # Update preferred genres
            for genre in genre_names:
                if genre in profile.preferred_genres:
                    profile.preferred_genres[genre] += rating / 10.0
                else:
                    profile.preferred_genres[genre] = rating / 10.0
            
            # Update emotional tendencies based on content characteristics
            intensity = self._calculate_content_intensity([{"genres": genre_names}])
            mood_improving = self._calculate_mood_improving_score([{"genres": genre_names}])
            
            if mood_improving > 0.6:
                profile.emotional_tendencies["uplifting"] = profile.emotional_tendencies.get("uplifting", 0.5) + (rating / 10.0) * 0.1
            if intensity > 0.7:
                profile.emotional_tendencies["intense"] = profile.emotional_tendencies.get("intense", 0.5) + (rating / 10.0) * 0.1
            
            # Update profile confidence
            profile.profile_confidence = min(1.0, profile.total_watched_movies / 20.0)
            
        except Exception as e:
            logger.error(f"Error updating emotional characteristics: {str(e)}")
    

    
    def get_cached_user_emotion_profile(self, user_id: int, content_type: str = "movie") -> Dict[str, Any]:
        try:
            profile = self.db.query(UserEmotionalProfile).filter(
                UserEmotionalProfile.user_id == user_id
            ).first()
            
            if not profile:
                return self._get_empty_profile_response()
            
            return self._build_profile_response(profile, content_type)
            
        except Exception as e:
            logger.error(f"Error getting cached user emotion profile: {str(e)}")
            return self._get_error_response(str(e))
    
    def get_pending_feedback_notifications(self) -> List[Dict[str, Any]]:
        try:
            yesterday = datetime.utcnow() - timedelta(days=1)
            two_days_ago = datetime.utcnow() - timedelta(days=2)
            
            pending_recommendations = self.db.query(UserRecommendation).filter(
                and_(
                    UserRecommendation.created_at >= two_days_ago,
                    UserRecommendation.created_at <= yesterday,
                    UserRecommendation.viewed == True
                )
            ).all()
            
            notifications = []
            for rec in pending_recommendations:
                if not self._has_existing_feedback(rec):
                    notifications.append({
                        "user_id": rec.user_id,
                        "tmdb_id": rec.tmdb_id,
                        "content_type": rec.content_type,
                        "recommendation_type": rec.recommendation_type,
                        "emotion_state": rec.emotion_state,
                        "recommended_at": rec.created_at
                    })
            
            return notifications
            
        except Exception as e:
            logger.error(f"Error getting pending feedback notifications: {str(e)}")
            return []
    
    def save_post_viewing_feedback(self, user_id: int, feedback_data: Dict[str, Any]) -> bool:
        """Save user's post-viewing feedback"""
        try:
            feedback = RecommendationSelection(
                user_id=user_id,
                tmdb_id=feedback_data["tmdb_id"],
                content_type=feedback_data["content_type"],
                pre_viewing_emotion=feedback_data.get("pre_viewing_emotion"),
                pre_viewing_emotion_text=feedback_data.get("pre_viewing_emotion_text"),
                post_viewing_emotion=feedback_data.get("post_viewing_emotion"),
                post_viewing_emotion_text=feedback_data.get("post_viewing_emotion_text"),
                emotional_impact_score=feedback_data.get("emotional_impact_score"),
                recommendation_accuracy=feedback_data.get("recommendation_accuracy"),
                mood_improvement=feedback_data.get("mood_improvement"),
                emotional_catharsis=feedback_data.get("emotional_catharsis"),
                would_recommend_to_others=feedback_data.get("would_recommend_to_others"),
                additional_comments=feedback_data.get("additional_comments"),
                feedback_provided=True,
                feedback_at=datetime.utcnow()
            )
            
            self.db.add(feedback)
            self.db.commit()
            
            # Update user's emotion profile with embedding-based approach
            self.update_user_emotion_profile(user_id, {
                "content_embedding": feedback_data.get("content_embedding", []),
                "emotional_characteristics": feedback_data.get("emotional_characteristics", {}),
                "liked": feedback_data.get("recommendation_accuracy", 5) >= 7
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving post-viewing feedback: {str(e)}")
            self.db.rollback()
            return False
    
    def get_user_emotion_insights(self, user_id: int) -> Dict[str, Any]:
        """Get insights about user's emotional preferences and patterns"""
        try:
            profile = self.db.query(UserEmotionalProfile).filter(
                UserEmotionalProfile.user_id == user_id
            ).first()
            
            if not profile:
                return {"message": "No emotion profile found"}
            
            # Get recent feedback
            recent_feedback = self.db.query(RecommendationSelection).filter(
                RecommendationSelection.user_id == user_id
            ).order_by(RecommendationSelection.created_at.desc()).limit(10).all()
            
            # Most preferred genres
            top_genres = sorted(
                profile.preferred_genres.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]
            
            # Most common emotional tendencies
            top_tendencies = sorted(
                profile.emotional_tendencies.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:3]
            
            # Get average embedding if available
            average_embedding = profile.emotional_embedding.tolist() if profile.emotional_embedding is not None else []
            
            return {
                "profile_confidence": profile.profile_confidence,
                "total_watched_movies": profile.total_watched_movies,
                "top_genres": top_genres,
                "top_emotional_tendencies": top_tendencies,
                "average_embedding": average_embedding,
                "recent_feedback_count": len(recent_feedback),
                "last_updated": profile.last_updated.isoformat() if profile.last_updated else None
            }
            
        except Exception as e:
            logger.error(f"Error getting user emotion insights: {str(e)}")
            return {"error": str(e)} 