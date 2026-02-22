from app.db import SessionLocal
from app.services.room_service import RoomService
from app.models.room import RoomAction, RoomStatus
import uuid

def main():
    db = SessionLocal()
    try:
        service = RoomService(db)
        print("Creating room...")
        
        # We no longer need user_id, it is fully anonymous
        creator_session = str(uuid.uuid4())
        room = service.create_room(creator_session_id=creator_session)
        print(f"Room created: {room.code}")

        # Add another anon participant
        participant2_session = str(uuid.uuid4())
        service.join_room(session_id=participant2_session, room_code=room.code)
        print("Participant 2 joined")

        # Submit moods
        room = service.submit_mood(creator_session, room.code, "action")
        room = service.submit_mood(participant2_session, room.code, "comedy")
        print(f"All ready: {room.are_all_participants_ready()}")

        if room.are_all_participants_ready():
            print("Fetching recommendations...")
            recs = service.start_voting_session(room)
            print(f"Got {len(recs)} recommendations")

            if recs:
                first_rec_id = recs[0]["id"]
                print(f"Voting on TMDB ID {first_rec_id}")
                
                service.record_swipe(creator_session, room.code, first_rec_id, RoomAction.LIKE)
                match = service.record_swipe(participant2_session, room.code, first_rec_id, RoomAction.SUPERLIKE)
                
                if match:
                    print(f"Match found! TMDB ID: {match.tmdb_id}")
                    service.finish_room(room)
                    print(f"Room status is now: {room.status}")
                else:
                    print("No match found.")

            print("Testing TTL cleanup...")
            service.cleanup_expired_rooms(minutes_old=0)
            print("Cleanup ran.")
            
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
