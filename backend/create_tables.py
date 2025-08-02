import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import engine, Base
# Tüm modelleri tek seferde import et
from app.models import *

def main():
    """Tüm veritabanı tablolarını oluşturur"""
    Base.metadata.create_all(bind=engine)
    print("Tüm tablolar başarıyla oluşturuldu.")

if __name__ == "__main__":
    main() 