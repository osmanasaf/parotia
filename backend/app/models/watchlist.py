from sqlalchemy import Column, Integer, ForeignKey, String
from app.db import Base

class Watchlist(Base):
    __tablename__ = "watchlists"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    status = Column(String, nullable=False)  # e.g. 'watched', 'to_watch' 