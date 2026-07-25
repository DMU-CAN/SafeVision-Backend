from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.models.safety_event import SafetyEvent


def record_fall_detected_event(camera_id: int | None = None) -> None:
    detected_at = datetime.now(timezone.utc)
    print(f"[BARO][FALL_DETECTED] {detected_at.isoformat()} 넘어짐 감지됨 camera_id={camera_id}")

    db = SessionLocal()
    try:
        db.add(
            SafetyEvent(
                camera_id=camera_id,
                event_type="FALL_DETECTED",
                event_level=2,
            )
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"[BARO][FALL_DETECTED][DB_ERROR] {exc}")
    finally:
        db.close()
