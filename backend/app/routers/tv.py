from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db import get_db
from app.core.auth import get_current_user
from app.core.exceptions import BaseAppException
from app.services.tv_service import TVService
from app.schemas.movie import (
    UserRatingCreate, UserRatingResponse, UserWatchlistCreate, UserWatchlistResponse
)

router = APIRouter(prefix="/tv", tags=["tv"])

def handle_exception(e: Exception) -> HTTPException:
    """Handle exceptions and convert to HTTPException"""
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

# TMDB TV Operations
@router.get("/popular")
def get_popular_tv_shows(
    page: int = Query(1, ge=1, description="Page number"),
    db: Session = Depends(get_db)
):
    """Get popular TV shows from TMDB"""
    try:
        tv_service = TVService(db)
        result = tv_service.get_popular_tv_shows(page)
        
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
def get_tv_show_details(
    tmdb_id: int,
    db: Session = Depends(get_db)
):
    """Get TV show details from TMDB"""
    try:
        tv_service = TVService(db)
        result = tv_service.get_tv_show_details(tmdb_id)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="TV show not found"
            )
    except Exception as e:
        raise handle_exception(e)

@router.get("/search")
def search_tv_shows(
    query: str = Query(..., description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    db: Session = Depends(get_db)
):
    """Search TV shows on TMDB"""
    try:
        tv_service = TVService(db)
        result = tv_service.search_tv_shows(query, page)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
    except Exception as e:
        raise handle_exception(e)

# User Rating Operations for TV Shows
@router.post("/rate", response_model=UserRatingResponse)
def rate_tv_show(
    rating_data: UserRatingCreate,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Rate a TV show"""
    try:
        tv_service = TVService(db)
        rating = tv_service.rate_tv_show(current_user_id, rating_data)
        return rating
    except Exception as e:
        raise handle_exception(e)

@router.get("/my/ratings", response_model=List[UserRatingResponse])
def get_my_tv_ratings(
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's TV show ratings"""
    try:
        tv_service = TVService(db)
        ratings = tv_service.get_user_tv_ratings(current_user_id)
        return ratings
    except Exception as e:
        raise handle_exception(e)

# User Watchlist Operations for TV Shows
@router.post("/watchlist", response_model=UserWatchlistResponse)
def add_tv_show_to_watchlist(
    watchlist_data: UserWatchlistCreate,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add TV show to user's watchlist"""
    try:
        tv_service = TVService(db)
        watchlist_item = tv_service.add_tv_show_to_watchlist(current_user_id, watchlist_data)
        return watchlist_item
    except Exception as e:
        raise handle_exception(e)

@router.get("/my/watchlist", response_model=List[UserWatchlistResponse])
def get_my_tv_watchlist(
    status: Optional[str] = Query(None, description="Filter by status ('to_watch', 'watching', 'completed')"),
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's TV show watchlist"""
    try:
        tv_service = TVService(db)
        watchlist = tv_service.get_user_tv_watchlist(current_user_id, status)
        return watchlist
    except Exception as e:
        raise handle_exception(e)

@router.put("/watchlist/{tmdb_id}")
def update_tv_watchlist_status(
    tmdb_id: int,
    status: str = Query(..., description="New status ('to_watch', 'watching', 'completed')"),
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update TV show watchlist item status"""
    try:
        tv_service = TVService(db)
        item = tv_service.update_tv_watchlist_status(current_user_id, tmdb_id, status)
        
        if item:
            return item
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="TV show watchlist item not found"
            )
    except Exception as e:
        raise handle_exception(e) 