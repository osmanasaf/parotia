#!/usr/bin/env python3
"""
Test script for the hybrid recommendation system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings
from app.services.recommendation_service import RecommendationService
from app.services.embedding_service import EmbeddingService
from app.services.emotion_analysis_service import EmotionAnalysisService
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_hybrid_system():
    """Test the hybrid recommendation system"""
    
    try:
        # Initialize database connection
        settings = get_settings()
        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # Initialize services
        recommendation_service = RecommendationService(db)
        embedding_service = EmbeddingService()
        emotion_service = EmotionAnalysisService(db)
        
        print("🧠 Parotia Hibrit Öneri Sistemi Test Ediliyor...")
        print("=" * 60)
        
        # Check current stats
        print("\n📊 Mevcut Embedding Durumu:")
        current_stats = embedding_service.get_index_stats()
        print(f"Toplam içerik: {current_stats.get('total_items', 0)}")
        print(f"Film sayısı: {current_stats.get('movie_count', 0)}")
        print(f"TV dizi sayısı: {current_stats.get('tv_count', 0)}")
        
        # Test emotion analysis
        print("\n😊 Duygu Analizi Testi:")
        test_emotion = "Bugün kendimi değersiz hissettiğimi söyledim"
        emotion_analysis = emotion_service.analyze_user_emotion(test_emotion)
        print(f"Metin: '{test_emotion}'")
        print(f"Ana duygu: {emotion_analysis.get('primary_emotion', 'N/A')}")
        print(f"Duygu yoğunluğu: {emotion_analysis.get('emotional_intensity', 0):.2f}")
        print(f"Duygu tonu: {emotion_analysis.get('emotional_tone', 'N/A')}")
        print(f"Güven: {emotion_analysis.get('confidence', 0):.2f}")
        
        # Test basic emotion-based search
        print("\n🎭 Duygu Bazlı Film Arama Testi:")
        emotion_results = embedding_service.search_similar_content(
            query_text=test_emotion,
            top_k=5,
            content_type="movie"
        )
        
        print(f"Bulunan film sayısı: {len(emotion_results)}")
        for i, result in enumerate(emotion_results[:3], 1):
            print(f"  {i}. {result.get('title', 'N/A')} (Skor: {result.get('similarity_score', 0):.3f})")
        
        # Test TV search
        print("\n📺 Duygu Bazlı TV Dizi Arama Testi:")
        tv_results = embedding_service.search_similar_content(
            query_text=test_emotion,
            top_k=5,
            content_type="tv"
        )
        
        print(f"Bulunan dizi sayısı: {len(tv_results)}")
        for i, result in enumerate(tv_results[:3], 1):
            print(f"  {i}. {result.get('name', 'N/A')} (Skor: {result.get('similarity_score', 0):.3f})")
        
        # Test different emotions
        print("\n🎭 Farklı Duygularla Test:")
        test_emotions = [
            "Bugün çok mutluyum ve enerjik hissediyorum",
            "Stresli ve endişeli hissediyorum",
            "Romantik bir ruh halindeyim",
            "İlham verici bir şeyler arıyorum"
        ]
        
        for emotion in test_emotions:
            print(f"\nDuygu: '{emotion}'")
            emotion_analysis = emotion_service.analyze_user_emotion(emotion)
            print(f"  Ana duygu: {emotion_analysis.get('primary_emotion', 'N/A')}")
            
            results = embedding_service.search_similar_content(
                query_text=emotion,
                top_k=3,
                content_type="movie"
            )
            
            if results:
                print(f"  Önerilen: {results[0].get('title', 'N/A')} (Skor: {results[0].get('similarity_score', 0):.3f})")
        
        # Test embedding generation
        print("\n🔧 Embedding Testi:")
        test_text = "Bu bir test metnidir"
        embedding = embedding_service.test_embedding(test_text)
        print(f"Test metni: '{test_text}'")
        print(f"Embedding boyutu: {len(embedding)}")
        print(f"İlk 5 değer: {embedding[:5]}")
        
        print("\n✅ Hibrit sistem başarıyla test edildi!")
        
    except Exception as e:
        logger.error(f"Test sırasında hata: {str(e)}")
        print(f"❌ Hata: {str(e)}")
    
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    test_hybrid_system() 