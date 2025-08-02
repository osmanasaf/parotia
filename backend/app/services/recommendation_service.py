import logging
import numpy as np
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.core.tmdb_service import TMDBServiceFactory
from app.repositories.user_interaction_repository import (
    UserRatingRepository, UserRecommendationRepository
)
from app.schemas.movie import (
    EmotionBasedRecommendation, HistoryBasedRecommendation, HybridRecommendation
)
from app.core.exceptions import UserNotFoundException
from app.core.config import get_settings
from app.services.embedding_service import EmbeddingService
from app.services.emotion_analysis_service import EmotionAnalysisService

logger = logging.getLogger(__name__)

class RecommendationService:
    """Service for AI-based recommendation operations"""
    
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        
        # Initialize repositories
        self.rating_repo = UserRatingRepository(db)
        self.recommendation_repo = UserRecommendationRepository(db)
        
        # Initialize TMDB services
        self.tmdb_movie_service = TMDBServiceFactory.create_movie_service(
            api_key=self.settings.TMDB_API_KEY
        )
        self.tmdb_tv_service = TMDBServiceFactory.create_tv_service(
            api_key=self.settings.TMDB_API_KEY
        )
        
        # Initialize services
        self.embedding_service = EmbeddingService()
        self.emotion_service = EmotionAnalysisService(db)

    # ============================================================================
    # KULLANICI ÖNERİ METODLARI
    # ============================================================================

    def get_emotion_based_recommendations(self, user_id: int, emotion_data: EmotionBasedRecommendation) -> Dict[str, Any]:
        """
        Kullanıcının anlık duygu durumuna göre öneriler
        - %100 anlık duygu odaklı
        - Geçmiş verileri kullanmaz
        """
        try:
            # Handle "all" content type
            if emotion_data.content_type == "all":
                return self._get_emotion_based_recommendations_all(user_id, emotion_data)
            
            # Get emotion embedding from emotion analysis service
            emotion_analysis = self.emotion_service.analyze_user_emotion(emotion_data.emotion)
            emotion_embedding = emotion_analysis.get("emotion_embedding", [])
            
            if not emotion_embedding:
                logger.warning("No emotion embedding generated, falling back to text-based search")
                # Fallback to text-based search
                recommendations = self.embedding_service.search_similar_content(
                    query_text=emotion_data.emotion,
                    top_k=50,  # Daha fazla sonuç al
                    content_type=emotion_data.content_type
                )
            else:
                # Use emotion embedding for search
                emotion_embedding_array = np.array(emotion_embedding)
                recommendations = self.embedding_service.search_similar_content(
                    query_text="",
                    top_k=50,  # Daha fazla sonuç al
                    content_type=emotion_data.content_type,
                    query_embedding=emotion_embedding_array
                )
            
            # Filter out watched content and clean recommendations
            user_ratings = self.rating_repo.get_user_ratings(user_id, emotion_data.content_type)
            watched_tmdb_ids = {rating.tmdb_id for rating in user_ratings}
            
            seen_tmdb_ids = set()
            clean_recommendations = []
            
            for rec in recommendations:
                tmdb_id = rec.get("tmdb_id")
                
                # Skip if already seen or watched
                if tmdb_id in seen_tmdb_ids or tmdb_id in watched_tmdb_ids:
                    continue
                
                seen_tmdb_ids.add(tmdb_id)
                
                # Get detailed content info from TMDB
                try:
                    if emotion_data.content_type == "movie":
                        content_response = self.tmdb_movie_service.get_movie_details(tmdb_id)
                    else:
                        content_response = self.tmdb_tv_service.get_tv_show_details(tmdb_id)
                    
                    if content_response.success:
                        content_data = content_response.data
                        
                        # Filter out low-rated content (IMDB 6.0 altı)
                        vote_average = content_data.get("vote_average", 0)
                        if vote_average < 6.0:
                            continue
                        
                        # Clean recommendation data
                        clean_rec = {
                            "tmdb_id": tmdb_id,
                            "content_type": emotion_data.content_type,
                            "title": content_data.get("title", rec.get("title", "")),
                            "overview": content_data.get("overview", rec.get("overview", "")),
                            "backdrop_path": content_data.get("backdrop_path"),
                            "poster_path": content_data.get("poster_path"),
                            "release_date": content_data.get("release_date"),
                            "vote_average": vote_average,
                            "similarity_score": float(rec.get("similarity_score", 0.0)),
                            "rank": len(clean_recommendations) + 1
                        }
                        clean_recommendations.append(clean_rec)
                        
                        # Save to history
                        self.recommendation_repo.save_recommendation(
                            user_id=user_id,
                            tmdb_id=tmdb_id,
                            content_type=emotion_data.content_type,
                            recommendation_type="current_emotion",
                            emotion_state=emotion_data.emotion,
                            score=rec["similarity_score"]
                        )
                        
                        # Stop when we have 10 recommendations
                        if len(clean_recommendations) >= 10:
                            break
                            
                except Exception as e:
                    logger.warning(f"Error getting details for {emotion_data.content_type} {tmdb_id}: {str(e)}")
                    continue
            
            return {
                "success": True,
                "data": {
                    "recommendations": clean_recommendations,
                    "emotion": emotion_data.emotion,
                    "content_type": emotion_data.content_type,
                    "total": len(clean_recommendations),
                    "method": "current_emotion"
                }
            }
        except Exception as e:
            logger.error(f"Error getting emotion-based recommendations: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_hybrid_recommendations(self, user_id: int, emotion_text: str, content_type: str = "movie") -> Dict[str, Any]:
        """
        Hibrit öneriler: %70-80 duygu durumu + %20-30 izleme geçmişi
        - Kullanıcının anlık duygu durumu ve geçmişini birleştirir
        - En dengeli öneri sistemi
        """
        try:
            # Handle "all" content type
            if content_type == "all":
                return self._get_hybrid_recommendations_all(user_id, emotion_text)
            
            # Get user's cached emotion profile (fast access)
            user_emotion = self.emotion_service.get_cached_user_emotion_profile(user_id, content_type)
            user_emotion_embedding = user_emotion.get("emotion_embedding", [])
            
            # Get current emotion embedding
            emotion_analysis = self.emotion_service.analyze_user_emotion(emotion_text)
            emotion_embedding = emotion_analysis.get("emotion_embedding", [])
            
            # If user has no cached profile, fall back to emotion-based recommendations
            if not user_emotion_embedding:
                logger.info(f"User {user_id} has no cached profile, using emotion-based recommendations")
                return self.get_emotion_based_recommendations(
                    user_id=user_id,
                    emotion_data=EmotionBasedRecommendation(
                        emotion=emotion_text,
                        content_type=content_type,
                        page=1
                    )
                )
            
            # Get user's ratings for additional context
            user_ratings = self.rating_repo.get_user_ratings(user_id, content_type)
            
            # Combine emotion embeddings for hybrid search
            if emotion_embedding and user_emotion_embedding:
                # Weighted combination: 70% current emotion, 30% user's historical emotion
                emotion_weight = 0.7
                user_weight = 0.3
                
                current_emotion_array = np.array(emotion_embedding)
                user_emotion_array = np.array(user_emotion_embedding)
                
                # Combine embeddings
                hybrid_embedding = (current_emotion_array * emotion_weight + 
                                  user_emotion_array * user_weight)
                
                # Search using hybrid embedding
                recommendations = self.embedding_service.search_similar_content(
                    query_text="",
                    top_k=50,  # Daha fazla sonuç al
                    content_type=content_type,
                    query_embedding=hybrid_embedding
                )
            else:
                # Fallback to emotion-based search
                if emotion_embedding:
                    emotion_array = np.array(emotion_embedding)
                    recommendations = self.embedding_service.search_similar_content(
                        query_text="",
                        top_k=50,  # Daha fazla sonuç al
                        content_type=content_type,
                        query_embedding=emotion_array
                    )
                else:
                    # Final fallback to text-based search
                    recommendations = self.embedding_service.search_similar_content(
                        query_text=emotion_text,
                        top_k=50,  # Daha fazla sonuç al
                        content_type=content_type
                    )
            
            # Filter out watched content and clean recommendations
            user_ratings = self.rating_repo.get_user_ratings(user_id, content_type)
            watched_tmdb_ids = {rating.tmdb_id for rating in user_ratings}
            
            logger.info(f"Hybrid recommendations: Found {len(recommendations)} initial recommendations")
            logger.info(f"User has {len(watched_tmdb_ids)} watched movies")
            
            seen_tmdb_ids = set()
            clean_recommendations = []
            
            for rec in recommendations:
                tmdb_id = rec.get("tmdb_id")
                
                # Skip if already seen or watched
                if tmdb_id in seen_tmdb_ids or tmdb_id in watched_tmdb_ids:
                    logger.info(f"Hybrid: Skipping duplicate/watched movie {tmdb_id}")
                    continue
                
                seen_tmdb_ids.add(tmdb_id)
                
                # Get detailed content info from TMDB
                try:
                    if content_type == "movie":
                        content_response = self.tmdb_movie_service.get_movie_details(tmdb_id)
                    else:
                        content_response = self.tmdb_tv_service.get_tv_show_details(tmdb_id)
                    
                    if content_response.success:
                        content_data = content_response.data
                        
                        # Filter out low-rated content (IMDB 6.0 altı)
                        vote_average = content_data.get("vote_average", 0)
                        if vote_average < 6.0:
                            continue
                        
                        # Clean recommendation data
                        clean_rec = {
                            "tmdb_id": tmdb_id,
                            "content_type": content_type,
                            "title": content_data.get("title", rec.get("title", "")),
                            "overview": content_data.get("overview", rec.get("overview", "")),
                            "backdrop_path": content_data.get("backdrop_path"),
                            "poster_path": content_data.get("poster_path"),
                            "release_date": content_data.get("release_date"),
                            "vote_average": vote_average,
                            "similarity_score": float(rec.get("similarity_score", 0.0)),
                            "rank": len(clean_recommendations) + 1
                        }
                        clean_recommendations.append(clean_rec)
                        
                        # Save to history
                        self.recommendation_repo.save_recommendation(
                            user_id=user_id,
                            tmdb_id=tmdb_id,
                            content_type=content_type,
                            recommendation_type="hybrid",
                            emotion_state=emotion_text,
                            score=rec["similarity_score"]
                        )
                        
                        # Stop when we have 10 recommendations
                        if len(clean_recommendations) >= 10:
                            break
                            
                except Exception as e:
                    logger.warning(f"Error getting details for {content_type} {tmdb_id}: {str(e)}")
                    continue
            
            return {
                "success": True,
                "data": {
                    "recommendations": clean_recommendations,
                    "emotion": emotion_text,
                    "content_type": content_type,
                    "total": len(clean_recommendations),
                    "user_emotion_confidence": user_emotion.get("confidence", 0.0),
                    "current_emotion_confidence": emotion_analysis.get("confidence", 0.0),
                    "recommendation_type": "hybrid",
                    "weights": {
                        "current_emotion": 0.7,
                        "user_profile": 0.3
                    }
                }
            }
        except Exception as e:
            logger.error(f"Error getting hybrid recommendations: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_history_based_recommendations(self, user_id: int, history_data: HistoryBasedRecommendation) -> Dict[str, Any]:
        """
        Kullanıcının izleme geçmişine göre öneriler
        - Kullanıcının rate ettiği filmlerin benzerlerini önerir
        - %100 geçmiş odaklı
        """
        try:
            # Get user's ratings
            user_ratings = self.rating_repo.get_user_ratings(user_id, history_data.content_type)
            
            if not user_ratings:
                return {
                    "success": True,
                    "data": {
                        "recommendations": [],
                        "message": "No viewing history found",
                        "total": 0,
                        "method": "history_based"
                    }
                }
            
            # Convert to format expected by embedding service
            ratings_data = []
            for rating in user_ratings:
                try:
                    # Get content details from TMDB
                    if rating.content_type == "movie":
                        content_response = self.tmdb_movie_service.get_movie_details(rating.tmdb_id)
                    else:
                        content_response = self.tmdb_tv_service.get_tv_show_details(rating.tmdb_id)
                    
                    if content_response.success:
                        content_data = content_response.data
                        content_data["content_type"] = rating.content_type
                        ratings_data.append({
                            "content": content_data,
                            "rating": rating.rating
                        })
                except Exception as e:
                    logger.warning(f"Error getting content details for {rating.tmdb_id}: {str(e)}")
                    continue
            
            # Get user preference embedding
            user_embedding = self.embedding_service.get_user_preference_embedding(ratings_data)
            
            if user_embedding is None:
                return {
                    "success": True,
                    "data": {
                        "recommendations": [],
                        "message": "Could not generate user preference embedding",
                        "total": 0,
                        "method": "history_based"
                    }
                }
            
            # Search for similar content using user embedding
            recommendations = self.embedding_service.search_similar_content(
                query_text="",  # Not used when user_embedding is provided
                top_k=20,
                content_type=history_data.content_type,
                user_embedding=user_embedding
            )
            
            # Filter out watched content and clean recommendations
            watched_tmdb_ids = {rating.tmdb_id for rating in user_ratings}
            
            seen_tmdb_ids = set()
            clean_recommendations = []
            
            for rec in recommendations:
                tmdb_id = rec.get("tmdb_id")
                
                # Skip if already seen or watched
                if tmdb_id in seen_tmdb_ids or tmdb_id in watched_tmdb_ids:
                    continue
                
                seen_tmdb_ids.add(tmdb_id)
                
                # Get detailed content info from TMDB
                try:
                    if history_data.content_type == "movie":
                        content_response = self.tmdb_movie_service.get_movie_details(tmdb_id)
                    else:
                        content_response = self.tmdb_tv_service.get_tv_show_details(tmdb_id)
                    
                    if content_response.success:
                        content_data = content_response.data
                        
                        # Filter out low-rated content (IMDB 6.0 altı)
                        vote_average = content_data.get("vote_average", 0)
                        if vote_average < 6.0:
                            continue
                        
                        # Clean recommendation data
                        clean_rec = {
                            "tmdb_id": tmdb_id,
                            "content_type": history_data.content_type,
                            "title": content_data.get("title", rec.get("title", "")),
                            "overview": content_data.get("overview", rec.get("overview", "")),
                            "backdrop_path": content_data.get("backdrop_path"),
                            "poster_path": content_data.get("poster_path"),
                            "release_date": content_data.get("release_date"),
                            "vote_average": vote_average,
                            "similarity_score": float(rec.get("similarity_score", 0.0)),
                            "rank": len(clean_recommendations) + 1
                        }
                        clean_recommendations.append(clean_rec)
                        
                        # Save to history
                        self.recommendation_repo.save_recommendation(
                            user_id=user_id,
                            tmdb_id=tmdb_id,
                            content_type=history_data.content_type,
                            recommendation_type="history_based",
                            emotion_state=None,
                            score=rec["similarity_score"]
                        )
                        
                        # Stop when we have 10 recommendations
                        if len(clean_recommendations) >= 10:
                            break
                            
                except Exception as e:
                    logger.warning(f"Error getting details for {history_data.content_type} {tmdb_id}: {str(e)}")
                    continue
            
            return {
                "success": True,
                "data": {
                    "recommendations": clean_recommendations,
                    "content_type": history_data.content_type,
                    "total": len(clean_recommendations),
                    "user_ratings_count": len(ratings_data),
                    "method": "history_based"
                }
            }
        except Exception as e:
            logger.error(f"Error getting history-based recommendations: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_profile_based_recommendations(self, user_id: int, content_type: str = "movie") -> Dict[str, Any]:
        """
        Kullanıcının emotion profile'ına göre öneriler
        - Emotion text gerektirmez
        - Kullanıcının geçmiş duygu analizlerini kullanır
        - %100 profile odaklı
        """
        try:
            # Step 1: Get user's emotional profile
            user_profile = self.embedding_service.get_user_emotional_profile(user_id, self.db)
            
            if not user_profile or user_profile["emotional_embedding"] is None:
                logger.warning(f"No emotional profile found for user {user_id}")
                return {
                    "success": False, 
                    "error": "No emotional profile found. Please rate some movies first.",
                    "data": {
                        "recommendations": [],
                        "user_profile": None,
                        "content_type": content_type,
                        "total": 0,
                        "method": "profile_based",
                        "profile_confidence": 0.0
                    }
                }
            
            # Step 2: Get recommendations using user's emotional embedding
            user_embedding = user_profile["emotional_embedding"]
            recommendations = self.embedding_service.search_similar_content(
                query_text="",
                top_k=50,  # Get more to filter out watched content
                content_type=content_type,
                user_embedding=user_embedding
            )
            
            # Step 3: Get user's watched content to filter out
            user_ratings = self.rating_repo.get_user_ratings(user_id, content_type)
            watched_tmdb_ids = {rating.tmdb_id for rating in user_ratings}
            
            # Step 4: Filter and clean recommendations
            seen_tmdb_ids = set()
            clean_recommendations = []
            
            for rec in recommendations:
                tmdb_id = rec.get("tmdb_id")
                
                # Skip if already seen or watched
                if tmdb_id in seen_tmdb_ids or tmdb_id in watched_tmdb_ids:
                    continue
                
                seen_tmdb_ids.add(tmdb_id)
                
                # Get detailed content info from TMDB
                try:
                    if content_type == "movie":
                        content_response = self.tmdb_movie_service.get_movie_details(tmdb_id)
                    else:
                        content_response = self.tmdb_tv_service.get_tv_show_details(tmdb_id)
                    
                    if content_response.success:
                        content_data = content_response.data
                        
                        # Filter out low-rated content (IMDB 6.0 altı)
                        vote_average = content_data.get("vote_average", 0)
                        if vote_average < 6.0:
                            continue
                        
                        # Clean recommendation data
                        clean_rec = {
                            "tmdb_id": tmdb_id,
                            "content_type": content_type,
                            "title": content_data.get("title", rec.get("title", "")),
                            "overview": content_data.get("overview", rec.get("overview", "")),
                            "backdrop_path": content_data.get("backdrop_path"),
                            "poster_path": content_data.get("poster_path"),
                            "release_date": content_data.get("release_date"),
                            "vote_average": vote_average,
                            "similarity_score": float(rec.get("similarity_score", 0.0)),
                            "rank": len(clean_recommendations) + 1
                        }
                        clean_recommendations.append(clean_rec)
                        
                        # Save to history
                        self.recommendation_repo.save_recommendation(
                            user_id=user_id,
                            tmdb_id=tmdb_id,
                            content_type=content_type,
                            recommendation_type="profile_based",
                            emotion_state="user_profile",
                            score=rec["similarity_score"]
                        )
                        
                        # Stop when we have 10 recommendations
                        if len(clean_recommendations) >= 10:
                            break
                            
                except Exception as e:
                    logger.warning(f"Error getting details for {content_type} {tmdb_id}: {str(e)}")
                    continue
            
            return {
                "success": True,
                "data": {
                    "recommendations": clean_recommendations,
                    "content_type": content_type,
                    "total": len(clean_recommendations),
                    "method": "profile_based",
                    "profile_confidence": user_profile["profile_confidence"]
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting profile-based recommendations: {str(e)}")
            return {"success": False, "error": str(e)}

    # ============================================================================
    # YARDIMCI METODLAR
    # ============================================================================

    def _get_hybrid_recommendations_all(self, user_id: int, emotion_text: str) -> Dict[str, Any]:
        """Get hybrid recommendations for both movies and TV shows"""
        try:
            # Get recommendations for both content types
            movie_result = self.get_hybrid_recommendations(user_id, emotion_text, "movie")
            tv_result = self.get_hybrid_recommendations(user_id, emotion_text, "tv")
            
            # Combine results
            all_recommendations = []
            
            if movie_result["success"] and "data" in movie_result:
                all_recommendations.extend(movie_result["data"]["recommendations"])
            
            if tv_result["success"] and "data" in tv_result:
                all_recommendations.extend(tv_result["data"]["recommendations"])
            
            # Sort by similarity score and take top 10
            all_recommendations.sort(key=lambda x: x["similarity_score"], reverse=True)
            top_recommendations = all_recommendations[:10]
            
            # Calculate breakdown
            movie_count = len([r for r in top_recommendations if r["content_type"] == "movie"])
            tv_count = len([r for r in top_recommendations if r["content_type"] == "tv"])
            
            return {
                "success": True,
                "data": {
                    "recommendations": top_recommendations,
                    "emotion": emotion_text,
                    "content_type": "all",
                    "total": len(top_recommendations),
                    "breakdown": {
                        "movies": movie_count,
                        "tv_shows": tv_count
                    },
                    "recommendation_type": "hybrid_all"
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting hybrid recommendations for all content types: {str(e)}")
            return {"success": False, "error": str(e)}

    def _get_emotion_based_recommendations_all(self, user_id: int, emotion_data: EmotionBasedRecommendation) -> Dict[str, Any]:
        """Get emotion-based recommendations for both movies and TV shows"""
        try:
            # Get recommendations for both content types
            movie_result = self.get_emotion_based_recommendations(
                user_id, 
                EmotionBasedRecommendation(
                    emotion=emotion_data.emotion,
                    content_type="movie",
                    page=emotion_data.page
                )
            )
            
            tv_result = self.get_emotion_based_recommendations(
                user_id, 
                EmotionBasedRecommendation(
                    emotion=emotion_data.emotion,
                    content_type="tv",
                    page=emotion_data.page
                )
            )
            
            # Combine results
            all_recommendations = []
            
            if movie_result["success"] and "data" in movie_result:
                all_recommendations.extend(movie_result["data"]["recommendations"])
            
            if tv_result["success"] and "data" in tv_result:
                all_recommendations.extend(tv_result["data"]["recommendations"])
            
            # Sort by similarity score and take top 10
            all_recommendations.sort(key=lambda x: x["similarity_score"], reverse=True)
            top_recommendations = all_recommendations[:10]
            
            # Calculate breakdown
            movie_count = len([r for r in top_recommendations if r["content_type"] == "movie"])
            tv_count = len([r for r in top_recommendations if r["content_type"] == "tv"])
            
            return {
                "success": True,
                "data": {
                    "recommendations": top_recommendations,
                    "emotion": emotion_data.emotion,
                    "content_type": "all",
                    "total": len(top_recommendations),
                    "breakdown": {
                        "movies": movie_count,
                        "tv_shows": tv_count
                    },
                    "recommendation_type": "emotion_all"
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting emotion-based recommendations for all content types: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_user_recommendation_history(self, user_id: int, recommendation_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get user's recommendation history"""
        try:
            recommendations = self.recommendation_repo.get_user_recommendations(user_id, recommendation_type)
            
            # Convert to dict format
            history = []
            for rec in recommendations:
                history.append({
                    "id": rec.id,
                    "user_id": rec.user_id,
                    "tmdb_id": rec.tmdb_id,
                    "content_type": rec.content_type,
                    "recommendation_type": rec.recommendation_type,
                    "emotion_state": rec.emotion_state,
                    "score": rec.score,
                    "viewed": rec.viewed,
                    "created_at": rec.created_at
                })
            
            return history
        except Exception as e:
            logger.error(f"Error getting user recommendation history: {str(e)}")
            return []

    # ============================================================================
    # ADMIN METODLARI (Sistem Yönetimi)
    # ============================================================================

    def populate_embedding_index(self, content_type: str = "movie", pages: int = 5) -> Dict[str, Any]:
        """Populate embedding index with popular content"""
        try:
            added_count = 0
            
            for page in range(1, pages + 1):
                if content_type == "movie":
                    response = self.tmdb_movie_service.get_popular_movies(page)
                else:
                    response = self.tmdb_tv_service.get_popular_tv_shows(page)
                
                if response.success:
                    for content in response.data.get("results", []):
                        # Check vote_average before adding (IMDB 6.0 altı filtreleme)
                        vote_average = content.get('vote_average', 0)
                        if vote_average < 6.0:
                            logger.info(f"Skipping low-rated {content_type} {content.get('id')}: {content.get('title') or content.get('name')} (vote_average: {vote_average})")
                            continue
                        
                        content["content_type"] = content_type
                        if self.embedding_service.add_content(content):
                            added_count += 1
            
            # Save the index
            self.embedding_service.save_index()
            
            return {
                "success": True,
                "data": {
                    "added_count": added_count,
                    "content_type": content_type,
                    "pages": pages,
                    "index_stats": self.embedding_service.get_index_stats()
                }
            }
        except Exception as e:
            logger.error(f"Error populating embedding index: {str(e)}")
            return {"success": False, "error": str(e)}

    def populate_embedding_index_with_details(self, content_type: str = "movie", pages: int = 5) -> Dict[str, Any]:
        """Populate embedding index with detailed content information"""
        try:
            added_count = 0
            failed_count = 0
            
            for page in range(1, pages + 1):
                logger.info(f"Processing page {page} for {content_type}")
                
                # Get popular content
                if content_type == "movie":
                    response = self.tmdb_movie_service.get_popular_movies(page)
                else:
                    response = self.tmdb_tv_service.get_popular_tv_shows(page)
                
                if response.success:
                    for content in response.data.get("results", []):
                        try:
                            # Get detailed information for each content
                            content_id = content.get("id")
                            if content_type == "movie":
                                detail_response = self.tmdb_movie_service.get_movie_details(content_id)
                                # Get credits
                                credits_response = self.tmdb_movie_service.get_movie_credits(content_id)
                            else:
                                detail_response = self.tmdb_tv_service.get_tv_show_details(content_id)
                                # Get credits
                                credits_response = self.tmdb_tv_service.get_tv_show_credits(content_id)
                            
                            if detail_response.success:
                                # Merge basic content with detailed information
                                detailed_content = {**content, **detail_response.data}
                                
                                # Add credits if available
                                if credits_response.success:
                                    detailed_content["credits"] = credits_response.data
                                
                                detailed_content["content_type"] = content_type
                                
                                # Check vote_average before adding (IMDB 6.0 altı filtreleme)
                                vote_average = detailed_content.get('vote_average', 0)
                                if vote_average < 6.0:
                                    logger.info(f"Skipping low-rated {content_type} {content_id}: {detailed_content.get('title') or detailed_content.get('name')} (vote_average: {vote_average})")
                                    failed_count += 1
                                    continue
                                
                                if self.embedding_service.add_content_with_details(detailed_content, self.db):
                                    added_count += 1
                                    logger.info(f"Added {content_type} {content_id}: {detailed_content.get('title') or detailed_content.get('name')} (vote_average: {vote_average})")
                                else:
                                    failed_count += 1
                            else:
                                failed_count += 1
                                logger.warning(f"Failed to get details for {content_type} {content_id}")
                                
                        except Exception as e:
                            failed_count += 1
                            logger.error(f"Error processing {content_type} {content.get('id')}: {str(e)}")
                            continue
            
            # Save the index
            self.embedding_service.save_index()
            
            return {
                "success": True,
                "data": {
                    "added_count": added_count,
                    "failed_count": failed_count,
                    "content_type": content_type,
                    "pages": pages,
                    "index_stats": self.embedding_service.get_index_stats()
                }
            }
        except Exception as e:
            logger.error(f"Error populating embedding index with details: {str(e)}")
            return {"success": False, "error": str(e)}

    def populate_embedding_index_by_genre(self, content_type: str = "movie", genre_id: int = None, pages: int = 3) -> Dict[str, Any]:
        """Populate embedding index with content from specific genre"""
        try:
            added_count = 0
            
            for page in range(1, pages + 1):
                if content_type == "movie":
                    # Get movies by genre
                    params = {"page": page}
                    if genre_id:
                        params["with_genres"] = genre_id
                    response = self.tmdb_movie_service.get_popular_movies(page)
                else:
                    # Get TV shows by genre
                    params = {"page": page}
                    if genre_id:
                        params["with_genres"] = genre_id
                    response = self.tmdb_tv_service.get_popular_tv_shows(page)
                
                if response.success:
                    for content in response.data.get("results", []):
                        # Check vote_average before adding (IMDB 6.0 altı filtreleme)
                        vote_average = content.get('vote_average', 0)
                        if vote_average < 6.0:
                            logger.info(f"Skipping low-rated {content_type} {content.get('id')}: {content.get('title') or content.get('name')} (vote_average: {vote_average})")
                            continue
                        
                        content["content_type"] = content_type
                        if self.embedding_service.add_content(content):
                            added_count += 1
            
            # Save the index
            self.embedding_service.save_index()
            
            return {
                "success": True,
                "data": {
                    "added_count": added_count,
                    "content_type": content_type,
                    "genre_id": genre_id,
                    "pages": pages,
                    "index_stats": self.embedding_service.get_index_stats()
                }
            }
        except Exception as e:
            logger.error(f"Error populating embedding index by genre: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_embedding_stats(self) -> Dict[str, Any]:
        """Get embedding index statistics"""
        return self.embedding_service.get_index_stats()

    def get_embedding_content_list(self, content_type: Optional[str] = None, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """Get list of content in embedding index"""
        try:
            content_list = self.embedding_service.get_content_list(content_type, limit, offset)
            return {
                "content_list": content_list,
                "total_count": len(self.embedding_service.content_data),
                "filtered_count": len(content_list),
                "content_type": content_type,
                "limit": limit,
                "offset": offset
            }
        except Exception as e:
            logger.error(f"Error getting embedding content list: {str(e)}")
            return {"error": str(e)}

    def test_embedding(self, text: str) -> np.ndarray:
        """Test method to get embedding for a text"""
        try:
            embedding = self.embedding_service.model.encode([text])[0]
            return embedding
        except Exception as e:
            logger.error(f"Error generating test embedding: {str(e)}")
            raise 

    def add_recommendation_to_watchlist(self, user_id: int, tmdb_id: int, content_type: str, recommendation_id: int = None, recommendation_type: str = None, recommendation_score: float = None) -> bool:
        """Add a recommended content to user's watchlist with recommendation tracking"""
        try:
            from app.models.user_interaction import UserWatchlist, UserRecommendation
            
            # Check if already in watchlist
            existing_item = self.db.query(UserWatchlist).filter(
                UserWatchlist.user_id == user_id,
                UserWatchlist.tmdb_id == tmdb_id,
                UserWatchlist.content_type == content_type
            ).first()
            
            if existing_item:
                # Update existing item with recommendation info
                existing_item.from_recommendation = True
                existing_item.recommendation_id = recommendation_id
                existing_item.recommendation_type = recommendation_type
                existing_item.recommendation_score = recommendation_score
                self.db.commit()
                logger.info(f"Updated watchlist item {tmdb_id} with recommendation tracking")
                return True
            
            # Create new watchlist item
            watchlist_item = UserWatchlist(
                user_id=user_id,
                tmdb_id=tmdb_id,
                content_type=content_type,
                status="to_watch",
                from_recommendation=True,
                recommendation_id=recommendation_id,
                recommendation_type=recommendation_type,
                recommendation_score=recommendation_score
            )
            
            self.db.add(watchlist_item)
            self.db.commit()
            
            logger.info(f"Added recommendation {tmdb_id} to watchlist with tracking")
            return True
            
        except Exception as e:
            logger.error(f"Error adding recommendation to watchlist: {str(e)}")
            self.db.rollback()
            return False
    
    def get_recommendation_tracking_stats(self, user_id: int) -> Dict[str, Any]:
        """Get statistics about recommendation tracking"""
        try:
            from app.models.user_interaction import UserWatchlist, UserRecommendation
            
            # Get all watchlist items from recommendations
            recommended_watchlist = self.db.query(UserWatchlist).filter(
                UserWatchlist.user_id == user_id,
                UserWatchlist.from_recommendation == True
            ).all()
            
            # Get completed recommendations
            completed_recommendations = self.db.query(UserWatchlist).filter(
                UserWatchlist.user_id == user_id,
                UserWatchlist.from_recommendation == True,
                UserWatchlist.status == "completed"
            ).all()
            
            # Group by recommendation type
            type_stats = {}
            for item in recommended_watchlist:
                rec_type = item.recommendation_type or "unknown"
                if rec_type not in type_stats:
                    type_stats[rec_type] = {"total": 0, "completed": 0, "avg_score": 0}
                
                type_stats[rec_type]["total"] += 1
                if item.status == "completed":
                    type_stats[rec_type]["completed"] += 1
                
                if item.recommendation_score:
                    type_stats[rec_type]["avg_score"] += item.recommendation_score
            
            # Calculate averages
            for rec_type in type_stats:
                total = type_stats[rec_type]["total"]
                if total > 0:
                    type_stats[rec_type]["avg_score"] = round(type_stats[rec_type]["avg_score"] / total, 3)
                    type_stats[rec_type]["completion_rate"] = round((type_stats[rec_type]["completed"] / total) * 100, 2)
            
            return {
                "total_recommended": len(recommended_watchlist),
                "total_completed": len(completed_recommendations),
                "overall_completion_rate": round((len(completed_recommendations) / max(len(recommended_watchlist), 1)) * 100, 2),
                "by_recommendation_type": type_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting recommendation tracking stats: {str(e)}")
            return {} 