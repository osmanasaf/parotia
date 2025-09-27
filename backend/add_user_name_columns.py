import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import engine
from sqlalchemy import text

def add_user_name_columns():
    """Users tablosuna first_name ve last_name kolonlarını ekler (varsa atlar)"""
    try:
        with engine.connect() as conn:
            columns_to_add = [
                "first_name VARCHAR",
                "last_name VARCHAR"
            ]

            for column_def in columns_to_add:
                try:
                    column_name = column_def.split()[0]
                    check_query = text(f"""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'users' 
                        AND column_name = '{column_name}'
                    """)
                    result = conn.execute(check_query)
                    if not result.fetchone():
                        alter_query = text(f"ALTER TABLE users ADD COLUMN {column_def}")
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
    add_user_name_columns()




