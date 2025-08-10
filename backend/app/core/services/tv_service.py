from typing import Dict
from ..interfaces import TVServiceInterface, TMDBResponse, TMDBClientInterface

class TVService(TVServiceInterface):
    """Service class for TV show-related operations"""
    
    def __init__(self, client: TMDBClientInterface):
        self.client = client
    
    def get_popular_tv_shows(self, page: int = 1) -> TMDBResponse:
        """Get popular TV shows"""
        params = {"page": page}
        return self.client.make_request("tv/popular", params)
    
    def get_tv_show_details(self, tv_id: int) -> TMDBResponse:
        """Get TV show details by ID"""
        return self.client.make_request(f"tv/{tv_id}")
    
    def get_tv_details(self, tv_id: int) -> TMDBResponse:
        """Get TV show details by ID (alias for get_tv_show_details)"""
        return self.get_tv_show_details(tv_id)
    
    def search_tv_shows(self, query: str, page: int = 1) -> TMDBResponse:
        """Search TV shows by query"""
        params = {"query": query, "page": page}
        return self.client.make_request("search/tv", params)
    
    def get_tv_credits(self, tv_id: int) -> TMDBResponse:
        """Get TV show credits by ID"""
        return self.client.make_request(f"tv/{tv_id}/credits")
    
    def get_tv_show_credits(self, tv_id: int) -> TMDBResponse:
        """Get TV show credits by ID (alias for get_tv_credits)"""
        return self.get_tv_credits(tv_id)
    
    def get_tv_recommendations(self, tv_id: int, page: int = 1) -> TMDBResponse:
        """Get TV show recommendations by ID"""
        params = {"page": page}
        return self.client.make_request(f"tv/{tv_id}/recommendations", params)
    
    def get_tv_watch_providers(self, tv_id: int) -> TMDBResponse:
        """Get TV show watch providers by ID"""
        return self.client.make_request(f"tv/{tv_id}/watch/providers")
    
    def get_tv_genres(self) -> TMDBResponse:
        """Get TV genres list from TMDB"""
        return self.client.make_request("genre/tv/list")
    
    def discover_tv_shows(self, page: int = 1, **filters) -> TMDBResponse:
        """Discover TV shows with filters (genre, year, etc.)"""
        params = {"page": page}
        params.update(filters)
        return self.client.make_request("discover/tv", params) 