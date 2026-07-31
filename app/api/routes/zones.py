from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.responses import error_response, success_response
from app.db.session import get_db
from app.models.zone import Zone
from app.schemas.zone import ZoneCreate, ZoneResponse
from app.services.zone_calibration import capture_frame_from_buffer, has_reference_frame, save_reference_frame

router = APIRouter(dependencies=[Depends(get_current_user)])


def serialize_zone(zone: Zone) -> dict:
    return ZoneResponse.model_validate(zone).model_dump(mode="json", by_alias=True)


@router.get("")
def list_zones(camera_id: int | None = Query(default=None), db: Session = Depends(get_db)):
    query = db.query(Zone).filter(Zone.is_active.is_(True))
    if camera_id is not None:
        query = query.filter((Zone.camera_id == camera_id) | (Zone.camera_id.is_(None)))
    zones = query.order_by(Zone.id.desc()).all()
    return success_response(data=[serialize_zone(zone) for zone in zones])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_zone(payload: ZoneCreate, db: Session = Depends(get_db)):
    zone = Zone(
        camera_id=payload.camera_id,
        name=payload.name,
        points=[point.model_dump() for point in payload.points],
        zone_type=payload.zone_type,
    )
    db.add(zone)
    db.commit()
    db.refresh(zone)

    # Establish the drift-correction baseline the first time a camera gets a
    # zone — later zones on the same camera reuse it. Best-effort: a missing
    # recording buffer (camera just registered, no segments yet) just means
    # drift correction stays off for this camera until a frame is available.
    if payload.camera_id is not None and not has_reference_frame(payload.camera_id):
        frame = capture_frame_from_buffer(payload.camera_id)
        if frame is not None:
            save_reference_frame(payload.camera_id, frame)

    return success_response(data=serialize_zone(zone), message="위험구역이 저장되었습니다.")


@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_zone(zone_id: int, db: Session = Depends(get_db)):
    zone = db.get(Zone, zone_id)
    if zone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response("ZONE_NOT_FOUND", "위험구역을 찾을 수 없습니다."),
        )
    db.delete(zone)
    db.commit()
