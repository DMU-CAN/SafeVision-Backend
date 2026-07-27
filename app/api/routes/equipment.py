from fastapi import APIRouter

from app.core.responses import success_response
from app.services.motor_controller import get_motor_controller


router = APIRouter()


@router.post("/stop")
def stop_equipment():
    sent = get_motor_controller().stop()
    return success_response(data={"sent": sent}, message="설비 정지 명령을 전송했습니다.")


@router.post("/slow")
def slow_equipment():
    sent = get_motor_controller().slow()
    return success_response(data={"sent": sent}, message="설비 감속 명령을 전송했습니다.")


@router.post("/resume")
def resume_equipment():
    sent = get_motor_controller().resume()
    return success_response(data={"sent": sent}, message="설비 재가동 명령을 전송했습니다.")
