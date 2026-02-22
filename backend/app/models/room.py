from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base
import enum


class RoomStatus(enum.Enum):
    WAITING = "waiting"
    VOTING = "voting"
    FINISHED = "finished"


class ContentType(enum.Enum):
    MOVIE = "movie"
    TV = "tv"
    MIXED = "mixed"


class RoomAction(enum.Enum):
    LIKE = "like"
    DISLIKE = "dislike"
    SUPERLIKE = "superlike"


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(6), unique=True, index=True, nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(RoomStatus), default=RoomStatus.WAITING, nullable=False)
    content_type = Column(Enum(ContentType), default=ContentType.MIXED, nullable=False)
    max_participants = Column(Integer, default=5, nullable=False)
    duration_minutes = Column(Integer, default=5, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    participants = relationship("RoomParticipant", back_populates="room", cascade="all, delete-orphan")
    interactions = relationship("RoomInteraction", back_populates="room", cascade="all, delete-orphan")
    matches = relationship("RoomMatch", back_populates="room", cascade="all, delete-orphan")

    def is_joinable(self) -> bool:
        return self.status == RoomStatus.WAITING and len(self.participants) < self.max_participants

    def are_all_participants_ready(self) -> bool:
        return bool(self.participants) and all(p.is_ready for p in self.participants)

    def start_voting(self):
        self.status = RoomStatus.VOTING

    def finish(self):
        self.status = RoomStatus.FINISHED


class RoomParticipant(Base):
    __tablename__ = "room_participants"
    __table_args__ = (
        UniqueConstraint("room_id", "user_id", name="uq_room_participant"),
    )

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    mood = Column(String, nullable=True)
    is_ready = Column(Boolean, default=False, nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    room = relationship("Room", back_populates="participants")
    user = relationship("User")

    def submit_mood(self, mood: str):
        self.mood = mood
        self.is_ready = True


class RoomInteraction(Base):
    __tablename__ = "room_interactions"
    __table_args__ = (
        UniqueConstraint("room_id", "user_id", "tmdb_id", name="uq_room_user_content"),
    )

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tmdb_id = Column(Integer, nullable=False)
    action = Column(Enum(RoomAction), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    room = relationship("Room", back_populates="interactions")


class RoomMatch(Base):
    __tablename__ = "room_matches"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    tmdb_id = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    room = relationship("Room", back_populates="matches")
