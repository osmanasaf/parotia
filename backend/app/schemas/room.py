from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from app.models.room import RoomStatus, RoomAction, ContentType


class RoomCreate(BaseModel):
    creator_session_id: str = Field(..., min_length=1, description="Unique session ID for the creator")
    content_type: ContentType = ContentType.MIXED
    max_participants: int = Field(default=5, ge=2, le=5)
    duration_minutes: int = Field(default=5, ge=1, le=30)


class RoomParticipantResponse(BaseModel):
    session_id: str
    user_id: Optional[int] = None
    mood: Optional[str] = None
    is_ready: bool = False

    class Config:
        from_attributes = True


class RoomMatchResponse(BaseModel):
    tmdb_id: int
    matched_at: datetime

    class Config:
        from_attributes = True


class RoomResponse(BaseModel):
    id: int
    code: str
    creator_id: int
    creator_session_id: str
    status: RoomStatus
    content_type: ContentType
    max_participants: int
    duration_minutes: int
    created_at: datetime
    participants: List[RoomParticipantResponse]
    matches: List[RoomMatchResponse] = []

    class Config:
        from_attributes = True


class RoomSwipe(BaseModel):
    tmdb_id: int = Field(gt=0)
    action: RoomAction


class MoodSubmission(BaseModel):
    text: str = Field(min_length=3, max_length=500)

