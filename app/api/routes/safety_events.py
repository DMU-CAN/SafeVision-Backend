from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.responses import error_response, success_response
from app.db.session import get_db
from app.models.safety_event import SafetyEvent
from app.schemas.safety_event import SafetyEventResponse


router = APIRouter(dependencies=[Depends(get_current_user)])


def serialize_event(event: SafetyEvent) -> dict:
    return SafetyEventResponse.model_validate(event).model_dump(mode="json", by_alias=True)


@router.get("")
def list_safety_events(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    events = db.query(SafetyEvent).order_by(SafetyEvent.id.desc()).limit(limit).all()
    return success_response(data=[serialize_event(event) for event in events])


@router.get("/{event_id}")
def get_safety_event(event_id: int, db: Session = Depends(get_db)):
    event = db.get(SafetyEvent, event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response("SAFETY_EVENT_NOT_FOUND", "안전 이벤트를 찾을 수 없습니다."),
        )

    return success_response(data=serialize_event(event))


@router.get("/{event_id}/clip")
def get_safety_event_clip(event_id: int, db: Session = Depends(get_db)):
    event = db.get(SafetyEvent, event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response("SAFETY_EVENT_NOT_FOUND", "안전 이벤트를 찾을 수 없습니다."),
        )
    if not event.clip_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response("CLIP_NOT_READY", "이벤트 영상이 아직 준비되지 않았습니다."),
        )

    clip_file = Path(get_settings().recordings_dir) / event.clip_path
    if not clip_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response("CLIP_NOT_FOUND", "이벤트 영상 파일을 찾을 수 없습니다."),
        )

    return FileResponse(clip_file, media_type="video/mp4")
