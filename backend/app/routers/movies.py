from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.auth import get_current_user
from app.db import get_db  # app.core.database yerine app.db
from app.core.exceptions import BaseAppException
from app.services.movie_service import MovieService
from app.schemas.movie import (
    UserRatingCreate, UserRatingResponse, UserWatchlistCreate, UserWatchlistResponse, UserWatchlistWithRatingResponse
)
from datetime import datetime
from app.models.user_interaction import UserWatchlist
from app.services.emotion_analysis_service import EmotionAnalysisService
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/movies", tags=["movies"])

def handle_exception(e: Exception) -> HTTPException:
    if isinstance(e, BaseAppException):
        return HTTPException(
            status_code=e.status_code,
            detail=e.message
        )
    else:
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred"
        )

# TMDB Movie Operations
@router.get("/popular")
def get_popular_movies(
    page: int = Query(1, ge=1, description="Page number"),
    db: Session = Depends(get_db)
):
    try:
        movie_service = MovieService(db)
        result = movie_service.get_popular_movies(page)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
    except Exception as e:
        raise handle_exception(e)

@router.get("/search")
def search_movies(
    query: str = Query(..., description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    db: Session = Depends(get_db)
):
    try:
        movie_service = MovieService(db)
        result = movie_service.search_movies(query, page)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
    except Exception as e:
        raise handle_exception(e)

@router.get("/{tmdb_id}")
def get_movie_details(
    tmdb_id: int,
    db: Session = Depends(get_db)
):
    try:
        movie_service = MovieService(db)
        result = movie_service.get_movie_details(tmdb_id)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Movie not found"
            )
    except Exception as e:
        raise handle_exception(e)

