from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Set
from app.db import get_db
from app.core.auth import get_current_user
from app.core.exceptions import BaseAppException
from app.services.movie_service import MovieService
from app.services.tv_service import TVService
from app.core.tmdb_service import TMDBServiceFactory
from app.core.enums import GenreHelper, MovieGenre, TVGenre
from pydantic import BaseModel

router = APIRouter(prefix="/content", tags=["content"])

# Common constants
DEFAULT_DISCOVER_SORT = "popularity.desc"

class ContentItem(BaseModel):
    """Unified content item model for movies and TV shows"""
    tmdb_id: int
    title: str
    original_title: str
    year: Optional[str]
    content_type: str  # "movie" or "tv"
    vote_average: float
    poster_path: Optional[str]
    backdrop_path: Optional[str]
    overview: str
    genre_ids: List[int]
    popularity: float

class ContentSearchResponse(BaseModel):
    """Unified search response"""
    success: bool
    data: List[ContentItem]
    total_results: int
    total_pages: int
    page: int
    query: Optional[str] = None

class GenreListResponse(BaseModel):
    """Genre list response"""
    success: bool
    data: Dict[str, Any]
    content_type: str

class GenreSection(BaseModel):
    genre_id: int
    genre_name: str
    items: List[ContentItem]

class GenreWithContentResponse(BaseModel):
    success: bool
    data: Dict[str, Any]
    content_type: str

def handle_exception(e: Exception) -> HTTPException:
    """Handle exceptions and return appropriate HTTP error"""
    if isinstance(e, BaseAppException):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    else:
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

def format_content_item(item: Dict[str, Any], content_type: str) -> ContentItem:
    """Format content item from TMDB response"""
    # Extract year from release_date or first_air_date
    release_date = item.get("release_date") or item.get("first_air_date")
    year = release_date.split("-")[0] if release_date else None
    
    return ContentItem(
        tmdb_id=item.get("id"),
        title=item.get("title") or item.get("name"),
        original_title=item.get("original_title") or item.get("original_name"),
        year=year,
        content_type=content_type,
        vote_average=item.get("vote_average", 0.0),
        poster_path=item.get("poster_path"),
        backdrop_path=item.get("backdrop_path"),
        overview=item.get("overview", ""),
        genre_ids=item.get("genre_ids", []),
        popularity=item.get("popularity", 0.0)
    )

@router.get("/genres", response_model=GenreListResponse)
def get_genres(
    content_type: str = Query("movie", description="İçerik türü: 'movie', 'tv', veya 'all'")
):
    """Get genre list for movies and/or TV shows"""
    try:
        if content_type == "movie":
            genres = GenreHelper.get_all_movie_genres()
            popular_genres = [g.value for g in GenreHelper.get_popular_movie_genres()]
        elif content_type == "tv":
            genres = GenreHelper.get_all_tv_genres()
            popular_genres = [g.value for g in GenreHelper.get_popular_tv_genres()]
        else:  # all
            movie_genres = GenreHelper.get_all_movie_genres()
            tv_genres = GenreHelper.get_all_tv_genres()
            genres = {**movie_genres, **tv_genres}
            popular_genres = (
                [g.value for g in GenreHelper.get_popular_movie_genres()] +
                [g.value for g in GenreHelper.get_popular_tv_genres()]
            )
        
        return GenreListResponse(
            success=True,
            data={
                "genres": genres,
                "popular_genres": popular_genres
            },
            content_type=content_type
        )
        
    except Exception as e:
        raise handle_exception(e)

