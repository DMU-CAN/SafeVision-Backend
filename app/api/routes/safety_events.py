from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.responses import error_response, success_response
from app.db.session import get_db
from app.models.safety_event import SafetyEvent
from app.schemas.safety_event import SafetyEventResponse


router = APIRouter()


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
