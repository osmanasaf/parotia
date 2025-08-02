#!/usr/bin/env python3
"""
Test script for Parotia Embedding-Based Emotion Analysis System
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "testpassword123"

class EmbeddingEmotionTester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.user_id = None
    
    def login(self) -> bool:
        """Login and get authentication token"""
        try:
            login_data = {
                "username": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            }
            
            response = self.session.post(f"{BASE_URL}/auth/login", data=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                print("✅ Login successful")
                return True
            else:
                print(f"❌ Login failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Login error: {str(e)}")
            return False
    
    def test_embedding_emotion_analysis(self) -> bool:
        """Test embedding-based emotion analysis"""
        print("\n🧠 Testing Embedding-Based Emotion Analysis...")
        
        test_emotions = [
            "Bugün kendimi çok yalnız hissediyorum",
            "Harika bir gün geçirdim, çok mutluyum!",
            "Stresli bir hafta geçirdim, rahatlamaya ihtiyacım var",
            "Romantik bir film izlemek istiyorum",
            "İlham verici bir şeyler arıyorum"
        ]
        
        for emotion_text in test_emotions:
            try:
                response = self.session.post(
                    f"{BASE_URL}/emotion/analyze",
                    params={"emotion_text": emotion_text}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    analysis = data.get("data", {}).get("analysis", {})
                    
                    print(f"✅ '{emotion_text[:30]}...' -> Embedding-based analysis")
                    print(f"   - Similar content count: {analysis.get('similar_content_count', 0)}")
                    print(f"   - Confidence: {analysis.get('confidence', 0):.2f}")
                    print(f"   - Embedding length: {len(analysis.get('emotion_embedding', []))}")
                else:
                    print(f"❌ Emotion analysis failed: {response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"❌ Emotion analysis error: {str(e)}")
                return False
        
        return True
    
    def test_user_emotion_from_watched_content(self) -> bool:
        """Test getting user emotion from watched content"""
        print("\n📺 Testing User Emotion from Watched Content...")
        
        try:
            response = self.session.post(
                f"{BASE_URL}/emotion/user-watched-content",
                params={"content_type": "movie"}
            )
            
            if response.status_code == 200:
                data = response.json()
                result = data.get("data", {})
                
                print(f"✅ User emotion from watched content:")
                print(f"   - Watched content count: {result.get('watched_content_count', 0)}")
                print(f"   - Confidence: {result.get('confidence', 0):.2f}")
                print(f"   - Embedding length: {len(result.get('emotion_embedding', []))}")
                
                if result.get('emotional_profile'):
                    profile = result['emotional_profile']
                    print(f"   - Average rating: {profile.get('average_rating', 0):.2f}")
                    print(f"   - Content diversity: {profile.get('content_diversity', 0):.2f}")
                    print(f"   - Preference intensity: {profile.get('preference_intensity', 0):.2f}")
            else:
                print(f"❌ User emotion from watched content failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ User emotion from watched content error: {str(e)}")
            return False
        
        return True
    
    def test_embedding_content_analysis(self) -> bool:
        """Test embedding-based content emotional analysis"""
        print("\n🎭 Testing Embedding-Based Content Analysis...")
        
        test_content = [
            {"tmdb_id": 550, "content_type": "movie"},  # Fight Club
            {"tmdb_id": 13, "content_type": "movie"},   # Forrest Gump
            {"tmdb_id": 238, "content_type": "movie"},  # The Godfather
        ]
        
        for content in test_content:
            try:
                response = self.session.post(
                    f"{BASE_URL}/emotion/content-tone/{content['tmdb_id']}",
                    params={"content_type": content["content_type"]}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    analysis = data.get("data", {}).get("emotional_analysis", {})
                    
                    print(f"✅ Content {content['tmdb_id']} ({content['content_type']}):")
                    print(f"   - Similar content count: {analysis.get('similar_content_count', 0)}")
                    print(f"   - Confidence: {analysis.get('confidence_score', 0):.2f}")
                    print(f"   - Embedding length: {len(analysis.get('content_embedding', []))}")
                    
                    if analysis.get('emotional_characteristics'):
                        chars = analysis['emotional_characteristics']
                        print(f"   - Intensity: {chars.get('intensity', 0):.2f}")
                        print(f"   - Complexity: {chars.get('complexity', 0):.2f}")
                        print(f"   - Mood improving: {chars.get('mood_improving', 0):.2f}")
                        print(f"   - Thought provoking: {chars.get('thought_provoking', 0):.2f}")
                else:
                    print(f"❌ Content analysis failed: {response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"❌ Content analysis error: {str(e)}")
                return False
        
        return True
    
    def test_embedding_recommendations(self) -> bool:
        """Test embedding-based recommendations"""
        print("\n🎬 Testing Embedding-Based Recommendations...")
        
        test_cases = [
            {
                "endpoint": "/recommendations/emotion",
                "params": {"emotion_text": "Bugün kendimi çok yalnız hissediyorum", "content_type": "movie"}
            },
            {
                "endpoint": "/recommendations/hybrid",
                "params": {"emotion_text": "Harika bir gün geçirdim", "content_type": "movie"}
            },
            {
                "endpoint": "/recommendations/mix",
                "params": {"emotion_text": "Romantik bir şeyler arıyorum"}
            }
        ]
        
        for test_case in test_cases:
            try:
                response = self.session.post(
                    f"{BASE_URL}{test_case['endpoint']}",
                    params=test_case['params']
                )
                
                if response.status_code == 200:
                    data = response.json()
                    recommendations = data.get("data", {}).get("recommendations", [])
                    
                    print(f"✅ {test_case['endpoint']}:")
                    print(f"   - Recommendations count: {len(recommendations)}")
                    print(f"   - Recommendation type: {data.get('data', {}).get('recommendation_type', 'unknown')}")
                    
                    if recommendations:
                        first_rec = recommendations[0]
                        print(f"   - Top recommendation: {first_rec.get('title', 'Unknown')}")
                        print(f"   - Similarity score: {first_rec.get('similarity_score', 0):.3f}")
                else:
                    print(f"❌ {test_case['endpoint']} failed: {response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"❌ {test_case['endpoint']} error: {str(e)}")
                return False
        
        return True
    
    def test_embedding_insights(self) -> bool:
        """Test embedding-based emotion insights"""
        print("\n📊 Testing Embedding-Based Emotion Insights...")
        
        try:
            response = self.session.get(f"{BASE_URL}/emotion/insights")
            
            if response.status_code == 200:
                data = response.json()
                insights = data.get("data", {})
                
                print(f"✅ Emotion insights:")
                print(f"   - Success rate: {insights.get('success_rate', 0):.2f}")
                print(f"   - Total recommendations: {insights.get('total_recommendations', 0)}")
                print(f"   - Successful recommendations: {insights.get('successful_recommendations', 0)}")
                print(f"   - Learning rate: {insights.get('learning_rate', 0):.2f}")
                
                if insights.get('average_embedding'):
                    print(f"   - Average embedding length: {len(insights['average_embedding'])}")
                
                if insights.get('top_characteristics'):
                    print(f"   - Top characteristics: {insights['top_characteristics'][:3]}")
            else:
                print(f"❌ Emotion insights failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Emotion insights error: {str(e)}")
            return False
        
        return True
    
    def run_all_tests(self) -> bool:
        """Run all embedding-based emotion tests"""
        print("🚀 Starting Embedding-Based Emotion Analysis System Tests")
        print("=" * 60)
        
        if not self.login():
            return False
        
        tests = [
            ("Embedding Emotion Analysis", self.test_embedding_emotion_analysis),
            ("User Emotion from Watched Content", self.test_user_emotion_from_watched_content),
            ("Embedding Content Analysis", self.test_embedding_content_analysis),
            ("Embedding Recommendations", self.test_embedding_recommendations),
            ("Embedding Insights", self.test_embedding_insights),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n{'='*20} {test_name} {'='*20}")
            try:
                if test_func():
                    passed += 1
                    print(f"✅ {test_name} PASSED")
                else:
                    print(f"❌ {test_name} FAILED")
            except Exception as e:
                print(f"❌ {test_name} ERROR: {str(e)}")
        
        print(f"\n{'='*60}")
        print(f"📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Embedding-based emotion system is working correctly.")
        else:
            print("⚠️  Some tests failed. Please check the implementation.")
        
        return passed == total

def main():
    """Main function to run tests"""
    tester = EmbeddingEmotionTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ All embedding-based emotion analysis tests completed successfully!")
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
    
    return success

if __name__ == "__main__":
    main() 