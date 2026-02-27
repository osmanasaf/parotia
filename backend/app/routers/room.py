import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.exceptions import BaseAppException
from app.db import get_db
from app.models.room import Room, RoomAction, RoomStatus
from app.schemas.room import RoomCreate, RoomResponse
from app.services.room_service import RoomService

router = APIRouter(prefix="/rooms", tags=["Movie Room"])
logger = logging.getLogger(__name__)


def handle_exception(e: Exception) -> HTTPException:
    """Convert domain exceptions to HTTP responses."""
    if isinstance(e, BaseAppException):
        return HTTPException(status_code=e.status_code, detail=e.message)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An internal server error occurred",
    )


class ConnectionManager:
    """Manages active WebSocket connections grouped by room code."""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_code: str):
        await websocket.accept()
        self.active_connections.setdefault(room_code, []).append(websocket)

    def disconnect(self, websocket: WebSocket, room_code: str):
        connections = self.active_connections.get(room_code)
        if connections and websocket in connections:
            connections.remove(websocket)
            if not connections:
                del self.active_connections[room_code]

    async def broadcast(self, room_code: str, message: dict):
        for connection in self.active_connections.get(room_code, []):
            try:
                await connection.send_json(message)
            except Exception:
                logger.warning("Failed to send message to a WebSocket client")

    async def close_room(self, room_code: str):
        for connection in self.active_connections.get(room_code, []):
            try:
                await connection.close()
            except Exception:
                pass
        self.active_connections.pop(room_code, None)


manager = ConnectionManager()


@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def create_room(
    room_data: RoomCreate,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user),
):
    try:
        service = RoomService(db)
        room = service.create_room(
            creator_id=current_user_id,
            creator_session_id=room_data.creator_session_id,
            content_type=room_data.content_type,
            duration=room_data.duration_minutes,
            max_participants=room_data.max_participants,
        )
        return room
    except Exception as e:
        raise handle_exception(e)


@router.get("/", response_model=List[RoomResponse])
def get_my_rooms(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user),
):
    """Get all rooms created by the logged-in user."""
    rooms = db.query(Room).filter(Room.creator_id == current_user_id).order_by(Room.created_at.desc()).all()
    return rooms


@router.get("/{code}", response_model=RoomResponse)
def get_room(code: str, db: Session = Depends(get_db)):
    try:
        service = RoomService(db)
        return service.get_room_by_code(code)
    except Exception as e:
        raise handle_exception(e)


@router.websocket("/{code}/ws")
async def room_websocket(
    websocket: WebSocket, code: str, session_id: str, db: Session = Depends(get_db)
):
    if not session_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    service = RoomService(db)

    try:
        room = service.join_or_rejoin_room(session_id, code)
    except BaseAppException as e:
        await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
        return

    await manager.connect(websocket, code)

    await manager.broadcast(code, {
        "type": "user_joined",
        "session_id": session_id,
        "participants_count": len(room.participants),
    })

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "detail": "Invalid JSON"})
                continue

            msg_type = message.get("type")

            if msg_type == "submit_mood":
                await _handle_submit_mood(service, code, session_id, message, manager)

            elif msg_type == "swipe":
                await _handle_swipe(service, code, session_id, message, manager)

            elif msg_type == "force_start":
                await _handle_force_start(service, code, session_id, manager)

            elif msg_type == "force_finish":
                await _handle_force_finish(service, code, session_id, manager)

            else:
                await websocket.send_json({"type": "error", "detail": "Unknown message type"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, code)
        await manager.broadcast(code, {"type": "user_left", "session_id": session_id})
    except Exception as e:
        logger.error(f"WebSocket error in room {code}: {e}")
        manager.disconnect(websocket, code)


async def _handle_submit_mood(
    service: RoomService, code: str, session_id: str, message: dict, mgr: ConnectionManager
):
    mood_text = message.get("text", "").strip()
    if not mood_text:
        return

    room = service.submit_mood(session_id, code, mood_text)
    all_ready = room.are_all_participants_ready()

    await mgr.broadcast(code, {
        "type": "user_ready",
        "session_id": session_id,
        "all_ready": all_ready,
        "ready_count": room.get_ready_count(),
        "total_count": room.get_total_count(),
    })

    if all_ready:
        recommendations = await service.start_voting_session(room)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=room.duration_minutes)

        await mgr.broadcast(code, {
            "type": "start_voting",
            "recommendations": recommendations,
            "expires_at": expires_at.isoformat(),
        })


async def _handle_swipe(
    service: RoomService, code: str, session_id: str, message: dict, mgr: ConnectionManager
):
    tmdb_id = message.get("tmdb_id")
    action_str = message.get("action", "").upper()

    if not tmdb_id:
        return

    try:
        action = RoomAction[action_str]
    except KeyError:
        return

    match, all_done = service.record_swipe(session_id, code, tmdb_id, action)

    if match:
        await mgr.broadcast(code, {
            "type": "match_found",
            "tmdb_id": tmdb_id,
        })

    if all_done:
        await _finish_room_and_broadcast(service, code, mgr)

async def _handle_force_start(
    service: RoomService, code: str, session_id: str, mgr: ConnectionManager
):
    """Creator starts voting without waiting for all participants."""
    try:
        recommendations = await service.force_start_voting(session_id, code)
        room = service.get_room_by_code(code)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=room.duration_minutes)

        await mgr.broadcast(code, {
            "type": "start_voting",
            "recommendations": recommendations,
            "expires_at": expires_at.isoformat(),
        })
    except BaseAppException as e:
        await mgr.broadcast(code, {"type": "error", "detail": e.message})


async def _handle_force_finish(
    service: RoomService, code: str, session_id: str, mgr: ConnectionManager
):
    """Creator ends voting early, best match is calculated from existing votes."""
    try:
        best_matches = service.force_finish_room(session_id, code)

        if best_matches:
            await mgr.broadcast(code, {
                "type": "voting_finished",
                "matches": [{"tmdb_id": m.tmdb_id} for m in best_matches]
            })
        else:
            await mgr.broadcast(code, {
                "type": "voting_finished",
                "matches": [],
                "detail": "No positive votes were cast",
            })

        # Sonuçların istemciye ulaşması için kısa bekleme, ardından bağlantıları kapat
        await asyncio.sleep(0.5)
        await mgr.close_room(code)
    except BaseAppException as e:
        await mgr.broadcast(code, {"type": "error", "detail": e.message})


async def _finish_room_and_broadcast(service: RoomService, code: str, mgr: ConnectionManager):
    """Tüm swipe'lar tamamlandığında odayı bitir ve sonuçları yayınla."""
    try:
        room = service.get_room_by_code(code)
        if room.status != RoomStatus.VOTING:
            return

        best_matches = service._calculate_top_matches(room)
        service.finish_room(room)

        if best_matches:
            await mgr.broadcast(code, {
                "type": "voting_finished",
                "matches": [{"tmdb_id": m.tmdb_id} for m in best_matches]
            })
        else:
            await mgr.broadcast(code, {
                "type": "voting_finished",
                "matches": [],
                "detail": "No positive votes were cast",
            })

        await asyncio.sleep(0.5)
        await mgr.close_room(code)
    except Exception as e:
        logger.error(f"Error finishing room {code}: {e}")
