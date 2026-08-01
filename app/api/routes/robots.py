from fastapi import APIRouter, Depends, HTTPException, Query, Response, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.responses import error_response, success_response
from app.db.session import get_db, SessionLocal
from app.models.camera import Camera
from app.models.robot import Robot
from app.models.robot_dispatch import RobotDispatch
from app.models.safety_event import SafetyEvent
from app.schemas.robot import (
    RobotCreateRequest,
    RobotDispatchRequest,
    RobotDispatchResponse,
    RobotMoveRequest,
    RobotPtzRequest,
    RobotRegisterRequest,
    RobotResponse,
    RobotUpdateRequest,
)
from app.services import robot_connections


router = APIRouter()
protected = [Depends(get_current_user)]


def serialize_robot(robot: Robot) -> dict:
    return RobotResponse.model_validate(robot).model_dump(mode="json", by_alias=True)


def serialize_dispatch(dispatch: RobotDispatch) -> dict:
    return RobotDispatchResponse.model_validate(dispatch).model_dump(mode="json", by_alias=True)


def get_robot_or_404(robot_id: int, db: Session) -> Robot:
    robot = db.get(Robot, robot_id)
    if robot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response("ROBOT_NOT_FOUND", "로봇을 찾을 수 없습니다."),
        )
    return robot


@router.get("", dependencies=protected)
def list_robots(db: Session = Depends(get_db)):
    robots = db.scalars(select(Robot).order_by(Robot.id.desc())).all()
    return success_response(data={"items": [serialize_robot(robot) for robot in robots]})


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=protected)
def create_robot(payload: RobotCreateRequest, db: Session = Depends(get_db)):
    robot = Robot(
        name=payload.name,
        control_address=payload.control_address,
        camera_rtsp_url=payload.camera_rtsp_url,
        location_x=payload.location_x,
        location_y=payload.location_y,
        status="IDLE",
    )
    db.add(robot)
    db.commit()
    db.refresh(robot)
    return success_response(data=serialize_robot(robot), message="로봇이 등록되었습니다.")


@router.post("/register")
def register_robot(payload: RobotRegisterRequest, db: Session = Depends(get_db)):
    """Self-registration endpoint the robot calls on boot (see
    SafeVision-Robot's discovery client) instead of an operator filling in
    a form — upserts by hardware_id so re-announcing after a reboot/IP
    change updates the existing row rather than creating a duplicate."""
    robot = db.scalar(select(Robot).where(Robot.hardware_id == payload.hardware_id))
    created = robot is None
    if robot is None:
        robot = Robot(hardware_id=payload.hardware_id)
        db.add(robot)

    robot.name = payload.name
    robot.control_address = payload.control_address
    robot.camera_rtsp_url = payload.camera_rtsp_url
    if created or robot.status == "OFFLINE":
        robot.status = "IDLE"

    db.commit()
    db.refresh(robot)
    message = "로봇이 등록되었습니다." if created else "로봇 접속 정보가 갱신되었습니다."
    return success_response(data=serialize_robot(robot), message=message)


@router.get("/{robot_id}", dependencies=protected)
def get_robot(robot_id: int, db: Session = Depends(get_db)):
    return success_response(data=serialize_robot(get_robot_or_404(robot_id, db)))


@router.put("/{robot_id}", dependencies=protected)
async def update_robot(robot_id: int, payload: RobotUpdateRequest, db: Session = Depends(get_db)):
    robot = get_robot_or_404(robot_id, db)
    previous_status = robot.status
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(robot, key, value)

    dispatch: RobotDispatch | None = None
    should_start_dispatch = previous_status == "IDLE" and robot.status == "DISPATCHED"
    if should_start_dispatch:
        dispatch = RobotDispatch(robot_id=robot_id)
        db.add(dispatch)

    db.commit()
    db.refresh(robot)
    sent: bool | None = None
    if dispatch is not None:
        db.refresh(dispatch)
        sent = await robot_connections.send_command(
            robot_id,
            {
                "type": "dispatch",
                "fallbackRoute": DEMO_DISPATCH_ROUTE,
                "dispatchId": dispatch.id,
            },
        )
    data = serialize_robot(robot)
    if sent is not None:
        data["sent"] = sent
    return success_response(data=data, message="로봇 정보가 수정되었습니다.")


