from typing import Dict
from ..interfaces import TVServiceInterface, TMDBResponse, TMDBClientInterface
from ..cache import CacheService

CACHE_TTL_24H = 24 * 60 * 60

class TVService(TVServiceInterface):
    """Service class for TV show-related operations"""
    
    def __init__(self, client: TMDBClientInterface):
        self.client = client
        self.cache = CacheService()
    
    def get_popular_tv_shows(self, page: int = 1) -> TMDBResponse:
        """Get popular TV shows"""
        cache_key = f"tmdb:tv:popular:p{page}"
        cached = self.cache.get_json(cache_key)
        if cached is not None:
            return TMDBResponse(cached, 200, True)
        params = {"page": page}
        resp = self.client.make_request("tv/popular", params)
        if resp.success:
            self.cache.set_json(cache_key, resp.data, CACHE_TTL_24H)
        return resp
    
    def get_tv_show_details(self, tv_id: int) -> TMDBResponse:
        """Get TV show details by ID"""
        cache_key = f"tmdb:tv:{tv_id}:details"
        cached = self.cache.get_json(cache_key)
        if cached is not None:
            return TMDBResponse(cached, 200, True)
        resp = self.client.make_request(f"tv/{tv_id}")
        if resp.success:
            self.cache.set_json(cache_key, resp.data, CACHE_TTL_24H)
        return resp
    
    def get_tv_details(self, tv_id: int) -> TMDBResponse:
        """Get TV show details by ID (alias for get_tv_show_details)"""
        return self.get_tv_show_details(tv_id)
    
    def search_tv_shows(self, query: str, page: int = 1) -> TMDBResponse:
        """Search TV shows by query"""
        params = {"query": query, "page": page}
        return self.client.make_request("search/tv", params)
    
    def get_tv_credits(self, tv_id: int) -> TMDBResponse:
        """Get TV show credits by ID"""
        cache_key = f"tmdb:tv:{tv_id}:credits"
        cached = self.cache.get_json(cache_key)
        if cached is not None:
            return TMDBResponse(cached, 200, True)
        resp = self.client.make_request(f"tv/{tv_id}/credits")
        if resp.success:
            self.cache.set_json(cache_key, resp.data, CACHE_TTL_24H)
        return resp
    
    def get_tv_show_credits(self, tv_id: int) -> TMDBResponse:
        """Get TV show credits by ID (alias for get_tv_credits)"""
        return self.get_tv_credits(tv_id)
    
    def get_tv_recommendations(self, tv_id: int, page: int = 1) -> TMDBResponse:
        """Get TV show recommendations by ID"""
        params = {"page": page}
        return self.client.make_request(f"tv/{tv_id}/recommendations", params)
    
    def get_tv_watch_providers(self, tv_id: int) -> TMDBResponse:
        """Get TV show watch providers by ID"""
        cache_key = f"tmdb:tv:{tv_id}:watch_providers"
        cached = self.cache.get_json(cache_key)
        if cached is not None:
            return TMDBResponse(cached, 200, True)
        resp = self.client.make_request(f"tv/{tv_id}/watch/providers")
        if resp.success:
            self.cache.set_json(cache_key, resp.data, CACHE_TTL_24H)
        return resp
    
    def get_tv_genres(self) -> TMDBResponse:
        """Get TV genres list from TMDB"""
        cache_key = f"tmdb:tv:genres"
        cached = self.cache.get_json(cache_key)
        if cached is not None:
            return TMDBResponse(cached, 200, True)
        resp = self.client.make_request("genre/tv/list")
        if resp.success:
            self.cache.set_json(cache_key, resp.data, CACHE_TTL_24H)
        return resp
    
    def discover_tv_shows(self, page: int = 1, **filters) -> TMDBResponse:
        """Discover TV shows with filters (genre, year, etc.)"""
        params = {"page": page}
        params.update(filters)
        parts = [f"{k}={v}" for k, v in sorted(filters.items())]
        key_suffix = ":".join(parts) if parts else "none"
        cache_key = f"tmdb:tv:discover:{key_suffix}:p{page}"
        cached = self.cache.get_json(cache_key)
        if cached is not None:
            return TMDBResponse(cached, 200, True)
        resp = self.client.make_request("discover/tv", params)
        if resp.success:
            self.cache.set_json(cache_key, resp.data, CACHE_TTL_24H)
        return resp