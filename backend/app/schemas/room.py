from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from app.models.room import RoomStatus, RoomAction, ContentType


class RoomCreate(BaseModel):
    content_type: ContentType = ContentType.MIXED
    max_participants: int = Field(default=5, ge=2, le=5)
    duration_minutes: int = Field(default=5, ge=1, le=30)


class RoomParticipantResponse(BaseModel):
    user_id: int
    mood: Optional[str] = None
    is_ready: bool = False

    class Config:
        from_attributes = True


class RoomResponse(BaseModel):
    id: int
    code: str
    creator_id: int
    status: RoomStatus
    content_type: ContentType
    max_participants: int
    duration_minutes: int
    created_at: datetime
    participants: List[RoomParticipantResponse]

    class Config:
        from_attributes = True


class RoomSwipe(BaseModel):
    tmdb_id: int = Field(gt=0)
    action: RoomAction


class MoodSubmission(BaseModel):
    text: str = Field(min_length=3, max_length=500)


class RoomMatchResponse(BaseModel):
    tmdb_id: int
    matched_at: datetime

    class Config:
        from_attributes = True
