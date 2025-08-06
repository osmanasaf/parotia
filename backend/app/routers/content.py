from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.db import get_db
from app.core.auth import get_current_user
from app.core.exceptions import BaseAppException
from app.services.movie_service import MovieService
from app.services.tv_service import TVService
from app.core.tmdb_service import TMDBServiceFactory
from pydantic import BaseModel

router = APIRouter(prefix="/content", tags=["content"])

class ContentItem(BaseModel):
    """Unified content item model for movies and TV shows"""
    tmdb_id: int
    title: str
    original_title: str
    year: Optional[str]
    content_type: str  # "movie" or "tv"
    vote_average: float
    poster_path: Optional[str]
    overview: str
    genre_ids: List[int]
    popularity: float

class ContentSearchResponse(BaseModel):
    """Response model for content search"""
    success: bool
    data: List[ContentItem]
    total_results: int
    total_pages: int
    page: int
    query: str

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

def format_content_item(item: Dict[str, Any], content_type: str) -> ContentItem:
    """Format TMDB response item to unified content item"""
    # Extract year from release_date or first_air_date
    year = None
    if content_type == "movie" and item.get("release_date"):
        year = item["release_date"][:4]
    elif content_type == "tv" and item.get("first_air_date"):
        year = item["first_air_date"][:4]
    
    # Handle title/name field differences between movies and TV shows
    title = item.get("title") if content_type == "movie" else item.get("name", "")
    original_title = item.get("original_title") if content_type == "movie" else item.get("original_name", "")
    
    return ContentItem(
        tmdb_id=item["id"],
        title=title,
        original_title=original_title,
        year=year,
        content_type=content_type,
        vote_average=item.get("vote_average", 0.0),
        poster_path=item.get("poster_path"),
        overview=item.get("overview", ""),
        genre_ids=item.get("genre_ids", []),
        popularity=item.get("popularity", 0.0)
    )

@router.get("/search", response_model=ContentSearchResponse)
def search_content(
    query: str = Query(..., description="Search query for movies and TV shows"),
    page: int = Query(1, ge=1, description="Page number"),
    content_type: Optional[str] = Query(None, description="Filter by content type: 'movie', 'tv', or 'all'"),
    db: Session = Depends(get_db)
):
    """
    Search for movies and TV shows with unified response format.
    Returns simplified content items with essential information.
    """
    try:
        # Initialize services
        movie_service = MovieService(db)
        tv_service = TVService(db)
        
        all_results = []
        total_results = 0
        total_pages = 0
        
        # Search movies if requested
        if content_type is None or content_type in ["movie", "all"]:
            movie_result = movie_service.search_movies(query, page)
            if movie_result["success"]:
                movie_data = movie_result["data"]
                print(f"Movie Results: {len(movie_data.get('results', []))} items found")
                movie_items = []
                for item in movie_data.get("results", []):
                    try:
                        formatted_item = format_content_item(item, "movie")
                        movie_items.append(formatted_item)
                        print(f"Formatted Movie item: {formatted_item.title} ({formatted_item.content_type})")
                    except Exception as e:
                        print(f"Error formatting Movie item: {e}")
                        print(f"Raw item: {item}")
                all_results.extend(movie_items)
                total_results += movie_data.get("total_results", 0)
                total_pages = max(total_pages, movie_data.get("total_pages", 0))
        
        # Search TV shows if requested
        if content_type is None or content_type in ["tv", "all"]:
            tv_result = tv_service.search_tv_shows(query, page)
            if tv_result["success"]:
                tv_data = tv_result["data"]
                print(f"TV Results: {len(tv_data.get('results', []))} items found")
                tv_items = []
                for item in tv_data.get("results", []):
                    try:
                        formatted_item = format_content_item(item, "tv")
                        tv_items.append(formatted_item)
                        print(f"Formatted TV item: {formatted_item.title} ({formatted_item.content_type})")
                    except Exception as e:
                        print(f"Error formatting TV item: {e}")
                        print(f"Raw item: {item}")
                all_results.extend(tv_items)
                total_results += tv_data.get("total_results", 0)
                total_pages = max(total_pages, tv_data.get("total_pages", 0))
        
        # Sort by popularity (descending)
        all_results.sort(key=lambda x: x.popularity, reverse=True)
        
        return ContentSearchResponse(
            success=True,
            data=all_results,
            total_results=total_results,
            total_pages=total_pages,
            page=page,
            query=query
        )
        
    except Exception as e:
        raise handle_exception(e)

@router.get("/popular", response_model=ContentSearchResponse)
def get_popular_content(
    page: int = Query(1, ge=1, description="Page number"),
    content_type: Optional[str] = Query(None, description="Filter by content type: 'movie', 'tv', or 'all'"),
    db: Session = Depends(get_db)
):
    """
    Get popular movies and TV shows with unified response format.
    """
    try:
        # Initialize services
        movie_service = MovieService(db)
        tv_service = TVService(db)
        
        all_results = []
        total_results = 0
        total_pages = 0
        
        # Get popular movies if requested
        if content_type is None or content_type in ["movie", "all"]:
            movie_result = movie_service.get_popular_movies(page)
            if movie_result["success"]:
                movie_data = movie_result["data"]
                movie_items = [format_content_item(item, "movie") for item in movie_data.get("results", [])]
                all_results.extend(movie_items)
                total_results += movie_data.get("total_results", 0)
                total_pages = max(total_pages, movie_data.get("total_pages", 0))
        
        # Get popular TV shows if requested
        if content_type is None or content_type in ["tv", "all"]:
            tv_result = tv_service.get_popular_tv_shows(page)
            if tv_result["success"]:
                tv_data = tv_result["data"]
                tv_items = [format_content_item(item, "tv") for item in tv_data.get("results", [])]
                all_results.extend(tv_items)
                total_results += tv_data.get("total_results", 0)
                total_pages = max(total_pages, tv_data.get("total_pages", 0))
        
        # Sort by popularity (descending)
        all_results.sort(key=lambda x: x.popularity, reverse=True)
        
        return ContentSearchResponse(
            success=True,
            data=all_results,
            total_results=total_results,
            total_pages=total_pages,
            page=page,
            query="popular"
        )
        
    except Exception as e:
        raise handle_exception(e)

@router.get("/{content_type}/{tmdb_id}")
def get_content_details(
    content_type: str,
    tmdb_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information for a specific movie or TV show.
    content_type: 'movie' or 'tv'
    """
    try:
        if content_type == "movie":
            service = MovieService(db)
            result = service.get_movie_details(tmdb_id)
        elif content_type == "tv":
            service = TVService(db)
            result = service.get_tv_show_details(tmdb_id)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid content_type. Must be 'movie' or 'tv'"
            )
        
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{content_type.title()} not found"
            )
    except Exception as e:
        raise handle_exception(e) 