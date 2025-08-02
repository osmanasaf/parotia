#!/usr/bin/env python3
"""
Quick test for the embedding system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.embedding_service import EmbeddingService
from app.services.emotion_analysis_service import EmotionAnalysisService
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def quick_test():
    """Quick test of the embedding system"""
    
    try:
        print("🚀 Hızlı Sistem Testi Başlıyor...")
        print("=" * 40)
        
        # Initialize services
        embedding_service = EmbeddingService()
        emotion_service = EmotionAnalysisService(None)  # No DB needed for basic tests
        
        # Check current stats
        print("\n📊 Mevcut Durum:")
        stats = embedding_service.get_index_stats()
        print(f"Toplam içerik: {stats.get('total_items', 0)}")
        print(f"Film sayısı: {stats.get('movie_count', 0)}")
        print(f"TV dizi sayısı: {stats.get('tv_count', 0)}")
        
        # Test emotion analysis
        print("\n😊 Duygu Analizi Testi:")
        test_emotion = "Bugün kendimi değersiz hissettiğimi söyledim"
        emotion_analysis = emotion_service.analyze_user_emotion(test_emotion)
        print(f"Metin: '{test_emotion}'")
        print(f"Ana duygu: {emotion_analysis.get('primary_emotion', 'N/A')}")
        print(f"Yoğunluk: {emotion_analysis.get('emotional_intensity', 0):.2f}")
        
        # Test embedding generation
        print("\n🔧 Embedding Testi:")
        test_text = "Bu bir test metnidir"
        embedding = embedding_service.test_embedding(test_text)
        print(f"Test metni: '{test_text}'")
        print(f"Embedding boyutu: {len(embedding)}")
        print(f"İlk 3 değer: {embedding[:3]}")
        
        # Test search if we have content
        if stats.get('total_items', 0) > 0:
            print("\n🔍 Arama Testi:")
            results = embedding_service.search_similar_content(
                query_text=test_emotion,
                top_k=3,
                content_type="movie"
            )
            print(f"Bulunan sonuç: {len(results)}")
            if results:
                print(f"En iyi eşleşme: {results[0].get('title', 'N/A')}")
        else:
            print("\n⚠️  Henüz içerik yok. Önce film/TV dizisi ekleyin.")
        
        print("\n✅ Hızlı test tamamlandı!")
        
    except Exception as e:
        logger.error(f"Test sırasında hata: {str(e)}")
        print(f"❌ Hata: {str(e)}")

if __name__ == "__main__":
    quick_test() 