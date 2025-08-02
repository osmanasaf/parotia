#!/usr/bin/env python3
"""
Test script for the embedding system with real cosine similarity calculations
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db import get_db
from app.services.embedding_service import EmbeddingService
from app.services.recommendation_service import RecommendationService
from app.services.emotion_analysis_service import EmotionAnalysisService
from app.core.tmdb_service import TMDBServiceFactory

def test_embedding_generation():
    """Test embedding generation for sample content"""
    print("🧠 Testing Embedding Generation...")
    
    # Initialize services
    db = next(get_db())
    embedding_service = EmbeddingService()
    
    # Sample content for testing
    sample_movies = [
        {
            "tmdb_id": 550,
            "content_type": "movie",
            "title": "Fight Club",
            "overview": "A depressed man meets a soap maker and they form an underground fight club that evolves into something much, much more.",
            "genres": [{"name": "Drama"}, {"name": "Thriller"}],
            "release_date": "1999-10-15",
            "tagline": "How much can you know about yourself if you've never been in a fight?",
            "vote_average": 8.8
        },
        {
            "tmdb_id": 37165,
            "content_type": "movie", 
            "title": "The Truman Show",
            "overview": "An insurance salesman discovers his entire life is actually a reality TV show.",
            "genres": [{"name": "Drama"}, {"name": "Comedy"}],
            "release_date": "1998-06-05",
            "tagline": "On the air. Unaware.",
            "vote_average": 8.1
        },
        {
            "tmdb_id": 13,
            "content_type": "movie",
            "title": "Forrest Gump", 
            "overview": "The presidencies of Kennedy and Johnson, the Vietnam War, the Watergate scandal and other historical events unfold from the perspective of an Alabama man with an IQ of 75.",
            "genres": [{"name": "Drama"}, {"name": "Romance"}],
            "release_date": "1994-07-06",
            "tagline": "The world will never be the same once you've seen it through the eyes of Forrest Gump.",
            "vote_average": 8.8
        }
    ]
    
    # Add sample content to embedding index
    for movie in sample_movies:
        success = embedding_service.add_content_with_details(movie)
        print(f"✅ Added {movie['title']}: {success}")
    
    # Save the index
    embedding_service.save_index()
    print(f"📊 Index stats: {embedding_service.get_index_stats()}")

def test_emotion_analysis():
    """Test emotion analysis for user input"""
    print("\n😊 Testing Emotion Analysis...")
    
    db = next(get_db())
    emotion_service = EmotionAnalysisService(db)
    
    # Test user emotion
    user_text = "Bugün kendimi değersiz hissettiğimi söyledim"
    emotion_analysis = emotion_service.analyze_user_emotion(user_text)
    
    print(f"📝 User text: {user_text}")
    print(f"🎭 Emotion analysis: {emotion_analysis}")

def test_similarity_search():
    """Test similarity search with real embeddings"""
    print("\n🔍 Testing Similarity Search...")
    
    embedding_service = EmbeddingService()
    
    # Test query
    query = "Bugün kendimi değersiz hissettiğimi söyledim"
    results = embedding_service.search_similar_content(
        query_text=query,
        top_k=5,
        content_type="movie"
    )
    
    print(f"🔎 Query: {query}")
    print(f"📋 Found {len(results)} similar movies:")
    
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result['title']} (Score: {result['similarity_score']:.3f})")
        print(f"     Overview: {result['overview'][:100]}...")

def test_user_embedding():
    """Test user embedding from ratings"""
    print("\n👤 Testing User Embedding from Ratings...")
    
    embedding_service = EmbeddingService()
    
    # Sample user ratings (high ratings for Fight Club and Truman Show)
    user_ratings = [
        {"tmdb_id": 550, "rating": 9, "content_type": "movie"},  # Fight Club
        {"tmdb_id": 37165, "rating": 8, "content_type": "movie"}, # Truman Show
        {"tmdb_id": 13, "rating": 7, "content_type": "movie"}     # Forrest Gump
    ]
    
    # Generate user embedding
    user_embedding = embedding_service.get_user_preference_embedding(user_ratings)
    
    if user_embedding is not None:
        print(f"✅ Generated user embedding with shape: {user_embedding.shape}")
        
        # Search for similar content using user embedding
        results = embedding_service.search_similar_content(
            query_text="",
            top_k=3,
            content_type="movie",
            user_embedding=user_embedding
        )
        
        print(f"🎯 User preference recommendations:")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['title']} (Score: {result['similarity_score']:.3f})")
    else:
        print("❌ Could not generate user embedding")

def test_hybrid_recommendations():
    """Test hybrid recommendations combining emotion and history"""
    print("\n🔄 Testing Hybrid Recommendations...")
    
    embedding_service = EmbeddingService()
    
    # Test parameters
    emotion_text = "Bugün kendimi değersiz hissettiğimi söyledim"
    user_ratings = [
        {"tmdb_id": 550, "rating": 9, "content_type": "movie"},  # Fight Club
        {"tmdb_id": 37165, "rating": 8, "content_type": "movie"}, # Truman Show
    ]
    
    # Get hybrid recommendations
    results = embedding_service.get_hybrid_recommendations(
        emotion_text=emotion_text,
        user_ratings=user_ratings,
        top_k=3,
        emotion_weight=0.7
    )
    
    print(f"🎭 Emotion text: {emotion_text}")
    print(f"📊 User ratings: {len(user_ratings)} movies")
    print(f"🎯 Hybrid recommendations:")
    
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result['title']} (Score: {result['similarity_score']:.3f})")
        print(f"     Type: {result['recommendation_type']}")

def test_advanced_hybrid():
    """Test advanced hybrid recommendations with full system"""
    print("\n🚀 Testing Advanced Hybrid Recommendations...")
    
    db = next(get_db())
    recommendation_service = RecommendationService(db)
    
    # Test with user ID 1 (assuming exists)
    user_id = 1
    emotion_text = "Bugün kendimi değersiz hissettiğimi söyledim"
    
    try:
        result = recommendation_service.get_advanced_hybrid_recommendations(
            user_id=user_id,
            emotion_text=emotion_text,
            content_type="movie"
        )
        
        if result["success"]:
            print(f"✅ Advanced hybrid recommendations generated!")
            print(f"📊 Emotion analysis: {result['data']['emotion_analysis']}")
            print(f"🎯 Recommendations: {len(result['data']['recommendations'])} movies")
            
            for i, rec in enumerate(result['data']['recommendations'][:3], 1):
                print(f"  {i}. {rec['title']} (Final Score: {rec['final_score']:.3f})")
                print(f"     Sources: {rec['recommendation_sources']}")
        else:
            print(f"❌ Error: {result['error']}")
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

if __name__ == "__main__":
    print("🎬 Parotia Embedding System Test")
    print("=" * 50)
    
    try:
        # Run tests
        test_embedding_generation()
        test_emotion_analysis()
        test_similarity_search()
        test_user_embedding()
        test_hybrid_recommendations()
        test_advanced_hybrid()
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc() 