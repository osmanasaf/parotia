#!/usr/bin/env python3
"""
Test script for Parotia Emotion Analysis and Feedback Features
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "testpassword123"

class EmotionFeatureTester:
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
    
    def test_emotion_analysis(self) -> bool:
        """Test emotion analysis functionality"""
        print("\n🧠 Testing Emotion Analysis...")
        
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
                    
                    print(f"✅ '{emotion_text[:30]}...' -> {analysis.get('primary_emotion', 'unknown')} "
                          f"(confidence: {analysis.get('confidence', 0):.2f})")
                else:
                    print(f"❌ Emotion analysis failed: {response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"❌ Emotion analysis error: {str(e)}")
                return False
        
        return True
    
    def test_content_emotional_tone(self) -> bool:
        """Test content emotional tone analysis"""
        print("\n🎭 Testing Content Emotional Tone Analysis...")
        
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
                    
                    print(f"✅ TMDB {content['tmdb_id']} -> {analysis.get('primary_emotion', 'unknown')} "
                          f"(mood_improving: {analysis.get('mood_improving', False)})")
                else:
                    print(f"❌ Content tone analysis failed: {response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"❌ Content tone analysis error: {str(e)}")
                return False
        
        return True
    
    def test_feedback_survey(self) -> bool:
        """Test feedback survey creation"""
        print("\n📝 Testing Feedback Survey...")
        
        try:
            response = self.session.get(
                f"{BASE_URL}/emotion/survey/550",
                params={"content_type": "movie"}
            )
            
            if response.status_code == 200:
                data = response.json()
                survey = data.get("data", {})
                
                print(f"✅ Survey created for TMDB 550")
                print(f"   Questions: {len(survey.get('questions', []))}")
                print(f"   Pre-viewing emotion: {survey.get('pre_viewing_emotion', 'unknown')}")
                return True
            else:
                print(f"❌ Survey creation failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Survey creation error: {str(e)}")
            return False
    
    def test_post_viewing_feedback(self) -> bool:
        """Test post-viewing feedback submission"""
        print("\n💭 Testing Post-Viewing Feedback...")
        
        feedback_data = {
            "tmdb_id": 550,
            "content_type": "movie",
            "pre_viewing_emotion": "sad",
            "pre_viewing_emotion_text": "Kendimi yalnız hissediyordum",
            "post_viewing_emotion": "inspired",
            "post_viewing_emotion_text": "Film beni çok etkiledi, daha güçlü hissettim",
            "emotional_impact_score": 9,
            "recommendation_accuracy": 8,
            "mood_improvement": True,
            "emotional_catharsis": True,
            "would_recommend_to_others": True,
            "additional_comments": "Harika bir film, tam ihtiyacım olan şeydi!"
        }
        
        try:
            response = self.session.post(
                f"{BASE_URL}/emotion/feedback",
                json=feedback_data
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Feedback submitted successfully")
                print(f"   User ID: {data.get('data', {}).get('user_id')}")
                print(f"   TMDB ID: {data.get('data', {}).get('tmdb_id')}")
                return True
            else:
                print(f"❌ Feedback submission failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Feedback submission error: {str(e)}")
            return False
    
    def test_emotion_insights(self) -> bool:
        """Test emotion insights retrieval"""
        print("\n📊 Testing Emotion Insights...")
        
        try:
            response = self.session.get(f"{BASE_URL}/emotion/insights")
            
            if response.status_code == 200:
                data = response.json()
                insights = data.get("data", {})
                
                print(f"✅ Emotion insights retrieved")
                print(f"   Success rate: {insights.get('success_rate', 0):.2%}")
                print(f"   Total recommendations: {insights.get('total_recommendations', 0)}")
                print(f"   Top emotions: {insights.get('top_emotions', [])}")
                return True
            else:
                print(f"❌ Emotion insights failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Emotion insights error: {str(e)}")
            return False
    
    def test_notification_features(self) -> bool:
        """Test notification features"""
        print("\n🔔 Testing Notification Features...")
        
        # Test pending notifications
        try:
            response = self.session.get(f"{BASE_URL}/emotion/notifications/pending")
            
            if response.status_code == 200:
                data = response.json()
                notifications = data.get("data", {}).get("notifications", [])
                
                print(f"✅ Pending notifications: {len(notifications)}")
                
                # Test notification history
                response = self.session.get(f"{BASE_URL}/emotion/notifications/history")
                
                if response.status_code == 200:
                    data = response.json()
                    history = data.get("data", {}).get("history", [])
                    
                    print(f"✅ Notification history: {len(history)} items")
                    return True
                else:
                    print(f"❌ Notification history failed: {response.status_code}")
                    return False
            else:
                print(f"❌ Pending notifications failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Notification features error: {str(e)}")
            return False
    
    def test_statistics(self) -> bool:
        """Test statistics endpoint"""
        print("\n📈 Testing Statistics...")
        
        try:
            response = self.session.get(f"{BASE_URL}/emotion/statistics")
            
            if response.status_code == 200:
                data = response.json()
                stats = data.get("data", {})
                
                print(f"✅ Statistics retrieved")
                print(f"   Total notifications: {stats.get('total_notifications_sent', 0)}")
                print(f"   Feedback rate: {stats.get('feedback_rate_percentage', 0):.1f}%")
                print(f"   Average emotional impact: {stats.get('average_emotional_impact', 0):.1f}")
                return True
            else:
                print(f"❌ Statistics failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Statistics error: {str(e)}")
            return False
    
    def test_emotion_profile_update(self) -> bool:
        """Test emotion profile update"""
        print("\n⚙️ Testing Emotion Profile Update...")
        
        try:
            response = self.session.post(
                f"{BASE_URL}/emotion/profile/update",
                params={"learning_rate": 0.15}
            )
            
            if response.status_code == 200:
                data = response.json()
                profile_data = data.get("data", {})
                
                print(f"✅ Profile updated successfully")
                print(f"   Learning rate: {profile_data.get('learning_rate', 0)}")
                print(f"   Total recommendations: {profile_data.get('total_recommendations', 0)}")
                return True
            else:
                print(f"❌ Profile update failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Profile update error: {str(e)}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all emotion feature tests"""
        print("🚀 Starting Emotion Analysis and Feedback Feature Tests")
        print("=" * 60)
        
        if not self.login():
            return False
        
        tests = [
            ("Emotion Analysis", self.test_emotion_analysis),
            ("Content Emotional Tone", self.test_content_emotional_tone),
            ("Feedback Survey", self.test_feedback_survey),
            ("Post-Viewing Feedback", self.test_post_viewing_feedback),
            ("Emotion Insights", self.test_emotion_insights),
            ("Notification Features", self.test_notification_features),
            ("Statistics", self.test_statistics),
            ("Profile Update", self.test_emotion_profile_update),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                else:
                    print(f"❌ {test_name} test failed")
            except Exception as e:
                print(f"❌ {test_name} test error: {str(e)}")
        
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All emotion features working correctly!")
        else:
            print("⚠️ Some tests failed. Check the logs above.")
        
        return passed == total

def main():
    """Main test function"""
    tester = EmotionFeatureTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ All emotion analysis and feedback features are working!")
    else:
        print("\n❌ Some features need attention.")
    
    return success

if __name__ == "__main__":
    main() 