@router.get("/genres-with-content", response_model=GenreWithContentResponse)
def get_genres_with_content(
    content_type: str = Query("movie", description="İçerik türü: 'movie' veya 'tv'"),
    db: Session = Depends(get_db)
):
    """Popüler genre'ler için her birinden 15'er içerik ile birlikte genre listesini döndür."""
    try:
        # Genre listeleri ve popüler genre ID'lerini al
        if content_type == "movie":
            genres = GenreHelper.get_all_movie_genres()
            popular_genre_ids = [g.value for g in GenreHelper.get_popular_movie_genres()]
        elif content_type == "tv":
            genres = GenreHelper.get_all_tv_genres()
            popular_genre_ids = [g.value for g in GenreHelper.get_popular_tv_genres()]
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid content_type. Must be 'movie' or 'tv'"
            )

        # Servisleri başlat
        movie_service = MovieService(db)
        tv_service = TVService(db)

        sections: List[GenreSection] = []
        used_tmdb_ids: Set[int] = set()

        for genre_id in popular_genre_ids:
            # Her bölüm için 15 benzersiz içerik hedefi
            items: List[ContentItem] = []
            page = 1
            max_pages = 3  # Çok fazla çağrıdan kaçınmak için sınır

            while len(items) < 15 and page <= max_pages:
                if content_type == "movie":
                    response = movie_service.tmdb_movie_service.discover_movies(
                        page, sort_by=DEFAULT_DISCOVER_SORT, with_genres=genre_id
                    )
                else:
                    response = tv_service.tmdb_tv_service.discover_tv_shows(
                        page, sort_by=DEFAULT_DISCOVER_SORT, with_genres=genre_id
                    )

                if not response.success:
                    break

                raw_items = response.data.get("results", [])
                if not raw_items:
                    break

                for raw in raw_items:
                    if len(items) >= 15:
                        break
                    try:
                        raw_id = raw.get("id")
                        if raw_id is None or raw_id in used_tmdb_ids:
                            continue
                        formatted = format_content_item(raw, content_type)
                        items.append(formatted)
                        used_tmdb_ids.add(formatted.tmdb_id)
                    except Exception:
                        continue

                page += 1

            sections.append(
                GenreSection(
                    genre_id=genre_id,
                    genre_name=(
                        GenreHelper.get_movie_genre_name(genre_id)
                        if content_type == "movie"
                        else GenreHelper.get_tv_genre_name(genre_id)
                    ),
                    items=items
                )
            )

        # Ön yüz için daha kullanışlı, camelCase alan adlarıyla map'le
        def map_item_to_frontend(i: ContentItem) -> Dict[str, Any]:
            return {
                "id": i.tmdb_id,
                "title": i.title,
                "originalTitle": i.original_title,
                "year": i.year,
                "contentType": i.content_type,
                "rating": i.vote_average,
                "posterPath": i.poster_path,
                "backdropPath": i.backdrop_path,
                "overview": i.overview,
                "genreIds": i.genre_ids,
                "popularity": i.popularity,
            }

        sections_serialized: List[Dict[str, Any]] = []
        for section in sections:
            sections_serialized.append(
                {
                    "id": section.genre_id,
                    "name": section.genre_name,
                    "items": [map_item_to_frontend(i) for i in section.items],
                }
            )

        genres_list = [
            {"id": gid, "name": gname} for gid, gname in genres.items()
        ]

        return GenreWithContentResponse(
            success=True,
            data={
                "genres": genres_list,
                "popularGenres": popular_genre_ids,
                "sections": sections_serialized,
            },
            content_type=content_type
        )
    except Exception as e:
        raise handle_exception(e)

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

@router.get("/discover", response_model=ContentSearchResponse)
def discover_content(
    content_type: str = Query("movie", description="İçerik türü: 'movie' veya 'tv'"),
    page: int = Query(1, ge=1, description="Sayfa numarası"),
    genre_id: Optional[int] = Query(None, description="Genre ID"),
    year: Optional[int] = Query(None, description="Yıl"),
    sort_by: str = Query("popularity.desc", description="Sıralama: 'popularity.desc', 'vote_average.desc', 'release_date.desc'"),
    db: Session = Depends(get_db)
):
    """Discover movies or TV shows with filters"""
    try:
        # Initialize services
        movie_service = MovieService(db)
        tv_service = TVService(db)
        
        # Build filters
        filters = {"sort_by": sort_by}
        if genre_id:
            filters["with_genres"] = genre_id
        if year:
            filters["year"] = year
        
        # Get content based on type
        if content_type == "movie":
            response = movie_service.tmdb_movie_service.discover_movies(page, **filters)
        else:
            response = tv_service.tmdb_tv_service.discover_tv_shows(page, **filters)
        
        if response.success:
            results = []
            for item in response.data.get("results", []):
                try:
                    formatted_item = format_content_item(item, content_type)
                    results.append(formatted_item)
                except Exception as e:
                    print(f"Error formatting {content_type} item: {e}")
                    continue
            
            return ContentSearchResponse(
                success=True,
                data=results,
                total_results=response.data.get("total_results", 0),
                total_pages=response.data.get("total_pages", 0),
                page=page
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to discover content"
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