from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class TMDBConfig:
    """Configuration class for TMDB API"""
    api_key: str
    base_url: str = "https://api.themoviedb.org/3"
    language: str = "en-US"
    locale: str = "US"  # Default locale for watch providers
    timeout: int = 30

class TMDBResponse:
    """Response wrapper for TMDB API calls"""
    def __init__(self, data: Dict, status_code: int, success: bool):
        self.data = data
        self.status_code = status_code
        self.success = success

class TMDBError(Exception):
    """Custom exception for TMDB API errors"""
    def __init__(self, message: str, status_code: int = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class TMDBClientInterface(ABC):
    """Abstract interface for TMDB client"""
    
    @abstractmethod
    def make_request(self, endpoint: str, params: Dict = None) -> TMDBResponse:
        pass

class MovieServiceInterface(ABC):
    """Abstract interface for movie service"""
    
    @abstractmethod
    def get_popular_movies(self, page: int = 1) -> TMDBResponse:
        pass
    
    @abstractmethod
    def get_movie_details(self, movie_id: int) -> TMDBResponse:
        pass
    
    @abstractmethod
    def search_movies(self, query: str, page: int = 1) -> TMDBResponse:
        pass
    
    @abstractmethod
    def get_movie_credits(self, movie_id: int) -> TMDBResponse:
        pass
    
    @abstractmethod
    def get_movie_recommendations(self, movie_id: int, page: int = 1) -> TMDBResponse:
        pass
    
    @abstractmethod
    def get_movie_watch_providers(self, movie_id: int) -> TMDBResponse:
        pass

class TVServiceInterface(ABC):
    """Abstract interface for TV service"""
    
    @abstractmethod
    def get_popular_tv_shows(self, page: int = 1) -> TMDBResponse:
        pass
    
    @abstractmethod
    def get_tv_details(self, tv_id: int) -> TMDBResponse:
        pass
    
    @abstractmethod
    def search_tv_shows(self, query: str, page: int = 1) -> TMDBResponse:
        pass
    
    @abstractmethod
    def get_tv_credits(self, tv_id: int) -> TMDBResponse:
        pass
    
    @abstractmethod
    def get_tv_recommendations(self, tv_id: int, page: int = 1) -> TMDBResponse:
        pass
    
    @abstractmethod
    def get_tv_watch_providers(self, tv_id: int) -> TMDBResponse:
        pass

class PersonServiceInterface(ABC):
    """Abstract interface for person service"""
    
    @abstractmethod
    def get_person_details(self, person_id: int) -> TMDBResponse:
        pass
    
    @abstractmethod
    def get_person_movie_credits(self, person_id: int) -> TMDBResponse:
        pass
    
    @abstractmethod
    def get_person_tv_credits(self, person_id: int) -> TMDBResponse:
        pass
    
    @abstractmethod
    def search_persons(self, query: str, page: int = 1) -> TMDBResponse:
        pass 