import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Doğrudan DATABASE_URL tanımla (geliştirme ortamı için)
DATABASE_URL = "postgresql+psycopg2://postgres:asdqwe123!.@localhost:5432/parotia_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base() 