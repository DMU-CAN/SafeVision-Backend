import threading
import time
from datetime import datetime, timezone

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.safety_event import SafetyEvent
from app.services.motor_controller import get_motor_controller
from app.services.recording_service import extract_event_clip


def record_fall_detected_event(camera_id: int | None = None) -> None:
    detected_at = datetime.now(timezone.utc)
    print(f"[BARO][FALL_DETECTED] {detected_at.isoformat()} 넘어짐 감지됨 camera_id={camera_id}")

    event_id: int | None = None
    db = SessionLocal()
    try:
        event = SafetyEvent(
            camera_id=camera_id,
            event_type="FALL_DETECTED",
            event_level=2,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        event_id = event.id
    except Exception as exc:
        db.rollback()
        print(f"[BARO][FALL_DETECTED][DB_ERROR] {exc}")
    finally:
        db.close()

    get_motor_controller().stop()

    if camera_id is not None and event_id is not None:
        threading.Thread(target=_save_event_clip, args=(camera_id, event_id), daemon=True).start()


def _save_event_clip(camera_id: int, event_id: int) -> None:
    # Wait for post-roll footage to land in the rolling buffer before
    # concatenating it into a permanent clip, so the saved clip covers both
    # sides of the event, not just the moments before it.
    time.sleep(get_settings().recording_clip_post_roll_seconds)
    clip_path = extract_event_clip(camera_id, event_id)
    if not clip_path:
        return

    db = SessionLocal()
    try:
        event = db.get(SafetyEvent, event_id)
        if event is not None:
            event.clip_path = clip_path
            db.commit()
    except Exception as exc:
        db.rollback()
        print(f"[BARO][FALL_DETECTED][CLIP_DB_ERROR] {exc}")
    finally:
        db.close()
