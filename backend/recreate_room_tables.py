from app.db import engine
from sqlalchemy import text

def add_columns():
    with engine.connect() as conn:
        try:
            # Drop old tables to avoid conflicts for this specific feature 
            # (since it's a new feature, wiping its tables is safe and ensures clean schema)
            print("Dropping old room tables...")
            conn.execute(text("DROP TABLE IF EXISTS room_matches CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS room_interactions CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS room_participants CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS rooms CASCADE;"))
            conn.commit()
            print("Room tables dropped. The app will auto-create them on next run or when Base.metadata.create_all is called.")
            
        except Exception as e:
            print(f"Error dropping columns: {e}")
            conn.rollback()

if __name__ == "__main__":
    add_columns()
    
    # Recreate tables immediately
    from app.db import Base
    import app.models.room  # import to register
    Base.metadata.create_all(bind=engine)
    print("Room tables recreated with latest schema.")