@router.delete("/{robot_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=protected)
def delete_robot(robot_id: int, db: Session = Depends(get_db)):
    robot = get_robot_or_404(robot_id, db)
    db.delete(robot)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{robot_id}/ptz", dependencies=protected)
async def send_ptz_command(robot_id: int, payload: RobotPtzRequest, db: Session = Depends(get_db)):
    get_robot_or_404(robot_id, db)
    sent = await robot_connections.send_command(robot_id, {"type": "ptz", "direction": payload.direction})
    return success_response(data={"sent": sent}, message="PTZ 명령을 전송했습니다.")


@router.post("/{robot_id}/move", dependencies=protected)
async def send_move_command(robot_id: int, payload: RobotMoveRequest, db: Session = Depends(get_db)):
    get_robot_or_404(robot_id, db)
    sent = await robot_connections.send_command(robot_id, {"type": "move", "direction": payload.direction})
    return success_response(data={"sent": sent}, message="로봇 주행 명령을 전송했습니다.")


@router.post("/{robot_id}/route-record/start", dependencies=protected)
async def start_route_recording(robot_id: int, db: Session = Depends(get_db)):
    get_robot_or_404(robot_id, db)
    sent = await robot_connections.send_command(robot_id, {"type": "route_record_start"})
    return success_response(data={"sent": sent}, message="이동 경로 녹화를 시작했습니다.")


@router.post("/{robot_id}/route-record/save", dependencies=protected)
async def save_route_recording(robot_id: int, db: Session = Depends(get_db)):
    get_robot_or_404(robot_id, db)
    sent = await robot_connections.send_command(robot_id, {"type": "route_record_save"})
    return success_response(data={"sent": sent}, message="이동 경로를 저장했습니다.")


@router.post("/{robot_id}/route-record/clear", dependencies=protected)
async def clear_route_recording(robot_id: int, db: Session = Depends(get_db)):
    get_robot_or_404(robot_id, db)
    sent = await robot_connections.send_command(robot_id, {"type": "route_record_clear"})
    return success_response(data={"sent": sent}, message="저장된 이동 경로를 삭제했습니다.")


@router.post("/{robot_id}/route-record/play", dependencies=protected)
async def play_route_recording(robot_id: int, db: Session = Depends(get_db)):
    get_robot_or_404(robot_id, db)
    sent = await robot_connections.send_command(robot_id, {"type": "route_play"})
    return success_response(data={"sent": sent}, message="저장된 이동 경로 재생을 시작했습니다.")


DEMO_DISPATCH_ROUTE = [
    {"direction": "forward", "durationMs": 2500},
    {"direction": "right", "durationMs": 700},
    {"direction": "forward", "durationMs": 1800},
    {"direction": "left", "durationMs": 700},
    {"direction": "forward", "durationMs": 1200},
]


@router.post("/{robot_id}/dispatch", status_code=status.HTTP_201_CREATED, dependencies=protected)
async def dispatch_robot(robot_id: int, payload: RobotDispatchRequest, db: Session = Depends(get_db)):
    robot = get_robot_or_404(robot_id, db)

    target_x: float | None = None
    target_y: float | None = None
    if payload.safety_event_id is not None:
        event = db.get(SafetyEvent, payload.safety_event_id)
        if event is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response("SAFETY_EVENT_NOT_FOUND", "안전 이벤트를 찾을 수 없습니다."),
            )
        if event.camera_id is not None:
            camera = db.get(Camera, event.camera_id)
            if camera is not None:
                target_x, target_y = camera.location_x, camera.location_y

    dispatch = RobotDispatch(
        robot_id=robot_id,
        safety_event_id=payload.safety_event_id,
        target_x=target_x,
        target_y=target_y,
    )
    db.add(dispatch)
    robot.status = "DISPATCHED"
    db.commit()
    db.refresh(dispatch)
    sent = await robot_connections.send_command(
        robot_id,
        {
            "type": "dispatch",
            "fallbackRoute": DEMO_DISPATCH_ROUTE,
            "safetyEventId": payload.safety_event_id,
            "dispatchId": dispatch.id,
        },
    )
    return success_response(
        data={**serialize_dispatch(dispatch), "sent": sent},
        message="로봇을 출동시켰습니다.",
    )


@router.post("/{robot_id}/return", dependencies=protected)
async def return_robot(robot_id: int, db: Session = Depends(get_db)):
    robot = get_robot_or_404(robot_id, db)
    sent = await robot_connections.send_command(robot_id, {"type": "return"})
    robot.status = "IDLE"
    db.commit()
    db.refresh(robot)
    return success_response(
        data={"robot": serialize_robot(robot), "sent": sent},
        message="로봇 복귀 명령을 전송했습니다.",
    )


@router.get("/{robot_id}/dispatches", dependencies=protected)
def list_dispatches(robot_id: int, db: Session = Depends(get_db)):
    get_robot_or_404(robot_id, db)
    dispatches = (
        db.query(RobotDispatch)
        .filter(RobotDispatch.robot_id == robot_id)
        .order_by(RobotDispatch.id.desc())
        .limit(20)
        .all()
    )
    return success_response(data=[serialize_dispatch(dispatch) for dispatch in dispatches])


@router.websocket("/ws")
async def robot_command_channel(websocket: WebSocket, hardware_id: str = Query(alias="hardwareId")):
    """The robot itself connects here and keeps the socket open (see
    SafeVision-Robot's command_ws.py) — commands are pushed down this
    connection instead of the backend dialing the robot, since robots may
    be behind NAT/firewalls the backend can't reach inbound. No auth here,
    same as /register — a robot only needs to know its own hardware_id,
    matching the self-registration flow's trust model."""
    db = SessionLocal()
    try:
        robot = db.scalar(select(Robot).where(Robot.hardware_id == hardware_id))
    finally:
        db.close()

    if robot is None:
        await websocket.close(code=4404)
        return

    await websocket.accept()
    robot_connections.register(robot.id, websocket)
    try:
        while True:
            # Nothing meaningful expected from the robot on this channel —
            # just block here so we notice the disconnect (ping/pong is
            # handled by the ASGI server beneath us).
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        robot_connections.unregister(robot.id, websocket)
