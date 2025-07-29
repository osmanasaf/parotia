import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import engine, Base
# Tüm modelleri tek seferde import et
from app.models import *

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("All tables created successfully.") 