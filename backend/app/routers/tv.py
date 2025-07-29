from fastapi import APIRouter, HTTPException, Depends, Query, Path
from typing import List, Dict, Optional
import os
from pydantic import BaseModel

from app.core.tmdb_service import TMDBServiceFactory
from app.core.interfaces import TMDBError

# Pydantic models for request/response
class TVResponse(BaseModel):
    id: int
    name: str
    overview: Optional[str]
    first_air_date: Optional[str]
    poster_path: Optional[str]
    vote_average: Optional[float]
    vote_count: Optional[int]

class TVSearchResponse(BaseModel):
    page: int
    results: List[TVResponse]
    total_pages: int
    total_results: int

class TVCreditsResponse(BaseModel):
    id: int
    cast: List[Dict]
    crew: List[Dict]

class TVWatchProvidersResponse(BaseModel):
    id: int
    results: Dict

# Dependency injection
def get_tv_service():
    """Dependency to get TV service instance"""
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="TMDB API key not configured")
    
    return TMDBServiceFactory.create_tv_service(api_key)

router = APIRouter(prefix="/tv", tags=["tv"])

@router.get("/popular", response_model=TVSearchResponse)
def get_popular_tv_shows(
    page: int = Query(1, ge=1, le=1000, description="Page number"),
    tv_service = Depends(get_tv_service)
):
    """Get popular TV shows from TMDB"""
    try:
        response = tv_service.get_popular_tv_shows(page)
        if response.success:
            return TVSearchResponse(**response.data)
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch popular TV shows")
    except TMDBError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search", response_model=TVSearchResponse)
def search_tv_shows(
    query: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1, le=1000, description="Page number"),
    tv_service = Depends(get_tv_service)
):
    """Search TV shows by query"""
    try:
        response = tv_service.search_tv_shows(query, page)
        if response.success:
            return TVSearchResponse(**response.data)
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to search TV shows")
    except TMDBError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{tv_id}", response_model=TVResponse)
def get_tv_details(
    tv_id: int = Path(..., gt=0, description="TV ID"),
    tv_service = Depends(get_tv_service)
):
    """Get TV show details by ID"""
    try:
        response = tv_service.get_tv_details(tv_id)
        if response.success:
            return TVResponse(**response.data)
        else:
            raise HTTPException(status_code=response.status_code, detail="TV show not found")
    except TMDBError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{tv_id}/credits", response_model=TVCreditsResponse)
def get_tv_credits(
    tv_id: int = Path(..., gt=0, description="TV ID"),
    tv_service = Depends(get_tv_service)
):
    """Get TV show credits by ID"""
    try:
        response = tv_service.get_tv_credits(tv_id)
        if response.success:
            return TVCreditsResponse(**response.data)
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch TV show credits")
    except TMDBError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{tv_id}/recommendations", response_model=TVSearchResponse)
def get_tv_recommendations(
    tv_id: int = Path(..., gt=0, description="TV ID"),
    page: int = Query(1, ge=1, le=1000, description="Page number"),
    tv_service = Depends(get_tv_service)
):
    """Get TV show recommendations by ID"""
    try:
        response = tv_service.get_tv_recommendations(tv_id, page)
        if response.success:
            return TVSearchResponse(**response.data)
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch recommendations")
    except TMDBError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{tv_id}/watch-providers", response_model=TVWatchProvidersResponse)
def get_tv_watch_providers(
    tv_id: int = Path(..., gt=0, description="TV ID"),
    locale: str = Query("US", description="Country code (e.g., TR, US, GB)"),
    tv_service = Depends(get_tv_service)
):
    """Get TV show watch providers by ID"""
    try:
        # Create a new service instance with the specified locale
        api_key = os.getenv("TMDB_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="TMDB API key not configured")
        
        service_with_locale = TMDBServiceFactory.create_tv_service(api_key, locale=locale)
        response = service_with_locale.get_tv_watch_providers(tv_id)
        
        if response.success:
            return TVWatchProvidersResponse(**response.data)
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch watch providers")
    except TMDBError as e:
        raise HTTPException(status_code=500, detail=str(e)) 