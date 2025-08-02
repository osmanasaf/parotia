import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import engine
from sqlalchemy import text

def add_watchlist_columns():
    """UserWatchlist tablosuna eksik kolonları ekler"""
    try:
        with engine.connect() as conn:
            # Eksik kolonları ekle
            columns_to_add = [
                "source VARCHAR",
                "notification_sent BOOLEAN DEFAULT FALSE",
                "notification_sent_at TIMESTAMP WITH TIME ZONE",
                "feedback_provided BOOLEAN DEFAULT FALSE", 
                "feedback_provided_at TIMESTAMP WITH TIME ZONE"
            ]
            
            for column_def in columns_to_add:
                try:
                    # Kolon adını çıkar
                    column_name = column_def.split()[0]
                    
                    # Kolon var mı kontrol et
                    check_query = text(f"""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'user_watchlists' 
                        AND column_name = '{column_name}'
                    """)
                    
                    result = conn.execute(check_query)
                    if not result.fetchone():
                        # Kolon yoksa ekle
                        alter_query = text(f"ALTER TABLE user_watchlists ADD COLUMN {column_def}")
                        conn.execute(alter_query)
                        print(f"✅ {column_name} kolonu eklendi")
                    else:
                        print(f"ℹ️ {column_name} kolonu zaten mevcut")
                        
                except Exception as e:
                    print(f"❌ {column_def} eklenirken hata: {str(e)}")
            
            conn.commit()
            print("🎉 Migration tamamlandı!")
            
    except Exception as e:
        print(f"❌ Migration hatası: {str(e)}")

if __name__ == "__main__":
    add_watchlist_columns() 