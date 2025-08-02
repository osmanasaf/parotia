#!/usr/bin/env python3
"""
Test script to populate the embedding system with 50 movies and 50 TV shows
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings
from app.services.recommendation_service import RecommendationService
from app.services.embedding_service import EmbeddingService
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_populate_system():
    """Test populating the embedding system with movies and TV shows"""
    
    try:
        # Initialize database connection
        settings = get_settings()
        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # Initialize services
        recommendation_service = RecommendationService(db)
        embedding_service = EmbeddingService()
        
        print("🎬 Parotia Embedding Sistemi Test Ediliyor...")
        print("=" * 50)
        
        # Check current stats
        print("\n📊 Mevcut Durum:")
        current_stats = embedding_service.get_index_stats()
        print(f"Toplam içerik: {current_stats.get('total_items', 0)}")
        print(f"Film sayısı: {current_stats.get('movie_count', 0)}")
        print(f"TV dizi sayısı: {current_stats.get('tv_count', 0)}")
        
        # Populate with 50 movies (5 pages * 10 movies per page)
        print("\n🎭 50 Film Ekleniyor...")
        movie_result = recommendation_service.populate_embedding_index_with_details(
            content_type="movie", 
            pages=5
        )
        
        if movie_result["success"]:
            print(f"✅ Filmler eklendi: {movie_result['data']['added_count']}")
            print(f"❌ Başarısız: {movie_result['data']['failed_count']}")
        else:
            print(f"❌ Film ekleme hatası: {movie_result.get('error')}")
        
        # Populate with 50 TV shows (5 pages * 10 shows per page)
        print("\n📺 50 TV Dizisi Ekleniyor...")
        tv_result = recommendation_service.populate_embedding_index_with_details(
            content_type="tv", 
            pages=5
        )
        
        if tv_result["success"]:
            print(f"✅ TV dizileri eklendi: {tv_result['data']['added_count']}")
            print(f"❌ Başarısız: {tv_result['data']['failed_count']}")
        else:
            print(f"❌ TV dizi ekleme hatası: {tv_result.get('error')}")
        
        # Final stats
        print("\n📊 Final Durum:")
        final_stats = embedding_service.get_index_stats()
        print(f"Toplam içerik: {final_stats.get('total_items', 0)}")
        print(f"Film sayısı: {final_stats.get('movie_count', 0)}")
        print(f"TV dizi sayısı: {final_stats.get('tv_count', 0)}")
        print(f"Model: {final_stats.get('model_name', 'N/A')}")
        print(f"Boyut: {final_stats.get('index_dimension', 0)}")
        
        # Test search functionality
        print("\n🔍 Arama Fonksiyonu Test Ediliyor...")
        
        # Test emotion-based search
        print("\n1. Duygu bazlı arama testi:")
        emotion_results = embedding_service.search_similar_content(
            query_text="Bugün kendimi değersiz hissettiğimi söyledim",
            top_k=5,
            content_type="movie"
        )
        
        print(f"Bulunan film sayısı: {len(emotion_results)}")
        for i, result in enumerate(emotion_results[:3], 1):
            print(f"  {i}. {result.get('title', 'N/A')} (Skor: {result.get('similarity_score', 0):.3f})")
        
        # Test TV search
        print("\n2. TV dizi arama testi:")
        tv_results = embedding_service.search_similar_content(
            query_text="heyecanlı ve sürükleyici dizi",
            top_k=5,
            content_type="tv"
        )
        
        print(f"Bulunan dizi sayısı: {len(tv_results)}")
        for i, result in enumerate(tv_results[:3], 1):
            print(f"  {i}. {result.get('name', 'N/A')} (Skor: {result.get('similarity_score', 0):.3f})")
        
        print("\n✅ Sistem başarıyla test edildi!")
        
    except Exception as e:
        logger.error(f"Test sırasında hata: {str(e)}")
        print(f"❌ Hata: {str(e)}")
    
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    test_populate_system() 