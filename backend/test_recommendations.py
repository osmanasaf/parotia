#!/usr/bin/env python3
"""
Test script for recommendation system
"""

import requests
import json
import sys
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "testpassword123"

def login_user() -> str:
    """Login user and return access token"""
    try:
        login_data = {
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        }
        
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        
        if response.status_code == 200:
            data = response.json()
            return data["data"]["access_token"]
        else:
            print(f"Login failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Login error: {str(e)}")
        return None

def test_embedding_stats(token: str) -> bool:
    """Test embedding index statistics"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/recommendations/embedding/stats", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            stats = data["data"]
            print(f"✅ Embedding Stats:")
            print(f"   Total content: {stats['total_content']}")
            print(f"   Index size: {stats['index_size']}")
            print(f"   Movie count: {stats['movie_count']}")
            print(f"   TV count: {stats['tv_count']}")
            return stats['total_content'] > 0
        else:
            print(f"❌ Embedding stats failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Embedding stats error: {str(e)}")
        return False

def test_emotion_recommendations(token: str) -> bool:
    """Test emotion-based recommendations"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test movie recommendations
        movie_data = {
            "emotion": "Bugün kendimi çok yalnız hissediyorum",
            "content_type": "movie"
        }
        
        response = requests.post(f"{BASE_URL}/recommendations/emotion", json=movie_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            recommendations = data["data"]["recommendations"]
            print(f"✅ Emotion-based movie recommendations: {len(recommendations)} found")
            for i, rec in enumerate(recommendations[:3]):
                print(f"   {i+1}. {rec['title']} (Score: {rec['similarity_score']:.3f})")
            return len(recommendations) > 0
        else:
            print(f"❌ Emotion recommendations failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Emotion recommendations error: {str(e)}")
        return False

def test_hybrid_recommendations(token: str) -> bool:
    """Test hybrid recommendations"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test hybrid recommendations
        hybrid_data = {
            "emotion_text": "Bugün kendimi çok yalnız hissediyorum",
            "content_type": "movie"
        }
        
        response = requests.post(f"{BASE_URL}/recommendations/hybrid", json=hybrid_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            recommendations = data["data"]["recommendations"]
            print(f"✅ Hybrid recommendations: {len(recommendations)} found")
            for i, rec in enumerate(recommendations[:3]):
                print(f"   {i+1}. {rec['title']} (Score: {rec['similarity_score']:.3f})")
            return len(recommendations) > 0
        else:
            print(f"❌ Hybrid recommendations failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Hybrid recommendations error: {str(e)}")
        return False

def test_mix_recommendations(token: str) -> bool:
    """Test mix recommendations (no content type specified)"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test mix recommendations (no content type)
        params = {
            "emotion_text": "Bugün kendimi çok yalnız hissediyorum"
        }
        
        response = requests.post(f"{BASE_URL}/recommendations/mix", params=params, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            recommendations = data["data"]["recommendations"]
            movie_count = data["data"]["movie_count"]
            tv_count = data["data"]["tv_count"]
            print(f"✅ Mix recommendations: {len(recommendations)} found ({movie_count} movies, {tv_count} TV shows)")
            for i, rec in enumerate(recommendations[:3]):
                print(f"   {i+1}. {rec['title']} ({rec['content_type']}) (Score: {rec['similarity_score']:.3f})")
            return len(recommendations) > 0
        else:
            print(f"❌ Mix recommendations failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Mix recommendations error: {str(e)}")
        return False

def test_history_recommendations(token: str) -> bool:
    """Test history-based recommendations"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test history-based recommendations
        history_data = {
            "content_type": "movie"
        }
        
        response = requests.post(f"{BASE_URL}/recommendations/history", json=history_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            recommendations = data["data"]["recommendations"]
            print(f"✅ History-based recommendations: {len(recommendations)} found")
            if recommendations:
                for i, rec in enumerate(recommendations[:3]):
                    print(f"   {i+1}. {rec['title']} (Score: {rec['similarity_score']:.3f})")
            else:
                print("   No recommendations (user has no rating history)")
            return True
        else:
            print(f"❌ History recommendations failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ History recommendations error: {str(e)}")
        return False

def test_advanced_hybrid_recommendations(token: str) -> bool:
    """Test advanced hybrid recommendations with emotion analysis"""
    print("\n=== Testing Advanced Hybrid Recommendations ===")
    
    # Test emotion-based recommendations
    emotion_text = "Bugün kendimi çok yalnız hissediyorum"
    
    response = requests.post(
        f"{BASE_URL}/recommendations/advanced-hybrid",
        params={
            "emotion_text": emotion_text,
            "content_type": "movie"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Advanced Hybrid Recommendations (Movie):")
        print(f"   Emotion Analysis: {data['data']['emotion_analysis']}")
        print(f"   User Profile: {data['data']['user_profile']}")
        print(f"   Total Recommendations: {data['data']['total']}")
        print(f"   Breakdown: {data['data']['recommendation_breakdown']}")
        
        # Show first recommendation
        if data['data']['recommendations']:
            first_rec = data['data']['recommendations'][0]
            print(f"   Top Recommendation: {first_rec['title']} (Score: {first_rec['final_score']:.3f})")
            print(f"   Sources: {first_rec['recommendation_sources']}")
        return True
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
        return False

def test_mix_advanced_recommendations(token: str) -> bool:
    """Test advanced hybrid recommendations for mix content type"""
    print("\n=== Testing Advanced Hybrid Mix Recommendations ===")
    
    emotion_text = "Bugün kendimi çok yalnız hissediyorum"
    
    response = requests.post(
        f"{BASE_URL}/recommendations/advanced-hybrid",
        params={
            "emotion_text": emotion_text,
            "content_type": "mix"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Advanced Hybrid Mix Recommendations:")
        print(f"   Total Recommendations: {data['data']['total']}")
        print(f"   Breakdown: {data['data']['recommendation_breakdown']}")
        
        # Show recommendations by type
        movies = [r for r in data['data']['recommendations'] if r['content_type'] == 'movie']
        tv_shows = [r for r in data['data']['recommendations'] if r['content_type'] == 'tv']
        
        if movies:
            print(f"   Top Movie: {movies[0]['title']} (Score: {movies[0]['final_score']:.3f})")
        if tv_shows:
            print(f"   Top TV Show: {tv_shows[0]['title']} (Score: {tv_shows[0]['final_score']:.3f})")
        return True
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
        return False

def main():
    """Main test function"""
    print("🎬 Testing Parotia Recommendation System")
    print("=" * 50)
    
    # Login
    print("🔐 Logging in...")
    token = login_user()
    if not token:
        print("❌ Failed to login. Exiting.")
        sys.exit(1)
    
    print("✅ Login successful")
    print()
    
    # Test embedding stats
    print("📊 Testing embedding statistics...")
    has_content = test_embedding_stats(token)
    print()
    
    if not has_content:
        print("⚠️  No content in embedding index. Please populate the index first.")
        print("   Run: POST /recommendations/embedding/populate")
        print()
    
    # Test recommendations
    tests = [
        ("Emotion-based recommendations", test_emotion_recommendations),
        ("Hybrid recommendations", test_hybrid_recommendations),
        ("Mix recommendations", test_mix_recommendations),
        ("History-based recommendations", test_history_recommendations),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"🧪 Testing {test_name}...")
        result = test_func(token)
        results.append((test_name, result))
        print()
    
    # Test advanced hybrid recommendations
    test_advanced_hybrid_recommendations(token)
    test_mix_advanced_recommendations(token)
    
    # Summary
    print("📋 Test Summary:")
    print("=" * 30)
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Recommendation system is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the logs above.")

if __name__ == "__main__":
    main() 