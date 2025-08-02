from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.auth import get_current_user
from app.db import get_db  # app.core.database yerine app.db
from app.core.exceptions import BaseAppException
from app.services.movie_service import MovieService
from app.schemas.movie import (
    UserRatingCreate, UserRatingResponse, UserWatchlistCreate, UserWatchlistResponse
)
from datetime import datetime
from app.models.user_interaction import UserWatchlist
from app.services.emotion_analysis_service import EmotionAnalysisService

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
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        movie_service = MovieService(db)
        rating = movie_service.rate_movie(current_user_id, rating_data)
        
        # Update emotion profile in real-time
        emotion_service = EmotionAnalysisService(db)
        emotion_service.update_user_emotion_profile_realtime(
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
        result = movie_service.get_user_ratings(current_user_id)
        
        if result["success"]:
            return result["data"]
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
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
        result = movie_service.add_to_watchlist(current_user_id, watchlist_data)
        
        if result["success"]:
            return result["data"]
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except Exception as e:
        raise handle_exception(e)

@router.get("/my/watchlist", response_model=List[UserWatchlistResponse])
def get_my_movie_watchlist(
    status: Optional[str] = Query(None, description="Filter by status ('to_watch', 'watching', 'completed')"),
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        movie_service = MovieService(db)
        result = movie_service.get_user_watchlist(current_user_id, status)
        
        if result["success"]:
            return result["data"]
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
    except Exception as e:
        raise handle_exception(e)

@router.put("/watchlist/{tmdb_id}")
def update_movie_watchlist_status(
    tmdb_id: int,
    status: str = Query(..., description="New status ('to_watch', 'watching', 'completed')"),
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        movie_service = MovieService(db)
        item = movie_service.update_movie_watchlist_status(current_user_id, tmdb_id, status)
        
        if item:
            # If status is completed, update emotion profile
            if status == "completed":
                emotion_service = EmotionAnalysisService(db)
                emotion_service.update_user_emotion_profile_realtime(
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

 

 