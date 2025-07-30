import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import engine, Base
from app.models import *
from sqlalchemy import text

def clean_database():
    """Drop all tables and recreate them"""
    try:
        # Drop all tables
        with engine.connect() as connection:
            connection.execute(text("DROP TABLE IF EXISTS users CASCADE"))
            connection.execute(text("DROP TABLE IF EXISTS movies CASCADE"))
            connection.execute(text("DROP TABLE IF EXISTS comments CASCADE"))
            connection.execute(text("DROP TABLE IF EXISTS watchlists CASCADE"))
            connection.execute(text("DROP TABLE IF EXISTS recommendation_feedbacks CASCADE"))
            connection.execute(text("DROP TABLE IF EXISTS email_verifications CASCADE"))
            connection.commit()
            print("✅ All tables dropped successfully")
        
        # Recreate tables
        Base.metadata.create_all(bind=engine)
        print("✅ All tables recreated successfully")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    clean_database() 