@router.get("/details-with-similar/{tmdb_id}")
def get_movie_details_with_similar(
    tmdb_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user)
):
    """Detay + similar içerikler (token varsa hibrit, yoksa emotion public)."""
    try:
        # 1) Detay
        movie_service = MovieService(db)
        detail_result = movie_service.get_movie_details(tmdb_id)
        if not detail_result["success"]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")

        detail = detail_result["data"]
        overview_text = detail.get("overview", "")

        # 2) Similar (token var: hybrid; yoksa public emotion)
        rec_service = RecommendationService(db)
        # Similar set içinde aynı içerik (tmdb_id) yer almamalı
        similar = rec_service.get_hybrid_recommendations(
            current_user_id,
            overview_text,
            content_type="movie",
            exclude_tmdb_ids={tmdb_id}
        )

        return {
            "success": True,
            "data": {
                "detail": detail,
                "similar": similar.get("data", {}).get("recommendations", [])
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise handle_exception(e)

@router.get("/details-with-similar-public/{tmdb_id}")
def get_movie_details_with_similar_public(
    tmdb_id: int,
    db: Session = Depends(get_db)
):
    """Detay + similar içerikler (public: token yok)."""
    try:
        from app.core.cache import CacheService
        cache_service = CacheService()
        cache_key = f"tmdb:movie:{tmdb_id}:details_similar_public"
        
        cached_result = cache_service.get_json(cache_key)
        if cached_result:
            return cached_result

        movie_service = MovieService(db)
        detail_result = movie_service.get_movie_details(tmdb_id)
        if not detail_result["success"]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")

        detail = detail_result["data"]
        overview_text = detail.get("overview", "")

        rec_service = RecommendationService(db)
        similar = rec_service.get_emotion_based_recommendations_public(
            overview_text, content_type="movie", exclude_tmdb_ids={tmdb_id}
        )

        response_data = {
            "success": True,
            "data": {
                "detail": detail,
                "similar": similar.get("data", {}).get("recommendations", [])
            }
        }
        
        # Cache for 24 hours (86400 seconds)
        cache_service.set_json(cache_key, response_data, 86400)
        
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        raise handle_exception(e)

@router.get("/details-public/{tmdb_id}")
def get_movie_details_public(
    tmdb_id: int,
    db: Session = Depends(get_db)
):
    """Sadece film detaylarını döner (public)."""
    try:
        from app.core.cache import CacheService
        cache_service = CacheService()
        cache_key = f"tmdb:movie:{tmdb_id}:details_public"
        
        cached_result = cache_service.get_json(cache_key)
        if cached_result:
            return cached_result

        movie_service = MovieService(db)
        detail_result = movie_service.get_movie_details(tmdb_id)
        if not detail_result["success"]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")

        response_data = {
            "success": True,
            "data": detail_result["data"]
        }
        
        # Cache for 24 hours
        cache_service.set_json(cache_key, response_data, 86400)
        
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        raise handle_exception(e)

@router.get("/similar-public/{tmdb_id}")
def get_similar_movies_public(
    tmdb_id: int,
    db: Session = Depends(get_db)
):
    """Benzer filmleri döner (public, 12 adet)."""
    try:
        from app.core.cache import CacheService
        cache_service = CacheService()
        cache_key = f"tmdb:movie:{tmdb_id}:similar_public_v2" # v2 because limit is 12 now
        
        cached_result = cache_service.get_json(cache_key)
        if cached_result:
            return cached_result

        movie_service = MovieService(db)
        detail_result = movie_service.get_movie_details(tmdb_id)
        if not detail_result["success"]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")

        detail = detail_result["data"]
        overview_text = detail.get("overview", "")

        rec_service = RecommendationService(db)
        # 12 tane dönmesi istendi
        similar = rec_service.get_emotion_based_recommendations_public(
            overview_text, 
            content_type="movie", 
            exclude_tmdb_ids={tmdb_id},
            page_size=12
        )

        response_data = {
            "success": True,
            "data": similar.get("data", {}).get("recommendations", [])
        }
        
        # Cache for 24 hours
        cache_service.set_json(cache_key, response_data, 86400)
        
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        raise handle_exception(e)

@router.get("/{tmdb_id}/watch-providers")
def get_movie_watch_providers(
    tmdb_id: int,
    db: Session = Depends(get_db)
):
    try:
        movie_service = MovieService(db)
        result = movie_service.get_movie_watch_providers(tmdb_id)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
    except Exception as e:
        raise handle_exception(e)

# User Rating Operations
@router.post("/rate", response_model=UserRatingResponse)
def rate_movie(
    rating_data: UserRatingCreate,
    background_tasks: BackgroundTasks,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        movie_service = MovieService(db)
        rating = movie_service.rate_movie(current_user_id, rating_data)
        
        # Update emotion profile in background to avoid blocking the API response
        emotion_service = EmotionAnalysisService(db)
        background_tasks.add_task(
            emotion_service.update_user_emotion_profile_realtime,
            current_user_id, 
            rating_data.tmdb_id, 
            rating_data.rating, 
            rating_data.content_type
        )
        
        return rating
    except Exception as e:
        raise handle_exception(e)

@router.get("/my/ratings", response_model=List[UserRatingResponse])
def get_my_movie_ratings(
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        movie_service = MovieService(db)
        result = movie_service.get_user_movie_ratings(current_user_id)
        return result
    except Exception as e:
        raise handle_exception(e)

# Watchlist Operations
@router.post("/watchlist", response_model=UserWatchlistResponse)
def add_movie_to_watchlist(
    watchlist_data: UserWatchlistCreate,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        movie_service = MovieService(db)
        result = movie_service.add_movie_to_watchlist(current_user_id, watchlist_data)
        return result
    except Exception as e:
        raise handle_exception(e)

@router.get("/my/watchlist", response_model=List[UserWatchlistWithRatingResponse])
def get_my_movie_watchlist(
    status: Optional[str] = Query(None, description="Filter by status ('to_watch', 'watching', 'completed')"),
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        movie_service = MovieService(db)
        enriched = movie_service.get_user_movie_watchlist_with_ratings(current_user_id, status)
        return enriched
    except Exception as e:
        raise handle_exception(e)

# Not: Rating tekil sorgu ve watchlist-with-ratings endpointleri kaldırıldı; 
# mevcut /my/watchlist artık rating bilgisini de döndürüyor.

@router.put("/watchlist/{tmdb_id}")
def update_movie_watchlist_status(
    tmdb_id: int,
    background_tasks: BackgroundTasks,
    status: str = Query(..., description="New status ('to_watch', 'watching', 'completed')"),
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        movie_service = MovieService(db)
        item = movie_service.update_movie_watchlist_status(current_user_id, tmdb_id, status)
        
        if item:
            # If status is completed, update emotion profile in background
            if status == "completed":
                emotion_service = EmotionAnalysisService(db)
                background_tasks.add_task(
                    emotion_service.update_user_emotion_profile_realtime,
                    current_user_id, 
                    tmdb_id, 
                    7.0,  # Default rating for completed items
                    "movie"
                )
            
            return item
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Watchlist item not found"
            )
    except Exception as e:
        raise handle_exception(e) 

 

 