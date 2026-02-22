import logging
import random
import string
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.room import (
    Room, RoomParticipant, RoomInteraction, RoomMatch,
    RoomStatus, RoomAction, ContentType,
)
from app.services.embedding_service import EmbeddingService
from app.core.exceptions import (
    RoomNotFoundException,
    RoomFullException,
    RoomAlreadyStartedException,
    InvalidRoomActionException,
)

logger = logging.getLogger(__name__)

ROOM_CODE_LENGTH = 6
RECOMMENDATION_COUNT = 20


class RoomService:
    """Application service that orchestrates Room lifecycle and recommendation fetching."""

    def __init__(self, db: Session):
        self.db = db
        self.embedding_service = EmbeddingService()

    def create_room(
        self,
        creator_id: int,
        content_type: ContentType = ContentType.MIXED,
        duration: int = 5,
        max_participants: int = 5,
    ) -> Room:
        """Create a new room and add the creator as the first participant."""
        room_code = self._generate_unique_code()

        room = Room(
            code=room_code,
            creator_id=creator_id,
            content_type=content_type,
            duration_minutes=duration,
            max_participants=max_participants,
            status=RoomStatus.WAITING,
        )
        self.db.add(room)
        self.db.commit()
        self.db.refresh(room)

        self._add_participant(room, creator_id)
        return room

    def join_room(self, user_id: int, room_code: str) -> Room:
        """Add a user to a room. Raises domain exceptions on failure."""
        room = self._get_room_or_raise(room_code)

        if room.status != RoomStatus.WAITING:
            raise RoomAlreadyStartedException()

        existing = self.db.query(RoomParticipant).filter(
            RoomParticipant.room_id == room.id,
            RoomParticipant.user_id == user_id,
        ).first()

        if existing:
            return room

        if not room.is_joinable():
            raise RoomFullException()

        self._add_participant(room, user_id)
        return room

    def submit_mood(self, user_id: int, room_code: str, mood: str) -> Room:
        """Record a participant's mood and mark them as ready."""
        room = self._get_room_or_raise(room_code)
        participant = self._get_participant_or_raise(room.id, user_id)

        participant.submit_mood(mood)
        self.db.commit()
        self.db.refresh(room)
        return room

    def start_voting_session(self, room: Room) -> List[Dict[str, Any]]:
        """Transition room to VOTING and return recommendations."""
        room.start_voting()
        self.db.commit()

        return self._fetch_recommendations(room)

    def record_swipe(
        self, user_id: int, room_code: str, tmdb_id: int, action: RoomAction
    ) -> Optional[RoomMatch]:
        """Record a swipe action and check for a unanimous match."""
        room = self._get_room_or_raise(room_code)

        interaction = RoomInteraction(
            room_id=room.id,
            user_id=user_id,
            tmdb_id=tmdb_id,
            action=action,
        )
        self.db.add(interaction)
        self.db.commit()

        if action in (RoomAction.LIKE, RoomAction.SUPERLIKE):
            return self._check_for_match(room, tmdb_id)

        return None

    def finish_room(self, room: Room):
        """Mark the room as finished."""
        room.finish()
        self.db.commit()

    def get_room_by_code(self, room_code: str) -> Room:
        return self._get_room_or_raise(room_code)

    # ── Private helpers ──────────────────────────────────────────

    def _generate_unique_code(self) -> str:
        for _ in range(10):
            code = "".join(
                random.choices(string.ascii_uppercase + string.digits, k=ROOM_CODE_LENGTH)
            )
            exists = (
                self.db.query(Room)
                .filter(Room.code == code, Room.status != RoomStatus.FINISHED)
                .first()
            )
            if not exists:
                return code
        raise InvalidRoomActionException("Could not generate a unique room code")

    def _get_room_or_raise(self, room_code: str) -> Room:
        room = self.db.query(Room).filter(Room.code == room_code).first()
        if not room:
            raise RoomNotFoundException()
        return room

    def _get_participant_or_raise(self, room_id: int, user_id: int) -> RoomParticipant:
        participant = self.db.query(RoomParticipant).filter(
            RoomParticipant.room_id == room_id,
            RoomParticipant.user_id == user_id,
        ).first()
        if not participant:
            raise InvalidRoomActionException("User is not a participant in this room")
        return participant

    def _add_participant(self, room: Room, user_id: int):
        participant = RoomParticipant(room_id=room.id, user_id=user_id)
        self.db.add(participant)
        self.db.commit()
        self.db.refresh(room)

    def _fetch_recommendations(self, room: Room) -> List[Dict[str, Any]]:
        moods = [p.mood for p in room.participants if p.mood]
        if not moods:
            return []

        combined_mood = " ".join(moods)
        content_type_filter = room.content_type.value if room.content_type != ContentType.MIXED else None

        recommendations = self.embedding_service.search_similar_content(
            query_text=combined_mood,
            top_k=RECOMMENDATION_COUNT,
            content_type=content_type_filter,
        )

        return self._sanitize_recommendations(recommendations)

    def _check_for_match(self, room: Room, tmdb_id: int) -> Optional[RoomMatch]:
        liked_user_ids = {
            row[0]
            for row in self.db.query(RoomInteraction.user_id)
            .filter(
                RoomInteraction.room_id == room.id,
                RoomInteraction.tmdb_id == tmdb_id,
                RoomInteraction.action.in_([RoomAction.LIKE, RoomAction.SUPERLIKE]),
            )
            .distinct()
            .all()
        }

        participant_user_ids = {p.user_id for p in room.participants}

        if participant_user_ids.issubset(liked_user_ids):
            match = RoomMatch(room_id=room.id, tmdb_id=tmdb_id)
            self.db.add(match)
            self.db.commit()
            self.db.refresh(match)
            return match

        return None

    @staticmethod
    def _sanitize_recommendations(recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove internal fields like embedding_vector before sending to clients."""
        sanitized = []
        for rec in recommendations:
            clean = {k: v for k, v in rec.items() if k != "embedding_vector"}
            sanitized.append(clean)
        return sanitized
