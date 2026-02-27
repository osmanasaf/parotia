import asyncio
import logging
import random
import string
from typing import List, Optional, Dict, Any, Tuple
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
from datetime import datetime, timezone, timedelta

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
        creator_session_id: str,
        content_type: ContentType = ContentType.MIXED,
        duration: int = 5,
        max_participants: int = 5,
    ) -> Room:
        """Create a new room and add the creator as the first participant."""
        room_code = self._generate_unique_code()

        room = Room(
            code=room_code,
            creator_id=creator_id,
            creator_session_id=creator_session_id,
            content_type=content_type,
            duration_minutes=duration,
            max_participants=max_participants,
            status=RoomStatus.WAITING,
        )
        self.db.add(room)
        self.db.commit()
        self.db.refresh(room)

        self._add_participant(room, creator_session_id)
        return room

    def join_room(self, session_id: str, room_code: str) -> Room:
        """Add a user to a room. Raises domain exceptions on failure."""
        room = self._get_room_or_raise(room_code)

        if room.status != RoomStatus.WAITING:
            raise RoomAlreadyStartedException()

        existing = self.db.query(RoomParticipant).filter(
            RoomParticipant.room_id == room.id,
            RoomParticipant.session_id == session_id,
        ).first()

        if existing:
            return room

        if not room.is_joinable():
            raise RoomFullException()

        self._add_participant(room, session_id)
        return room

    def join_or_rejoin_room(self, session_id: str, room_code: str) -> Room:
        """Add a user to a room or allow reconnect to an active VOTING room."""
        room = self._get_room_or_raise(room_code)

        existing = self.db.query(RoomParticipant).filter(
            RoomParticipant.room_id == room.id,
            RoomParticipant.session_id == session_id,
        ).first()

        if existing:
            return room

        if room.status == RoomStatus.FINISHED:
            raise InvalidRoomActionException("Room has already finished")

        if room.status == RoomStatus.VOTING:
            raise RoomAlreadyStartedException()

        if not room.is_joinable():
            raise RoomFullException()

        self._add_participant(room, session_id)
        return room

    def submit_mood(self, session_id: str, room_code: str, mood: str) -> Room:
        """Record a participant's mood and mark them as ready."""
        room = self._get_room_or_raise(room_code)
        participant = self._get_participant_or_raise(room.id, session_id)

        participant.submit_mood(mood)
        self.db.commit()
        self.db.refresh(room)
        return room

    async def start_voting_session(self, room: Room) -> List[Dict[str, Any]]:
        """Transition room to VOTING and return recommendations."""
        room.start_voting()
        self.db.commit()

        return await self._fetch_recommendations_async(room)

    def record_swipe(
        self, session_id: str, room_code: str, tmdb_id: int, action: RoomAction
    ) -> Tuple[Optional[RoomMatch], bool]:
        """Record a swipe action and check for a unanimous match.

        Returns (match_or_None, all_participants_done).
        all_participants_done is True when every participant has swiped every recommendation.
        """
        room = self._get_room_or_raise(room_code)

        existing_interaction = self.db.query(RoomInteraction).filter(
            RoomInteraction.room_id == room.id,
            RoomInteraction.session_id == session_id,
            RoomInteraction.tmdb_id == tmdb_id,
        ).first()

        if not existing_interaction:
            interaction = RoomInteraction(
                room_id=room.id,
                session_id=session_id,
                tmdb_id=tmdb_id,
                action=action,
            )
            self.db.add(interaction)
            self.db.commit()

        match = None
        if action in (RoomAction.LIKE, RoomAction.SUPERLIKE):
            match = self._check_for_match(room, tmdb_id)

        all_done = self._have_all_participants_finished_swiping(room)
        return match, all_done

    async def force_start_voting(self, session_id: str, room_code: str) -> List[Dict[str, Any]]:
        """Allow the room creator to start voting even if not all participants joined."""
        room = self._get_room_or_raise(room_code)

        if not room.is_creator(session_id):
            raise InvalidRoomActionException("Only the room creator can force start")

        if room.status != RoomStatus.WAITING:
            raise RoomAlreadyStartedException()

        if not room.has_any_ready_participant():
            raise InvalidRoomActionException("At least one participant must submit a mood before starting")

        return await self.start_voting_session(room)

    def force_finish_room(self, session_id: str, room_code: str) -> List[RoomMatch]:
        """Allow the room creator to end voting early and get the top ranked matches."""
        room = self._get_room_or_raise(room_code)

        if not room.is_creator(session_id):
            raise InvalidRoomActionException("Only the room creator can force finish")

        if room.status != RoomStatus.VOTING:
            raise InvalidRoomActionException("Room is not in voting state")

        best_matches = self._calculate_top_matches(room)
        self.finish_room(room)
        return best_matches

    def finish_room(self, room: Room):
        """Mark the room as finished."""
        room.finish()
        self.db.commit()

    def get_room_by_code(self, room_code: str) -> Room:
        return self._get_room_or_raise(room_code)

    def cleanup_expired_rooms(self, minutes_old: int = 30):
        """Delete inactive rooms or purge session data for finished rooms."""
        threshold = datetime.now(timezone.utc) - timedelta(minutes=minutes_old)

        # 1. Clean WAITING/VOTING rooms that are abandoned (delete entirely)
        abandoned_rooms = self.db.query(Room).filter(
            Room.status.in_([RoomStatus.WAITING, RoomStatus.VOTING]),
            Room.created_at < threshold
        ).all()
        for r in abandoned_rooms:
            self.db.delete(r)

        # 2. Clean FINISHED rooms (keep Room & RoomMatch, delete participants/interactions to save space)
        finished_rooms = self.db.query(Room).filter(
            Room.status == RoomStatus.FINISHED,
            Room.created_at < threshold
        ).all()
        
        for r in finished_rooms:
            self.db.query(RoomParticipant).filter(RoomParticipant.room_id == r.id).delete()
            self.db.query(RoomInteraction).filter(RoomInteraction.room_id == r.id).delete()

        self.db.commit()

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

    def _get_participant_or_raise(self, room_id: int, session_id: str) -> RoomParticipant:
        participant = self.db.query(RoomParticipant).filter(
            RoomParticipant.room_id == room_id,
            RoomParticipant.session_id == session_id,
        ).first()
        if not participant:
            raise InvalidRoomActionException("User is not a participant in this room")
        return participant

    def _add_participant(self, room: Room, session_id: str):
        participant = RoomParticipant(room_id=room.id, session_id=session_id)
        self.db.add(participant)
        self.db.commit()
        self.db.refresh(room)

    async def _fetch_recommendations_async(self, room: Room) -> List[Dict[str, Any]]:
        """Individual + Joker Pooling Strategy — paralel embedding aramaları."""
        moods = [p.mood for p in room.participants if p.mood]
        if not moods:
            return []

        content_type_filter = room.content_type.value if room.content_type != ContentType.MIXED else None

        loop = asyncio.get_event_loop()

        def search(query: str, top_k: int) -> List[Dict[str, Any]]:
            return self.embedding_service.search_similar_content(
                query_text=query,
                top_k=top_k,
                content_type=content_type_filter,
            )

        queries = [(mood, 10) for mood in moods]
        queries.append(("popular award winning masterpiece highly rated best", 5))

        results = await asyncio.gather(
            *[loop.run_in_executor(None, search, q, k) for q, k in queries]
        )

        all_recommendations: Dict[int, Dict[str, Any]] = {}
        for recs in results:
            for rec in recs:
                if rec["id"] not in all_recommendations:
                    all_recommendations[rec["id"]] = rec

        final_pool = list(all_recommendations.values())
        random.shuffle(final_pool)
        final_pool = final_pool[:RECOMMENDATION_COUNT]

        return self._sanitize_recommendations(final_pool)

    def _check_for_match(self, room: Room, tmdb_id: int) -> Optional[RoomMatch]:
        liked_session_ids = {
            row[0]
            for row in self.db.query(RoomInteraction.session_id)
            .filter(
                RoomInteraction.room_id == room.id,
                RoomInteraction.tmdb_id == tmdb_id,
                RoomInteraction.action.in_([RoomAction.LIKE, RoomAction.SUPERLIKE]),
            )
            .distinct()
            .all()
        }

        participant_session_ids = {p.session_id for p in room.participants}

        if not participant_session_ids.issubset(liked_session_ids):
            return None

        existing_match = self.db.query(RoomMatch).filter(
            RoomMatch.room_id == room.id,
            RoomMatch.tmdb_id == tmdb_id,
        ).first()
        if existing_match:
            return existing_match

        match = RoomMatch(room_id=room.id, tmdb_id=tmdb_id)
        self.db.add(match)
        self.db.commit()
        self.db.refresh(match)
        return match

    def _have_all_participants_finished_swiping(self, room: Room) -> bool:
        """Return True if every participant has swiped every recommendation in this room."""
        if room.status != RoomStatus.VOTING:
            return False

        participant_ids = {p.session_id for p in room.participants}
        if not participant_ids:
            return False

        swiped_tmdb_ids_per_participant: Dict[str, set] = {sid: set() for sid in participant_ids}

        interactions = (
            self.db.query(RoomInteraction.session_id, RoomInteraction.tmdb_id)
            .filter(RoomInteraction.room_id == room.id)
            .all()
        )
        for session_id, tmdb_id in interactions:
            if session_id in swiped_tmdb_ids_per_participant:
                swiped_tmdb_ids_per_participant[session_id].add(tmdb_id)

        all_tmdb_ids = set()
        for tmdb_ids in swiped_tmdb_ids_per_participant.values():
            all_tmdb_ids |= tmdb_ids

        if not all_tmdb_ids:
            return False

        return all(
            all_tmdb_ids.issubset(swiped)
            for swiped in swiped_tmdb_ids_per_participant.values()
        )

    @staticmethod
    def _sanitize_recommendations(recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove internal fields like embedding_vector before sending to clients."""
        sanitized = []
        for rec in recommendations:
            clean = {k: v for k, v in rec.items() if k != "embedding_vector"}
            sanitized.append(clean)
        return sanitized

    def _calculate_top_matches(self, room: Room, top_k: int = 5) -> List[RoomMatch]:
        """Find the contents with the highest combined score across all participants.

        Scoring: SUPERLIKE = 3 points, LIKE = 1 point, DISLIKE = 0.
        """
        positive_interactions = (
            self.db.query(RoomInteraction)
            .filter(
                RoomInteraction.room_id == room.id,
                RoomInteraction.action.in_([RoomAction.LIKE, RoomAction.SUPERLIKE]),
            )
            .all()
        )

        if not positive_interactions:
            return []

        scores: Dict[int, int] = {}
        for interaction in positive_interactions:
            weight = 3 if interaction.action == RoomAction.SUPERLIKE else 1
            scores[interaction.tmdb_id] = scores.get(interaction.tmdb_id, 0) + weight

        # Sort by score descending
        sorted_tmdb_ids = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_tmdb_ids = [k for k, v in sorted_tmdb_ids[:top_k]]

        matches = []
        for tmdb_id in top_tmdb_ids:
            match = RoomMatch(room_id=room.id, tmdb_id=tmdb_id)
            self.db.add(match)
            matches.append(match)
            
        self.db.commit()
        for match in matches:
            self.db.refresh(match)
            
        return matches
