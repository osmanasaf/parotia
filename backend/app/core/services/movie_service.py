from typing import Dict
from ..interfaces import MovieServiceInterface, TMDBResponse, TMDBClientInterface
from ..cache import CacheService

CACHE_TTL_24H = 24 * 60 * 60

class MovieService(MovieServiceInterface):
    """Service class for movie-related operations"""
    
    def __init__(self, client: TMDBClientInterface):
        self.client = client
        self.cache = CacheService()
    
    def get_popular_movies(self, page: int = 1) -> TMDBResponse:
        """Get popular movies"""
        cache_key = f"tmdb:movie:popular:p{page}"
        cached = self.cache.get_json(cache_key)
        if cached is not None:
            return TMDBResponse(cached, 200, True)
        params = {"page": page}
        resp = self.client.make_request("movie/popular", params)
        if resp.success:
            self.cache.set_json(cache_key, resp.data, CACHE_TTL_24H)
        return resp
    
    def get_movie_details(self, movie_id: int) -> TMDBResponse:
        """Get movie details by ID"""
        cache_key = f"tmdb:movie:{movie_id}:details"
        cached = self.cache.get_json(cache_key)
        if cached is not None:
            return TMDBResponse(cached, 200, True)
        resp = self.client.make_request(f"movie/{movie_id}")
        if resp.success:
            self.cache.set_json(cache_key, resp.data, CACHE_TTL_24H)
        return resp
    
    def search_movies(self, query: str, page: int = 1) -> TMDBResponse:
        """Search movies by query"""
        params = {"query": query, "page": page}
        return self.client.make_request("search/movie", params)
    
    def get_movie_credits(self, movie_id: int) -> TMDBResponse:
        """Get movie credits by ID"""
        cache_key = f"tmdb:movie:{movie_id}:credits"
        cached = self.cache.get_json(cache_key)
        if cached is not None:
            return TMDBResponse(cached, 200, True)
        resp = self.client.make_request(f"movie/{movie_id}/credits")
        if resp.success:
            self.cache.set_json(cache_key, resp.data, CACHE_TTL_24H)
        return resp
    
    def get_movie_recommendations(self, movie_id: int, page: int = 1) -> TMDBResponse:
        """Get movie recommendations by ID"""
        params = {"page": page}
        return self.client.make_request(f"movie/{movie_id}/recommendations", params)
    
    def get_movie_watch_providers(self, movie_id: int) -> TMDBResponse:
        """Get movie watch providers by ID"""
        cache_key = f"tmdb:movie:{movie_id}:watch_providers"
        cached = self.cache.get_json(cache_key)
        if cached is not None:
            return TMDBResponse(cached, 200, True)
        resp = self.client.make_request(f"movie/{movie_id}/watch/providers")
        if resp.success:
            self.cache.set_json(cache_key, resp.data, CACHE_TTL_24H)
        return resp
    
    def get_movie_genres(self) -> TMDBResponse:
        """Get movie genres list from TMDB"""
        cache_key = f"tmdb:movie:genres"
        cached = self.cache.get_json(cache_key)
        if cached is not None:
            return TMDBResponse(cached, 200, True)
        resp = self.client.make_request("genre/movie/list")
        if resp.success:
            self.cache.set_json(cache_key, resp.data, CACHE_TTL_24H)
        return resp
    
    def discover_movies(self, page: int = 1, **filters) -> TMDBResponse:
        """Discover movies with filters (genre, year, etc.)"""
        params = {"page": page}
        params.update(filters)
        # Basit key: filtreleri alfabetik sırada birleştir
        parts = [f"{k}={v}" for k, v in sorted(filters.items())]
        key_suffix = ":".join(parts) if parts else "none"
        cache_key = f"tmdb:movie:discover:{key_suffix}:p{page}"
        cached = self.cache.get_json(cache_key)
        if cached is not None:
            return TMDBResponse(cached, 200, True)
        resp = self.client.make_request("discover/movie", params)
        if resp.success:
            self.cache.set_json(cache_key, resp.data, CACHE_TTL_24H)
        return resp