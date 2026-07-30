from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.responses import error_response, success_response
from app.db.session import get_db
from app.models.equipment import Equipment
from app.schemas.equipment import EquipmentCreateRequest, EquipmentResponse, EquipmentUpdateRequest
from app.services.equipment_controller import send_equipment_command


router = APIRouter()


def serialize_equipment(equipment: Equipment) -> dict:
    return EquipmentResponse.model_validate(equipment).model_dump(mode="json", by_alias=True)


def get_equipment_or_404(equipment_id: int, db: Session) -> Equipment:
    equipment = db.get(Equipment, equipment_id)
    if equipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response("EQUIPMENT_NOT_FOUND", "설비를 찾을 수 없습니다."),
        )
    return equipment


@router.get("")
def list_equipments(db: Session = Depends(get_db)):
    equipments = db.scalars(select(Equipment).order_by(Equipment.id.desc())).all()
    return success_response(data={"items": [serialize_equipment(equipment) for equipment in equipments]})


@router.post("", status_code=status.HTTP_201_CREATED)
def create_equipment(payload: EquipmentCreateRequest, db: Session = Depends(get_db)):
    equipment = Equipment(
        name=payload.name,
        control_protocol=payload.control_protocol,
        control_address=payload.control_address,
    )
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    return success_response(data=serialize_equipment(equipment), message="설비가 등록되었습니다.")


@router.get("/{equipment_id}")
def get_equipment(equipment_id: int, db: Session = Depends(get_db)):
    return success_response(data=serialize_equipment(get_equipment_or_404(equipment_id, db)))


@router.put("/{equipment_id}")
def update_equipment(equipment_id: int, payload: EquipmentUpdateRequest, db: Session = Depends(get_db)):
    equipment = get_equipment_or_404(equipment_id, db)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(equipment, key, value)
    db.commit()
    db.refresh(equipment)
    return success_response(data=serialize_equipment(equipment), message="설비 정보가 수정되었습니다.")


@router.delete("/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_equipment(equipment_id: int, db: Session = Depends(get_db)):
    equipment = get_equipment_or_404(equipment_id, db)
    db.delete(equipment)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _send_command(equipment_id: int, command: str, message: str, db: Session):
    equipment = get_equipment_or_404(equipment_id, db)
    sent = send_equipment_command(equipment.control_protocol, equipment.control_address, command)
    return success_response(data={"sent": sent}, message=message)


@router.post("/{equipment_id}/stop")
def stop_equipment(equipment_id: int, db: Session = Depends(get_db)):
    return _send_command(equipment_id, "STOP", "설비 정지 명령을 전송했습니다.", db)


@router.post("/{equipment_id}/slow")
def slow_equipment(equipment_id: int, db: Session = Depends(get_db)):
    return _send_command(equipment_id, "SLOW", "설비 감속 명령을 전송했습니다.", db)


@router.post("/{equipment_id}/resume")
def resume_equipment(equipment_id: int, db: Session = Depends(get_db)):
    return _send_command(equipment_id, "RESUME", "설비 재가동 명령을 전송했습니다.", db)
