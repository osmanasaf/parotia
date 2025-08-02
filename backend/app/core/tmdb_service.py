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
    def create_service(api_key: str = None, language: str = "en-US", locale: str = "US"):
        """Create a combined service with movie and TV methods"""
        from app.core.config import get_settings
        
        if api_key is None:
            settings = get_settings()
            api_key = settings.TMDB_API_KEY
        
        config = TMDBConfig(api_key=api_key, language=language, locale=locale)
        client = TMDBClient(config)
        
        class CombinedTMDBService:
            def __init__(self, client):
                self.client = client
                self.movie_service = MovieService(client)
                self.tv_service = TVService(client)
            
            def get_movie_details(self, movie_id: int):
                """Get detailed movie information"""
                try:
                    return self.movie_service.get_movie_details(movie_id)
                except Exception as e:
                    logger.error(f"Error getting movie details: {str(e)}")
                    return None
            
            def get_tv_details(self, tv_id: int):
                """Get detailed TV show information"""
                try:
                    return self.tv_service.get_tv_details(tv_id)
                except Exception as e:
                    logger.error(f"Error getting TV details: {str(e)}")
                    return None
        
        return CombinedTMDBService(client)
    
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