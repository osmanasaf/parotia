from fastapi import APIRouter, HTTPException, Depends, Query, Path
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import os
from pydantic import BaseModel

from app.core.tmdb_service import TMDBServiceFactory
from app.core.interfaces import TMDBError
from app.models.movie import Movie
from app.db import SessionLocal

# Pydantic models for request/response
class MovieResponse(BaseModel):
    id: int
    title: str
    overview: Optional[str]
    release_date: Optional[str]
    poster_path: Optional[str]
    vote_average: Optional[float]
    vote_count: Optional[int]

class SearchResponse(BaseModel):
    page: int
    results: List[MovieResponse]
    total_pages: int
    total_results: int

class CreditsResponse(BaseModel):
    id: int
    cast: List[Dict]
    crew: List[Dict]

class WatchProvidersResponse(BaseModel):
    id: int
    results: Dict

# Dependency injection
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_movie_service():
    """Dependency to get movie service instance"""
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="TMDB API key not configured")
    
    return TMDBServiceFactory.create_movie_service(api_key)

router = APIRouter(prefix="/movies", tags=["movies"])

@router.get("/popular", response_model=SearchResponse)
def get_popular_movies(
    page: int = Query(1, ge=1, le=1000, description="Page number"),
    movie_service = Depends(get_movie_service)
):
    """Get popular movies from TMDB"""
    try:
        response = movie_service.get_popular_movies(page)
        if response.success:
            return SearchResponse(**response.data)
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch popular movies")
    except TMDBError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search", response_model=SearchResponse)
def search_movies(
    query: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1, le=1000, description="Page number"),
    movie_service = Depends(get_movie_service)
):
    """Search movies by query"""
    try:
        response = movie_service.search_movies(query, page)
        if response.success:
            return SearchResponse(**response.data)
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to search movies")
    except TMDBError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{movie_id}", response_model=MovieResponse)
def get_movie_details(
    movie_id: int = Path(..., gt=0, description="Movie ID"),
    movie_service = Depends(get_movie_service)
):
    """Get movie details by ID"""
    try:
        response = movie_service.get_movie_details(movie_id)
        if response.success:
            return MovieResponse(**response.data)
        else:
            raise HTTPException(status_code=response.status_code, detail="Movie not found")
    except TMDBError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{movie_id}/credits", response_model=CreditsResponse)
def get_movie_credits(
    movie_id: int = Path(..., gt=0, description="Movie ID"),
    movie_service = Depends(get_movie_service)
):
    """Get movie credits by ID"""
    try:
        response = movie_service.get_movie_credits(movie_id)
        if response.success:
            return CreditsResponse(**response.data)
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch movie credits")
    except TMDBError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{movie_id}/recommendations", response_model=SearchResponse)
def get_movie_recommendations(
    movie_id: int = Path(..., gt=0, description="Movie ID"),
    page: int = Query(1, ge=1, le=1000, description="Page number"),
    movie_service = Depends(get_movie_service)
):
    """Get movie recommendations by ID"""
    try:
        response = movie_service.get_movie_recommendations(movie_id, page)
        if response.success:
            return SearchResponse(**response.data)
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch recommendations")
    except TMDBError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{movie_id}/watch-providers", response_model=WatchProvidersResponse)
def get_movie_watch_providers(
    movie_id: int = Path(..., gt=0, description="Movie ID"),
    locale: str = Query("US", description="Country code (e.g., TR, US, GB)"),
    movie_service = Depends(get_movie_service)
):
    """Get movie watch providers by ID"""
    try:
        # Create a new service instance with the specified locale
        api_key = os.getenv("TMDB_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="TMDB API key not configured")
        
        service_with_locale = TMDBServiceFactory.create_movie_service(api_key, locale=locale)
        response = service_with_locale.get_movie_watch_providers(movie_id)
        
        if response.success:
            return WatchProvidersResponse(**response.data)
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch watch providers")
    except TMDBError as e:
        raise HTTPException(status_code=500, detail=str(e)) 