from typing import Dict
from ..interfaces import MovieServiceInterface, TMDBResponse, TMDBClientInterface

class MovieService(MovieServiceInterface):
    """Service class for movie-related operations"""
    
    def __init__(self, client: TMDBClientInterface):
        self.client = client
    
    def get_popular_movies(self, page: int = 1) -> TMDBResponse:
        """Get popular movies"""
        params = {"page": page}
        return self.client.make_request("movie/popular", params)
    
    def get_movie_details(self, movie_id: int) -> TMDBResponse:
        """Get movie details by ID"""
        return self.client.make_request(f"movie/{movie_id}")
    
    def search_movies(self, query: str, page: int = 1) -> TMDBResponse:
        """Search movies by query"""
        params = {"query": query, "page": page}
        return self.client.make_request("search/movie", params)
    
    def get_movie_credits(self, movie_id: int) -> TMDBResponse:
        """Get movie credits by ID"""
        return self.client.make_request(f"movie/{movie_id}/credits")
    
    def get_movie_recommendations(self, movie_id: int, page: int = 1) -> TMDBResponse:
        """Get movie recommendations by ID"""
        params = {"page": page}
        return self.client.make_request(f"movie/{movie_id}/recommendations", params)
    
    def get_movie_watch_providers(self, movie_id: int) -> TMDBResponse:
        """Get movie watch providers by ID"""
        return self.client.make_request(f"movie/{movie_id}/watch/providers")
    
    def get_movie_genres(self) -> TMDBResponse:
        """Get movie genres list from TMDB"""
        return self.client.make_request("genre/movie/list")
    
    def discover_movies(self, page: int = 1, **filters) -> TMDBResponse:
        """Discover movies with filters (genre, year, etc.)"""
        params = {"page": page}
        params.update(filters)
        return self.client.make_request("discover/movie", params) 