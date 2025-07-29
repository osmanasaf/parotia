from typing import Dict
from ..interfaces import PersonServiceInterface, TMDBResponse, TMDBClientInterface

class PersonService(PersonServiceInterface):
    """Service class for person-related operations"""
    
    def __init__(self, client: TMDBClientInterface):
        self.client = client
    
    def get_person_details(self, person_id: int) -> TMDBResponse:
        """Get person details by ID"""
        return self.client.make_request(f"person/{person_id}")
    
    def get_person_movie_credits(self, person_id: int) -> TMDBResponse:
        """Get person's movie credits by ID"""
        return self.client.make_request(f"person/{person_id}/movie_credits")
    
    def get_person_tv_credits(self, person_id: int) -> TMDBResponse:
        """Get person's TV credits by ID"""
        return self.client.make_request(f"person/{person_id}/tv_credits")
    
    def search_persons(self, query: str, page: int = 1) -> TMDBResponse:
        """Search persons by query"""
        params = {"query": query, "page": page}
        return self.client.make_request("search/person", params) 