from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from app.core.responses import success_response


router = APIRouter()


class EmergencyRequest(BaseModel):
    message: Optional[str] = None
    robot_id: Optional[int] = Field(default=None, alias="robotId")
    safety_event_id: Optional[int] = Field(default=None, alias="safetyEventId")

    model_config = ConfigDict(populate_by_name=True)


# There is no real emergency-center system integrated yet — these two
# endpoints exist so the frontend has something real to call now, and just
# log the request server-side. Swap the body for an actual call/webhook to
# the emergency center's system once one exists; the request/response shape
# here is designed to not need to change when that happens.


@router.post("/contact")
def contact_emergency_center(payload: EmergencyRequest):
    print(
        f"[BARO][EMERGENCY] {datetime.now(timezone.utc).isoformat()} 연결 요청 "
        f"robotId={payload.robot_id} eventId={payload.safety_event_id} message={payload.message}"
    )
    return success_response(data={"connected": True}, message="응급센터에 연결 요청을 전송했습니다.")


@router.post("/share")
def share_situation(payload: EmergencyRequest):
    print(
        f"[BARO][EMERGENCY] {datetime.now(timezone.utc).isoformat()} 현장 상황 공유 "
        f"robotId={payload.robot_id} eventId={payload.safety_event_id} message={payload.message}"
    )
    return success_response(data={"shared": True}, message="현장 상황을 공유했습니다.")
