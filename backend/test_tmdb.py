import os
import sys
from dotenv import load_dotenv

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.tmdb_service import TMDBServiceFactory

def test_tmdb_api():
    """Test TMDB API functionality"""
    
    # Load environment variables
    load_dotenv()
    
    # Get API key
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key or api_key == "your_tmdb_api_key_here":
        print("❌ TMDB_API_KEY not configured in .env file")
        print("Please get your API key from: https://www.themoviedb.org/settings/api")
        return
    
    print("🔑 Testing TMDB API...")
    print(f"API Key: {api_key[:10]}...")
    
    try:
        # Test Movie Service
        print("\n🎬 Testing Movie Service...")
        movie_service = TMDBServiceFactory.create_movie_service(api_key)
        
        # Test popular movies
        print("📺 Getting popular movies...")
        response = movie_service.get_popular_movies(1)
        if response.success:
            print(f"✅ Popular movies fetched successfully!")
            print(f"   Total results: {response.data.get('total_results', 'N/A')}")
            print(f"   Total pages: {response.data.get('total_pages', 'N/A')}")
            if response.data.get('results'):
                first_movie = response.data['results'][0]
                print(f"   First movie: {first_movie.get('title', 'N/A')}")
        else:
            print(f"❌ Failed to fetch popular movies: {response.status_code}")
        
        # Test movie search
        print("\n🔍 Testing movie search...")
        response = movie_service.search_movies("Inception", 1)
        if response.success:
            print(f"✅ Movie search successful!")
            if response.data.get('results'):
                first_result = response.data['results'][0]
                print(f"   First result: {first_result.get('title', 'N/A')}")
        else:
            print(f"❌ Failed to search movies: {response.status_code}")
        
        # Test TV Service
        print("\n📺 Testing TV Service...")
        tv_service = TMDBServiceFactory.create_tv_service(api_key)
        
        # Test popular TV shows
        print("📺 Getting popular TV shows...")
        response = tv_service.get_popular_tv_shows(1)
        if response.success:
            print(f"✅ Popular TV shows fetched successfully!")
            print(f"   Total results: {response.data.get('total_results', 'N/A')}")
            if response.data.get('results'):
                first_show = response.data['results'][0]
                print(f"   First show: {first_show.get('name', 'N/A')}")
        else:
            print(f"❌ Failed to fetch popular TV shows: {response.status_code}")
        
        print("\n🎉 All tests completed!")
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")

if __name__ == "__main__":
    test_tmdb_api() 