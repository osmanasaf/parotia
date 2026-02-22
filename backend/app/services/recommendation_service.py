import logging
import random
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
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
from app.core.cache import CacheService

logger = logging.getLogger(__name__)

# Performance/limit constants
# 5 sayfa x 9 = 45
PAGE_SIZE = 9
MAX_PAGES = 5
MAX_RECOMMENDATIONS = PAGE_SIZE * MAX_PAGES  # 45
EMBEDDING_TOP_K = 200
MIN_VOTE_AVERAGE = 6.0
MIN_VOTE_COUNT = 200
DETAILS_FETCH_CHUNK = PAGE_SIZE * 2

class RecommendationService:
    """Service for AI-based recommendation operations"""
    
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.cache = CacheService()
        
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

    # =========================================================================
    # YARDIMCI / ORTAK METODLAR (DRY & Performans)
    # =========================================================================

    def _get_emotion_embedding(self, text: str) -> Optional[np.ndarray]:
        """Encode emotion text directly using EmbeddingService (now cached)."""
        try:
            embedding = self.embedding_service.encode_text(text)
            if embedding.size == 0:
                return None
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            return embedding
        except Exception:
            return None

    def _search_by_emotion_or_text(self, content_type: str, emotion_embedding: Optional[np.ndarray], text: str):
        if emotion_embedding is not None:
            results = self.embedding_service.search_similar_content(
                query_text="",
                top_k=EMBEDDING_TOP_K,
                content_type=content_type,
                query_embedding=emotion_embedding,
            )
        else:
            results = self.embedding_service.search_similar_content(
                query_text=text,
                top_k=EMBEDDING_TOP_K,
                content_type=content_type,
            )
        return self._shuffle_within_score_bands(results)

    @staticmethod
    def _shuffle_within_score_bands(results: List[Dict[str, Any]], band_size: float = 0.02) -> List[Dict[str, Any]]:
        """Shuffle items that have very similar scores to add variety."""
        if not results:
            return results
        bands: List[List[Dict[str, Any]]] = []
        current_band: List[Dict[str, Any]] = []
        band_anchor: float = results[0].get("similarity_score", 0.0)
        for item in results:
            score = item.get("similarity_score", 0.0)
            if abs(score - band_anchor) <= band_size:
                current_band.append(item)
            else:
                bands.append(current_band)
                current_band = [item]
                band_anchor = score
        if current_band:
            bands.append(current_band)
        shuffled: List[Dict[str, Any]] = []
        for band in bands:
            random.shuffle(band)
            shuffled.extend(band)
        return shuffled

    def _fetch_details(self, content_type: str, tmdb_id: int) -> Optional[Dict[str, Any]]:
        if content_type == "movie":
            resp = self.tmdb_movie_service.get_movie_details(tmdb_id)
        else:
            resp = self.tmdb_tv_service.get_tv_show_details(tmdb_id)
        if not resp or not resp.success:
            return None
        return resp.data

    def _build_clean_rec(self, tmdb_id: int, content_type: str, content_data: Dict[str, Any], similarity_score: float, current_len: int) -> Dict[str, Any]:
        return {
            "tmdb_id": tmdb_id,
            "content_type": content_type,
            "title": content_data.get("title") or content_data.get("name") or "",
            "overview": content_data.get("overview", ""),
            "backdrop_path": content_data.get("backdrop_path"),
            "poster_path": content_data.get("poster_path"),
            "release_date": content_data.get("release_date") or content_data.get("first_air_date"),
            "vote_average": content_data.get("vote_average", 0),
            "similarity_score": round(float(similarity_score) * 100),
            "rank": current_len + 1,
        }

    def _stable_page_enrich_single(self, candidate_ids: list, page: int, content_type: str, *, save_params: Optional[Dict[str, Any]] = None, page_size: int = PAGE_SIZE) -> List[Dict[str, Any]]:
        page = min(max(page, 1), MAX_PAGES)
        start = (page - 1) * page_size
        clean: List[Dict[str, Any]] = []
        i = start
        while i < len(candidate_ids) and len(clean) < page_size:
            end = min(i + DETAILS_FETCH_CHUNK, len(candidate_ids))

            def _job(idx: int):
                tmdb_id, sim_score = candidate_ids[idx]
                data = self._fetch_details(content_type, tmdb_id)
                if not data:
                    return idx, None, None, None
                if data.get("vote_average", 0) < MIN_VOTE_AVERAGE:
                    return idx, None, None, None
                return idx, tmdb_id, sim_score, data

            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(_job, range(i, end)))

            for idx, tmdb_id, sim_score, data in sorted(results, key=lambda x: x[0]):
                if data is None:
                    continue
                clean_rec = self._build_clean_rec(tmdb_id, content_type, data, sim_score, len(clean))
                clean.append(clean_rec)
                if save_params:
                    try:
                        self.recommendation_repo.save_recommendation(
                            user_id=save_params["user_id"],
                            tmdb_id=tmdb_id,
                            content_type=content_type,
                            recommendation_type=save_params.get("recommendation_type"),
                            emotion_state=save_params.get("emotion_state"),
                            score=sim_score,
                        )
                    except Exception:
                        pass
                if len(clean) >= page_size:
                    break

            i = end
        return clean

    def _stable_page_enrich_mixed(self, candidate_ids: list, page: int, page_size: int = PAGE_SIZE) -> List[Dict[str, Any]]:
        page = min(max(page, 1), MAX_PAGES)
        start = (page - 1) * page_size
        clean: List[Dict[str, Any]] = []
        i = start
        while i < len(candidate_ids) and len(clean) < page_size:
            end = min(i + DETAILS_FETCH_CHUNK, len(candidate_ids))

            def _job(idx: int):
                tmdb_id, sim_score, ct = candidate_ids[idx]
                data = self._fetch_details(ct, tmdb_id)
                if not data or data.get("vote_average", 0) < MIN_VOTE_AVERAGE:
                    return idx, None, None, None, None
                return idx, tmdb_id, sim_score, ct, data

            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(_job, range(i, end)))

            for idx, tmdb_id, sim_score, ct, data in sorted(results, key=lambda x: x[0]):
                if data is None:
                    continue
                clean_rec = self._build_clean_rec(tmdb_id, ct, data, sim_score, len(clean))
                clean.append(clean_rec)
                if len(clean) >= page_size:
                    break

            i = end
        return clean

    # ============================================================================
    # KULLANICI ÖNERİ METODLARI
    # ============================================================================

    def get_emotion_based_recommendations(self, user_id: int, emotion_data: EmotionBasedRecommendation) -> Dict[str, Any]:
        """Kullanıcının anlık duygu durumuna göre öneriler (Redis Önbellekli)."""
        try:
            # Handle "all" content type
            if emotion_data.content_type == "all":
                return self._get_emotion_based_recommendations_all(user_id, emotion_data)
            
            # 1. Check Redis Cache
            page = getattr(emotion_data, "page", 1)
            cache_key = f"rec:emotion:{user_id}:{emotion_data.emotion}:{emotion_data.content_type}:p{page}"
            cached_result = self.cache.get_json(cache_key)
            if cached_result:
                logger.info(f"Returning cached emotion recommendations for user {user_id}")
                return cached_result

            # Get emotion embedding (model supports Turkish and 50+ languages natively)
            emb = self._get_emotion_embedding(emotion_data.emotion)
            recommendations = self._search_by_emotion_or_text(
                emotion_data.content_type, emb, emotion_data.emotion
            )
            
            # Prepare candidate IDs (lazy)
            user_ratings = self.rating_repo.get_user_ratings(user_id, emotion_data.content_type)
            watched_tmdb_ids = {rating.tmdb_id for rating in user_ratings}
            seen_tmdb_ids = set()
            candidate_ids = []
            for rec in recommendations:
                tmdb_id = rec.get("tmdb_id")
                if tmdb_id is None or tmdb_id in seen_tmdb_ids or tmdb_id in watched_tmdb_ids:
                    continue
                seen_tmdb_ids.add(tmdb_id)
                candidate_ids.append((tmdb_id, rec.get("similarity_score", 0.0)))
                if len(candidate_ids) >= MAX_RECOMMENDATIONS:
                    break

            # Yüksek benzerlik öne
            candidate_ids.sort(key=lambda x: x[1], reverse=True)

            # Pagination with stable PAGE_SIZE items (fill by looking ahead)
            page = min(max(getattr(emotion_data, "page", 1), 1), MAX_PAGES)
            clean_recommendations = self._stable_page_enrich_single(
                candidate_ids,
                page,
                emotion_data.content_type,
                save_params={
                    "user_id": user_id,
                    "recommendation_type": "current_emotion",
                    "emotion_state": emotion_data.emotion,
                },
            )
            
            final_result = {
                "success": True,
                "data": {
                    "recommendations": clean_recommendations,
                    "emotion": emotion_data.emotion,
                    "content_type": emotion_data.content_type,
                    "total": len(candidate_ids),
                    "page": page,
                    "page_size": PAGE_SIZE,
                    "total_pages": min((len(candidate_ids) + PAGE_SIZE - 1) // PAGE_SIZE, MAX_PAGES),
                    "method": "current_emotion"
                }
            }
            # 2. Save to Cache (5 minutes TTL)
            self.cache.set_json(cache_key, final_result, 300)
            return final_result
        except Exception as e:
            logger.error(f"Error getting emotion-based recommendations: {str(e)}")
            return {"success": False, "error": str(e)}

    # ============================================================================
    # KAMUYA AÇIK (AUTH GEREKTİRMEYEN) ÖNERİ METODLARI
    # ============================================================================

    def get_emotion_based_recommendations_public(self, emotion_text: str, content_type: str = "movie", exclude_tmdb_ids: Optional[set] = None, page: int = 1, page_size: int = PAGE_SIZE) -> Dict[str, Any]:
        """Token gerektirmeyen, anlık duygu metnine göre öneriler (Redis Önbellekli)."""
        try:
            # All türü için hem movie hem tv sonuçlarını birleştir
            if content_type == "all":
                return self._get_emotion_based_recommendations_public_all(emotion_text, page)
            
            # 1. Önbellek Kontrolü (Public sonuçlar paylaşımlıdır, user_id içermez)
            cache_key = f"rec:public:emotion:{emotion_text}:{content_type}:p{page}:sz{page_size}"
            cached = self.cache.get_json(cache_key)
            if cached:
                return cached

            # Get current emotion embedding (model supports Turkish and 50+ languages natively)
            emb = self._get_emotion_embedding(emotion_text)
            recommendations = self._search_by_emotion_or_text(content_type, emb, emotion_text)

            seen_tmdb_ids = set()
            exclude_ids = set(exclude_tmdb_ids or [])
            candidate_ids = []

            for rec in recommendations:
                tmdb_id = rec.get("tmdb_id")
                if tmdb_id is None or tmdb_id in seen_tmdb_ids or tmdb_id in exclude_ids:
                    continue
                seen_tmdb_ids.add(tmdb_id)

                try:
                    candidate_ids.append((tmdb_id, float(rec.get("similarity_score", 0.0))))
                    if len(candidate_ids) >= MAX_RECOMMENDATIONS:
                        break
                except Exception:
                    continue

            # Yüksek benzerlik öne
            candidate_ids.sort(key=lambda x: x[1], reverse=True)

            # Pagination indices (1..MAX_PAGES)
            page = min(max(page, 1), MAX_PAGES)
            clean_recommendations = self._stable_page_enrich_single(
                candidate_ids,
                page,
                content_type,
                page_size=page_size
            )

            final_result = {
                "success": True,
                "data": {
                    "recommendations": clean_recommendations,
                    "emotion": emotion_text,
                    "content_type": content_type,
                    "total": len(candidate_ids),
                    "page": page,
                    "page_size": page_size,
                    "total_pages": min((len(candidate_ids) + page_size - 1) // page_size, MAX_PAGES),
                    "method": "emotion_public"
                }
            }
            self.cache.set_json(cache_key, final_result, 600)  # 10 dakikalık public cache
            return final_result
        except Exception as e:
            logger.error(f"Error getting public emotion-based recommendations: {str(e)}")
            return {"success": False, "error": str(e)}

    def _get_emotion_based_recommendations_public_all(self, emotion_text: str, page: int, page_size: int = PAGE_SIZE) -> Dict[str, Any]:
        """Public all: movie ve tv adaylarını birleştirip 9'luk sayfa döndürür."""
        try:
            # 1) Emotion embedding (model supports Turkish and 50+ languages natively)
            emb = self._get_emotion_embedding(emotion_text)

            # 2) Her tür için arama yap
            def search_for_type(ct: str):
                return self._search_by_emotion_or_text(ct, emb, emotion_text)

            movie_recs = search_for_type("movie")
            tv_recs = search_for_type("tv")

            # 3) Aday havuzu (tmdb_id, score, content_type)
            seen_ids = set()
            candidate_ids: list[tuple[int, float, str]] = []
            for ct, recs in (("movie", movie_recs), ("tv", tv_recs)):
                for rec in recs:
                    tmdb_id = rec.get("tmdb_id")
                    if tmdb_id is None or (ct, tmdb_id) in seen_ids:
                        continue
                    seen_ids.add((ct, tmdb_id))
                    candidate_ids.append((tmdb_id, float(rec.get("similarity_score", 0.0)), ct))
                    if len(candidate_ids) >= MAX_RECOMMENDATIONS:
                        break

            # Yüksek benzerlik öne
            candidate_ids.sort(key=lambda x: x[1], reverse=True)

            # 4) Stabil sayfalama (9 öğe doldurmak için ileri bakış)
            page = min(max(page, 1), MAX_PAGES)
            clean_recommendations = self._stable_page_enrich_mixed(candidate_ids, page, page_size=page_size)

            return {
                "success": True,
                "data": {
                    "recommendations": clean_recommendations,
                    "emotion": emotion_text,
                    "content_type": "all",
                    "total": len(candidate_ids),
                    "page": page,
                    "page_size": page_size,
                    "total_pages": min((len(candidate_ids) + page_size - 1) // page_size, MAX_PAGES),
                    "method": "emotion_public_all"
                }
            }
        except Exception as e:
            logger.error(f"Error getting public emotion-based recommendations (all): {str(e)}")
            return {"success": False, "error": str(e)}

    def get_hybrid_recommendations(self, user_id: int, emotion_text: str, content_type: str = "movie", page: int = 1, exclude_tmdb_ids: Optional[set] = None) -> Dict[str, Any]:
        """Hibrit öneriler: anlık duygu + geçmiş profil birleşimi (Redis Önbellekli)."""
        try:
            # Handle "all" content type
            if content_type == "all":
                return self._get_hybrid_recommendations_all(user_id, emotion_text, page)
            
            # 1. Check Redis Cache
            cache_key = f"rec:hybrid:{user_id}:{emotion_text}:{content_type}:p{page}"
            cached_result = self.cache.get_json(cache_key)
            if cached_result:
                logger.info(f"Returning cached hybrid recommendations for user {user_id}")
                return cached_result

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
                raw_recommendations = self.embedding_service.search_similar_content(
                    query_text="",
                    top_k=EMBEDDING_TOP_K,
                    content_type=content_type,
                    query_embedding=hybrid_embedding
                )
                recommendations = self._shuffle_within_score_bands(raw_recommendations)
            else:
                # Fallback to emotion-based search
                if emotion_embedding:
                    recommendations = self._search_by_emotion_or_text(content_type, np.array(emotion_embedding), emotion_text)
                else:
                    recommendations = self._search_by_emotion_or_text(content_type, None, emotion_text)
            
            # Prepare candidate IDs (lazy) — skor bazlı sıralama
            user_ratings = self.rating_repo.get_user_ratings(user_id, content_type)
            watched_tmdb_ids = {rating.tmdb_id for rating in user_ratings}
            seen_tmdb_ids = set()
            exclude_ids = set(exclude_tmdb_ids or [])
            candidate_ids = []
            for rec in recommendations:
                tmdb_id = rec.get("tmdb_id")
                if tmdb_id is None or tmdb_id in seen_tmdb_ids or tmdb_id in watched_tmdb_ids or tmdb_id in exclude_ids:
                    continue
                seen_tmdb_ids.add(tmdb_id)
                candidate_ids.append((tmdb_id, rec.get("similarity_score", 0.0)))
                if len(candidate_ids) >= MAX_RECOMMENDATIONS:
                    break
            # yüksek benzerlik öne
            candidate_ids.sort(key=lambda x: x[1], reverse=True)

            # Pagination indices (from router) with stable PAGE_SIZE
            page = min(max(page, 1), MAX_PAGES) # Ensure page is within valid range
            clean_recommendations = self._stable_page_enrich_single(
                candidate_ids,
                page,
                content_type,
                save_params={
                    "user_id": user_id,
                    "recommendation_type": "hybrid",
                    "emotion_state": emotion_text,
                },
            )
            
            final_result = {
                "success": True,
                "data": {
                    "recommendations": clean_recommendations,
                    "emotion": emotion_text,
                    "content_type": content_type,
                    "total": len(candidate_ids),
                    "page": page,
                    "page_size": PAGE_SIZE,
                    "total_pages": min((len(candidate_ids) + PAGE_SIZE - 1) // PAGE_SIZE, MAX_PAGES),
                    "user_emotion_confidence": user_emotion.get("confidence", 0.0),
                    "current_emotion_confidence": emotion_analysis.get("confidence", 0.0),
                    "recommendation_type": "hybrid",
                    "weights": {
                        "current_emotion": 0.7,
                        "user_profile": 0.3
                    }
                }
            }
            # 2. Save to Cache (5 minutes TTL)
            self.cache.set_json(cache_key, final_result, 300)
            return final_result
        except Exception as e:
            logger.error(f"Error getting hybrid recommendations: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_history_based_recommendations(self, user_id: int, history_data: HistoryBasedRecommendation) -> Dict[str, Any]:
        """Kullanıcının izleme geçmişine göre öneriler."""
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
            
            # Convert to format expected by embedding service (lightweight, no TMDB fetch)
            ratings_data = []
            for rating in user_ratings:
                try:
                    ratings_data.append({
                        "tmdb_id": rating.tmdb_id,
                        "content_type": rating.content_type,
                        "rating": rating.rating,
                    })
                except Exception as e:
                    logger.warning(f"Error preparing rating data for {rating.tmdb_id}: {str(e)}")
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
                top_k=EMBEDDING_TOP_K,
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
                            "similarity_score": round(float(rec.get("similarity_score", 0.0)) * 100),
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
                        
                        if len(clean_recommendations) >= MAX_RECOMMENDATIONS:
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
        """Kullanıcının emotion profile'ına göre öneriler."""
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
                top_k=EMBEDDING_TOP_K,
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
                            "similarity_score": round(float(rec.get("similarity_score", 0.0)) * 100),
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
                        
                        if len(clean_recommendations) >= MAX_RECOMMENDATIONS:
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

    def _get_hybrid_recommendations_all(self, user_id: int, emotion_text: str, page: int = 1) -> Dict[str, Any]:
        """Hybrid önerileri her iki tür için getirir ve sayfalar."""
        try:
            user_emotion = self.emotion_service.get_cached_user_emotion_profile(user_id, "movie")
            user_emotion_embedding = user_emotion.get("emotion_embedding", [])
            
            emotion_analysis = self.emotion_service.analyze_user_emotion(emotion_text)
            emotion_embedding = emotion_analysis.get("emotion_embedding", [])
            
            if not user_emotion_embedding:
                return self._get_emotion_based_recommendations_all(
                    user_id, EmotionBasedRecommendation(emotion=emotion_text, content_type="all", page=page)
                )

            # Weight combination
            if emotion_embedding and user_emotion_embedding:
                emotion_weight = 0.7
                user_weight = 0.3
                hybrid_embedding = (np.array(emotion_embedding) * emotion_weight + np.array(user_emotion_embedding) * user_weight)
                
                movie_recs = self.embedding_service.search_similar_content("", EMBEDDING_TOP_K, "movie", hybrid_embedding)
                tv_recs = self.embedding_service.search_similar_content("", EMBEDDING_TOP_K, "tv", hybrid_embedding)
            else:
                movie_recs = self.embedding_service.search_similar_content(emotion_text, EMBEDDING_TOP_K, "movie")
                tv_recs = self.embedding_service.search_similar_content(emotion_text, EMBEDDING_TOP_K, "tv")

            # Shuffle and combine
            movie_recs = self._shuffle_within_score_bands(movie_recs)
            tv_recs = self._shuffle_within_score_bands(tv_recs)
            
            user_ratings_movie = self.rating_repo.get_user_ratings(user_id, "movie")
            user_ratings_tv = self.rating_repo.get_user_ratings(user_id, "tv")
            watched_movie_ids = {rating.tmdb_id for rating in user_ratings_movie}
            watched_tv_ids = {rating.tmdb_id for rating in user_ratings_tv}

            candidate_ids_movie = [(rec.get("tmdb_id"), rec.get("similarity_score", 0.0), "movie") 
                                 for rec in movie_recs if rec.get("tmdb_id") not in watched_movie_ids]
            candidate_ids_tv = [(rec.get("tmdb_id"), rec.get("similarity_score", 0.0), "tv") 
                              for rec in tv_recs if rec.get("tmdb_id") not in watched_tv_ids]

            all_candidates = candidate_ids_movie + candidate_ids_tv
            all_candidates.sort(key=lambda x: x[1], reverse=True)
            
            # Apply pagination
            page = min(max(page, 1), MAX_PAGES)
            start = (page - 1) * PAGE_SIZE
            clean = []
            
            i = start
            while i < len(all_candidates) and len(clean) < PAGE_SIZE:
                end = min(i + DETAILS_FETCH_CHUNK, len(all_candidates))
                
                def _job(idx: int):
                    tmdb_id, sim_score, c_type = all_candidates[idx]
                    data = self._fetch_details(c_type, tmdb_id)
                    if not data or data.get("vote_average", 0) < MIN_VOTE_AVERAGE:
                        return idx, None, None, None, None
                    return idx, tmdb_id, sim_score, data, c_type

                with ThreadPoolExecutor(max_workers=8) as pool:
                    results = list(pool.map(_job, range(i, end)))

                for idx, tmdb_id, sim_score, data, c_type in sorted(results, key=lambda x: x[0]):
                    if data is None: continue
                    clean_rec = self._build_clean_rec(tmdb_id, c_type, data, sim_score, len(clean))
                    clean.append(clean_rec)
                    try:
                        self.recommendation_repo.save_recommendation(
                            user_id=user_id, tmdb_id=tmdb_id, content_type=c_type,
                            recommendation_type="hybrid", emotion_state=emotion_text, score=sim_score
                        )
                    except Exception: pass
                    if len(clean) >= PAGE_SIZE: break
                
                i = end

            movie_count = len([r for r in clean if r["content_type"] == "movie"])
            tv_count = len([r for r in clean if r["content_type"] == "tv"])

            return {
                "success": True,
                "data": {
                    "recommendations": clean,
                    "emotion": emotion_text,
                    "content_type": "all",
                    "total": len(all_candidates),
                    "page": page,
                    "page_size": PAGE_SIZE,
                    "total_pages": min((len(all_candidates) + PAGE_SIZE - 1) // PAGE_SIZE, MAX_PAGES),
                    "breakdown": {"movies": movie_count, "tv_shows": tv_count},
                    "recommendation_type": "hybrid_all"
                }
            }
        except Exception as e:
            logger.error(f"Error getting hybrid recommendations for all content types: {str(e)}")
            return {"success": False, "error": str(e)}

    def _get_emotion_based_recommendations_all(self, user_id: int, emotion_data: EmotionBasedRecommendation) -> Dict[str, Any]:
        """Emotion-based önerileri her iki tür için getirir."""
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
            
            # Save the index and optimize if large
            self.embedding_service.save_index()
            ivf_optimized = self.embedding_service.optimize_index_if_large()
            
            return {
                "success": True,
                "data": {
                    "added_count": added_count,
                    "content_type": content_type,
                    "pages": pages,
                    "index_stats": self.embedding_service.get_index_stats(),
                    "ivf_optimized": ivf_optimized
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

    def populate_recent_content(self, content_type: str = "movie", days: int = 1, pages: int = 3, use_details: bool = False) -> Dict[str, Any]:
        """Populate embedding index with recently released/airing content.

        Params:
        - content_type: "movie" | "tv"
        - days: kaç gün öncesinden başlasın (UTC)
        - pages: TMDB discover sayfa sayısı
        - use_details: Her içerik için detayları çekip zengin metinle embed et
        """
        try:
            from_date = (datetime.utcnow() - timedelta(days=days)).date().isoformat()
            added = 0
            skipped = 0
            failed = 0

            for page in range(1, pages + 1):
                if content_type == "movie":
                    # Discover by release date
                    response = self.tmdb_movie_service.discover_movies(
                        page,
                        sort_by="popularity.desc",
                        **{
                            "primary_release_date.gte": from_date,
                            "vote_average.gte": MIN_VOTE_AVERAGE,
                        }
                    )
                else:
                    response = self.tmdb_tv_service.discover_tv_shows(
                        page,
                        sort_by="popularity.desc",
                        **{
                            "first_air_date.gte": from_date,
                            "vote_average.gte": MIN_VOTE_AVERAGE,
                        }
                    )

                if not response.success:
                    failed += 1
                    continue

                for content in response.data.get("results", []):
                    try:
                        tmdb_id = content.get("id")
                        if not tmdb_id:
                            skipped += 1
                            continue

                        # Normalize fields
                        content["tmdb_id"] = tmdb_id
                        content["content_type"] = content_type

                        if use_details:
                            # Fetch details for richer text
                            if content_type == "movie":
                                details = self.tmdb_movie_service.get_movie_details(tmdb_id)
                            else:
                                details = self.tmdb_tv_service.get_tv_show_details(tmdb_id)

                            if details and details.success:
                                full = details.data
                                full["tmdb_id"] = tmdb_id
                                full["content_type"] = content_type
                                ok = self.embedding_service.add_content_with_details(full, self.db)
                            else:
                                ok = self.embedding_service.add_content(content)
                        else:
                            ok = self.embedding_service.add_content(content)

                        if ok:
                            added += 1
                        else:
                            skipped += 1
                    except Exception:
                        failed += 1

            # Save the index after population and optimize if large
            self.embedding_service.save_index()
            ivf_optimized = self.embedding_service.optimize_index_if_large()

            return {
                "success": True,
                "data": {
                    "added": added,
                    "skipped": skipped,
                    "failed_pages": failed,
                    "content_type": content_type,
                    "days": days,
                    "pages": pages,
                    "index_stats": self.embedding_service.get_index_stats(),
                    "ivf_optimized": ivf_optimized,
                },
            }
        except Exception as e:
            logger.error(f"Error populating recent content: {str(e)}")
            return {"success": False, "error": str(e)}

    def bulk_populate_popular(self, content_type: str = "movie", start_page: int = 1, end_page: int = 500, use_details: bool = False) -> Dict[str, Any]:
        """Bulk populate using TMDB 'popular' pages in range [start_page, end_page]."""
        try:
            added = 0
            failed_pages = 0
            skipped = 0

            get_page = self.tmdb_movie_service.get_popular_movies if content_type == "movie" else self.tmdb_tv_service.get_popular_tv_shows

            for page in range(start_page, end_page + 1):
                response = get_page(page)
                if not response.success:
                    failed_pages += 1
                    continue

                for content in response.data.get("results", []):
                    tmdb_id = content.get("id")
                    if not tmdb_id:
                        skipped += 1
                        continue
                    content["tmdb_id"] = tmdb_id
                    content["content_type"] = content_type

                    ok = False
                    if use_details:
                        if content_type == "movie":
                            details = self.tmdb_movie_service.get_movie_details(tmdb_id)
                        else:
                            details = self.tmdb_tv_service.get_tv_show_details(tmdb_id)
                        if details and details.success:
                            full = details.data
                            full["tmdb_id"] = tmdb_id
                            full["content_type"] = content_type
                            ok = self.embedding_service.add_content_with_details(full, self.db)
                    if not use_details or not ok:
                        ok = self.embedding_service.add_content(content)

                    if ok:
                        added += 1
                    else:
                        skipped += 1

            self.embedding_service.save_index()
            ivf_optimized = self.embedding_service.optimize_index_if_large()
            return {
                "success": True,
                "data": {
                    "added": added,
                    "failed_pages": failed_pages,
                    "skipped": skipped,
                    "range": [start_page, end_page],
                    "content_type": content_type,
                    "index_stats": self.embedding_service.get_index_stats(),
                    "ivf_optimized": ivf_optimized,
                },
            }
        except Exception as e:
            logger.error(f"Error in bulk_populate_popular: {str(e)}")
            return {"success": False, "error": str(e)}

    def continue_bulk_popular(self, content_type: str = "movie", batch_pages: int = 25, use_details: bool = False) -> Dict[str, Any]:
        """Continue bulk popular ingestion from the last saved page in Redis.

        Stores progress per content_type in key: tmdb:ingest:popular:{content_type}:last_page
        """
        try:
            key = f"tmdb:ingest:popular:{content_type}:last_page"
            last_page_raw = self.cache.get_json(key)
            last_page = int(last_page_raw) if isinstance(last_page_raw, (int, str)) and str(last_page_raw).isdigit() else 0
            start_page = max(1, last_page + 1)
            end_page = min(500, start_page + batch_pages - 1)

            result = self.bulk_populate_popular(content_type, start_page, end_page, use_details)
            if result.get("success"):
                # Persist new last page
                self.cache.set_json(key, end_page, ttl_seconds=7 * 24 * 60 * 60)
                result["data"]["start_page"] = start_page
                result["data"]["end_page"] = end_page
                result["data"]["last_page_saved"] = end_page
            return result
        except Exception as e:
            logger.error(f"Error in continue_bulk_popular: {str(e)}")
            return {"success": False, "error": str(e)}

    def bulk_populate_by_year(self, content_type: str = "movie", year: int = 2020, pages: int = 100, use_details: bool = False) -> Dict[str, Any]:
        """Bulk populate using TMDB discover by year."""
        try:
            added = 0
            skipped = 0
            failed_pages = 0

            for page in range(1, pages + 1):
                if content_type == "movie":
                    response = self.tmdb_movie_service.discover_movies(
                        page,
                        sort_by="popularity.desc",
                        primary_release_year=year,
                        **{"vote_average.gte": MIN_VOTE_AVERAGE}
                    )
                else:
                    response = self.tmdb_tv_service.discover_tv_shows(
                        page,
                        sort_by="popularity.desc",
                        first_air_date_year=year,
                        **{"vote_average.gte": MIN_VOTE_AVERAGE}
                    )
                if not response.success:
                    failed_pages += 1
                    continue
                for content in response.data.get("results", []):
                    tmdb_id = content.get("id")
                    if not tmdb_id:
                        skipped += 1
                        continue
                    content["tmdb_id"] = tmdb_id
                    content["content_type"] = content_type
                    ok = False
                    if use_details:
                        if content_type == "movie":
                            details = self.tmdb_movie_service.get_movie_details(tmdb_id)
                        else:
                            details = self.tmdb_tv_service.get_tv_show_details(tmdb_id)
                        if details and details.success:
                            full = details.data
                            full["tmdb_id"] = tmdb_id
                            full["content_type"] = content_type
                            ok = self.embedding_service.add_content_with_details(full, self.db)
                    if not use_details or not ok:
                        ok = self.embedding_service.add_content(content)
                    if ok:
                        added += 1
                    else:
                        skipped += 1
            self.embedding_service.save_index()
            ivf_optimized = self.embedding_service.optimize_index_if_large()
            return {
                "success": True,
                "data": {
                    "added": added,
                    "skipped": skipped,
                    "failed_pages": failed_pages,
                    "year": year,
                    "pages": pages,
                    "content_type": content_type,
                    "index_stats": self.embedding_service.get_index_stats(),
                    "ivf_optimized": ivf_optimized,
                },
            }
        except Exception as e:
            logger.error(f"Error in bulk_populate_by_year: {str(e)}")
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