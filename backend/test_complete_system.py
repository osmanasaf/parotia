#!/usr/bin/env python3
"""
Complete system test for Parotia recommendation system
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
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_complete_system():
    """Test the complete recommendation system"""
    
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
        
        print("🎬 Parotia Tam Sistem Testi Başlıyor...")
        print("=" * 60)
        
        # Step 1: Check current stats
        print("\n📊 1. Mevcut Durum Kontrolü:")
        current_stats = embedding_service.get_index_stats()
        print(f"   Toplam içerik: {current_stats.get('total_items', 0)}")
        print(f"   Film sayısı: {current_stats.get('movie_count', 0)}")
        print(f"   TV dizi sayısı: {current_stats.get('tv_count', 0)}")
        
        # Step 2: Populate with movies if needed
        if current_stats.get('movie_count', 0) < 10:
            print("\n🎭 2. Film Veritabanı Dolduruluyor...")
            start_time = time.time()
            movie_result = recommendation_service.populate_embedding_index_with_details(
                content_type="movie", 
                pages=3  # 30 films
            )
            end_time = time.time()
            
            if movie_result["success"]:
                print(f"   ✅ {movie_result['data']['added_count']} film eklendi")
                print(f"   ⏱️  Süre: {end_time - start_time:.2f} saniye")
            else:
                print(f"   ❌ Film ekleme hatası: {movie_result.get('error')}")
        
        # Step 3: Populate with TV shows if needed
        if current_stats.get('tv_count', 0) < 10:
            print("\n📺 3. TV Dizi Veritabanı Dolduruluyor...")
            start_time = time.time()
            tv_result = recommendation_service.populate_embedding_index_with_details(
                content_type="tv", 
                pages=3  # 30 TV shows
            )
            end_time = time.time()
            
            if tv_result["success"]:
                print(f"   ✅ {tv_result['data']['added_count']} TV dizisi eklendi")
                print(f"   ⏱️  Süre: {end_time - start_time:.2f} saniye")
            else:
                print(f"   ❌ TV dizi ekleme hatası: {tv_result.get('error')}")
        
        # Step 4: Updated stats
        print("\n📊 4. Güncellenmiş Durum:")
        updated_stats = embedding_service.get_index_stats()
        print(f"   Toplam içerik: {updated_stats.get('total_items', 0)}")
        print(f"   Film sayısı: {updated_stats.get('movie_count', 0)}")
        print(f"   TV dizi sayısı: {updated_stats.get('tv_count', 0)}")
        
        # Step 5: Test emotion analysis
        print("\n😊 5. Duygu Analizi Testi:")
        test_emotions = [
            "Bugün kendimi değersiz hissettiğimi söyledim",
            "Çok mutluyum ve enerjik hissediyorum",
            "Stresli ve endişeli hissediyorum",
            "Romantik bir ruh halindeyim"
        ]
        
        for emotion in test_emotions:
            print(f"\n   Duygu: '{emotion}'")
            emotion_analysis = emotion_service.analyze_user_emotion(emotion)
            print(f"   Ana duygu: {emotion_analysis.get('primary_emotion', 'N/A')}")
            print(f"   Yoğunluk: {emotion_analysis.get('emotional_intensity', 0):.2f}")
        
        # Step 6: Test basic search
        print("\n🔍 6. Temel Arama Testi:")
        test_query = "Bugün kendimi değersiz hissettiğimi söyledim"
        
        # Movie search
        movie_results = embedding_service.search_similar_content(
            query_text=test_query,
            top_k=5,
            content_type="movie"
        )
        print(f"   Film arama sonuçları: {len(movie_results)} film bulundu")
        if movie_results:
            print(f"   En iyi eşleşme: {movie_results[0].get('title', 'N/A')} (Skor: {movie_results[0].get('similarity_score', 0):.3f})")
        
        # TV search
        tv_results = embedding_service.search_similar_content(
            query_text=test_query,
            top_k=5,
            content_type="tv"
        )
        print(f"   TV arama sonuçları: {len(tv_results)} dizi bulundu")
        if tv_results:
            print(f"   En iyi eşleşme: {tv_results[0].get('name', 'N/A')} (Skor: {tv_results[0].get('similarity_score', 0):.3f})")
        
        # Step 7: Test embedding generation
        print("\n🔧 7. Embedding Testi:")
        test_text = "Bu bir test metnidir"
        embedding = embedding_service.test_embedding(test_text)
        print(f"   Test metni: '{test_text}'")
        print(f"   Embedding boyutu: {len(embedding)}")
        print(f"   İlk 3 değer: {embedding[:3]}")
        
        # Step 8: Performance test
        print("\n⚡ 8. Performans Testi:")
        start_time = time.time()
        for i in range(5):
            results = embedding_service.search_similar_content(
                query_text=f"Test query {i}",
                top_k=10,
                content_type="movie"
            )
        end_time = time.time()
        avg_time = (end_time - start_time) / 5
        print(f"   Ortalama arama süresi: {avg_time:.3f} saniye")
        
        print("\n✅ Tam sistem testi başarıyla tamamlandı!")
        print("\n🎯 Sistem Hazır! Şimdi şunları yapabilirsiniz:")
        print("   1. FastAPI sunucusunu başlatın: uvicorn app.main:app --reload")
        print("   2. /docs endpoint'ine giderek API'yi test edin")
        print("   3. /recommendations/efficient-hybrid endpoint'ini kullanın")
        
    except Exception as e:
        logger.error(f"Test sırasında hata: {str(e)}")
        print(f"❌ Hata: {str(e)}")
    
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    test_complete_system() 