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
    _record_event(event_type="FALL_DETECTED", event_level=2, camera_id=camera_id, equipment_action="none")


def record_zone_intrusion_event(
    camera_id: int | None = None,
    zone_id: int | None = None,
    zone_type: str | None = None,
) -> None:
    detected_at = datetime.now(timezone.utc)
    if zone_type == "DANGER":
        equipment_action = "stop"
        event_level = 1
    elif zone_type == "RESTRICTED":
        equipment_action = "slow"
        event_level = 2
    else:
        equipment_action = "none"
        event_level = 2
    print(
        f"[BARO][ZONE_INTRUSION] {detected_at.isoformat()} 구역 접근 감지됨 "
        f"camera_id={camera_id} zone_id={zone_id} zone_type={zone_type} action={equipment_action.upper()}"
    )
    _record_event(
        event_type="ZONE_INTRUSION",
        event_level=event_level,
        camera_id=camera_id,
        zone_id=zone_id,
        equipment_action=equipment_action,
    )


def record_camera_drift_event(camera_id: int | None = None) -> None:
    # A large apparent camera shift isn't itself an on-site hazard the way a
    # fall or a zone intrusion is — it means zone monitoring for this camera
    # may now be unreliable, which calls for an operator to look and
    # re-register the zones, not an automatic equipment stop.
    detected_at = datetime.now(timezone.utc)
    print(f"[BARO][CAMERA_ANGLE_CHANGED] {detected_at.isoformat()} 카메라 각도 변경 감지됨 camera_id={camera_id}")
    _record_event(event_type="CAMERA_ANGLE_CHANGED", event_level=2, camera_id=camera_id, equipment_action="none")


def _record_event(
    event_type: str,
    event_level: int,
    camera_id: int | None = None,
    zone_id: int | None = None,
    equipment_action: str = "stop",
) -> None:
    event_id: int | None = None
    db = SessionLocal()
    try:
        event = SafetyEvent(
            camera_id=camera_id,
            zone_id=zone_id,
            event_type=event_type,
            event_level=event_level,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        event_id = event.id
    except Exception as exc:
        db.rollback()
        print(f"[BARO][{event_type}][DB_ERROR] {exc}")
    finally:
        db.close()

    if equipment_action == "stop":
        get_motor_controller().stop()
    elif equipment_action == "slow":
        get_motor_controller().slow()

    if camera_id is not None and event_id is not None:
        threading.Thread(target=_save_event_clip, args=(camera_id, event_id, event_type), daemon=True).start()


def _save_event_clip(camera_id: int, event_id: int, event_type: str) -> None:
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
        print(f"[BARO][{event_type}][CLIP_DB_ERROR] {exc}")
    finally:
        db.close()
