import logging
from .interfaces import TMDBConfig
from .tmdb_client import TMDBClient
from .services import MovieService, TVService, PersonService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TMDBServiceFactory:
    """Factory class for creating TMDB services"""
    
    @staticmethod
    def create_movie_service(api_key: str, language: str = "en-US", locale: str = "US") -> MovieService:
        """Create a new movie service instance"""
        config = TMDBConfig(api_key=api_key, language=language, locale=locale)
        client = TMDBClient(config)
        return MovieService(client)
    
    @staticmethod
    def create_tv_service(api_key: str, language: str = "en-US", locale: str = "US") -> TVService:
        """Create a new TV service instance"""
        config = TMDBConfig(api_key=api_key, language=language, locale=locale)
        client = TMDBClient(config)
        return TVService(client)
    
    @staticmethod
    def create_person_service(api_key: str, language: str = "en-US") -> PersonService:
        """Create a new person service instance"""
        config = TMDBConfig(api_key=api_key, language=language)
        client = TMDBClient(config)
        return PersonService(client)
    
    @staticmethod
    def create_all_services(api_key: str, language: str = "en-US") -> dict:
        """Create all service instances"""
        config = TMDBConfig(api_key=api_key, language=language)
        client = TMDBClient(config)
        
        return {
            'movie_service': MovieService(client),
            'tv_service': TVService(client),
            'person_service': PersonService(client)
        } 