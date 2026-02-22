import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, verify_token
from app.core.exceptions import BaseAppException
from app.db import get_db
from app.models.room import RoomAction
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
            content_type=room_data.content_type,
            duration=room_data.duration_minutes,
            max_participants=room_data.max_participants,
        )
        return room
    except Exception as e:
        raise handle_exception(e)


@router.get("/{code}", response_model=RoomResponse)
def get_room(code: str, db: Session = Depends(get_db)):
    try:
        service = RoomService(db)
        return service.get_room_by_code(code)
    except Exception as e:
        raise handle_exception(e)


@router.websocket("/{code}/ws")
async def room_websocket(
    websocket: WebSocket, code: str, token: str, db: Session = Depends(get_db)
):
    payload = verify_token(token)
    if not payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = payload.get("sub")
    service = RoomService(db)

    try:
        room = service.join_room(user_id, code)
    except BaseAppException:
        await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
        return

    await manager.connect(websocket, code)

    await manager.broadcast(code, {
        "type": "user_joined",
        "user_id": user_id,
        "participants_count": len(room.participants),
    })

    try:
        while True:
            raw = await websocket.receive_text()
            message = json.loads(raw)
            msg_type = message.get("type")

            if msg_type == "submit_mood":
                await _handle_submit_mood(service, code, user_id, message, manager)

            elif msg_type == "swipe":
                await _handle_swipe(service, code, user_id, message, manager)

            elif msg_type == "force_start":
                await _handle_force_start(service, code, user_id, manager)

            elif msg_type == "force_finish":
                await _handle_force_finish(service, code, user_id, manager)

            else:
                await websocket.send_json({"type": "error", "detail": "Unknown message type"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, code)
        await manager.broadcast(code, {"type": "user_left", "user_id": user_id})
    except Exception as e:
        logger.error(f"WebSocket error in room {code}: {e}")
        manager.disconnect(websocket, code)


async def _handle_submit_mood(
    service: RoomService, code: str, user_id: int, message: dict, mgr: ConnectionManager
):
    mood_text = message.get("text", "").strip()
    if not mood_text:
        return

    room = service.submit_mood(user_id, code, mood_text)
    all_ready = room.are_all_participants_ready()

    await mgr.broadcast(code, {
        "type": "user_ready",
        "user_id": user_id,
        "all_ready": all_ready,
    })

    if all_ready:
        recommendations = service.start_voting_session(room)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=room.duration_minutes)

        await mgr.broadcast(code, {
            "type": "start_voting",
            "recommendations": recommendations,
            "expires_at": expires_at.isoformat(),
        })


async def _handle_swipe(
    service: RoomService, code: str, user_id: int, message: dict, mgr: ConnectionManager
):
    tmdb_id = message.get("tmdb_id")
    action_str = message.get("action", "").upper()

    try:
        action = RoomAction[action_str]
    except KeyError:
        return

    match = service.record_swipe(user_id, code, tmdb_id, action)

    if match:
        room = service.get_room_by_code(code)
        service.finish_room(room)

        await mgr.broadcast(code, {
            "type": "match_found",
            "tmdb_id": tmdb_id,
        })

        await mgr.close_room(code)


async def _handle_force_start(
    service: RoomService, code: str, user_id: int, mgr: ConnectionManager
):
    """Creator starts voting without waiting for all participants."""
    try:
        recommendations = service.force_start_voting(user_id, code)
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
    service: RoomService, code: str, user_id: int, mgr: ConnectionManager
):
    """Creator ends voting early, best match is calculated from existing votes."""
    try:
        best_match = service.force_finish_room(user_id, code)

        if best_match:
            await mgr.broadcast(code, {
                "type": "match_found",
                "tmdb_id": best_match.tmdb_id,
            })
        else:
            await mgr.broadcast(code, {
                "type": "no_match",
                "detail": "No positive votes were cast",
            })

        await mgr.close_room(code)
    except BaseAppException as e:
        await mgr.broadcast(code, {"type": "error", "detail": e.message})
