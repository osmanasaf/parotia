import requests
import logging
from typing import Dict
from .interfaces import TMDBClientInterface, TMDBResponse, TMDBConfig, TMDBError

logger = logging.getLogger(__name__)

class TMDBClient(TMDBClientInterface):
    """Concrete implementation of TMDB client"""
    
    def __init__(self, config: TMDBConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "accept": "application/json"
        })
    
    def make_request(self, endpoint: str, params: Dict = None) -> TMDBResponse:
        """Make HTTP request to TMDB API"""
        try:
            url = f"{self.config.base_url}/{endpoint.lstrip('/')}"
            params = params or {}
            
            # Add API key to params
            params['api_key'] = self.config.api_key
            
            if self.config.language:
                params['language'] = self.config.language
            
            # Add locale for watch provider endpoints
            if 'watch/providers' in endpoint and self.config.locale:
                params['watch_region'] = self.config.locale
            
            logger.info(f"Making request to: {url}")
            response = self.session.get(url, params=params, timeout=self.config.timeout)
            
            if response.status_code == 200:
                return TMDBResponse(response.json(), response.status_code, True)
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return TMDBResponse({}, response.status_code, False)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception: {str(e)}")
            raise TMDBError(f"Request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise TMDBError(f"Unexpected error: {str(e)}") 