import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import engine
from sqlalchemy import text

def recreate_watchlist_table():
    """UserWatchlist tablosunu silip yeniden oluşturur"""
    try:
        with engine.connect() as conn:
            # Önce tabloyu sil
            print("��️ Eski tablo siliniyor...")
            drop_query = text("DROP TABLE IF EXISTS user_watchlists CASCADE")
            conn.execute(drop_query)
            
            # Yeni tabloyu oluştur
            print("🏗️ Yeni tablo oluşturuluyor...")
            create_query = text("""
                CREATE TABLE user_watchlists (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    tmdb_id INTEGER NOT NULL,
                    content_type VARCHAR NOT NULL,
                    status VARCHAR NOT NULL,
                    from_recommendation BOOLEAN DEFAULT FALSE,
                    recommendation_id INTEGER REFERENCES user_recommendations(id),
                    recommendation_type VARCHAR,
                    recommendation_score FLOAT,
                    source VARCHAR,
                    notification_sent BOOLEAN DEFAULT FALSE,
                    notification_sent_at TIMESTAMP WITH TIME ZONE,
                    feedback_provided BOOLEAN DEFAULT FALSE,
                    feedback_provided_at TIMESTAMP WITH TIME ZONE,
                    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE
                )
            """)
            conn.execute(create_query)
            
            # Index'leri oluştur
            print("📊 Index'ler oluşturuluyor...")
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_user_watchlists_user_id ON user_watchlists(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_user_watchlists_tmdb_id ON user_watchlists(tmdb_id)",
                "CREATE INDEX IF NOT EXISTS idx_user_watchlists_from_recommendation ON user_watchlists(from_recommendation)"
            ]
            
            for index_query in indexes:
                conn.execute(text(index_query))
            
            conn.commit()
            print("🎉 UserWatchlist tablosu başarıyla yeniden oluşturuldu!")
            
    except Exception as e:
        print(f"❌ Hata: {str(e)}")

if __name__ == "__main__":
    recreate_watchlist_table() 