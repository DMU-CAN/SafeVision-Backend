import asyncio
import uuid
from dataclasses import dataclass

from aiortc import RTCPeerConnection, RTCSessionDescription
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.responses import error_response, success_response
from app.db.session import get_db
from app.models.camera import Camera
from app.models.robot import Robot
from app.schemas.webrtc import WebRTCAnswerResponse, WebRTCOfferRequest, WebRTCSessionResponse
from app.services.camera_sources import CameraSource, RtspCameraSource, build_camera_source


router = APIRouter(dependencies=[Depends(get_current_user)])


@dataclass
class WebRTCSession:
    peer_connection: RTCPeerConnection
    camera_source: CameraSource


active_sessions: dict[str, WebRTCSession] = {}


async def close_session(session_id: str) -> None:
    session = active_sessions.pop(session_id, None)
    if not session:
        return
    await session.camera_source.close()
    await session.peer_connection.close()


def resolve_camera_source(payload: WebRTCOfferRequest, db: Session) -> CameraSource:
    if payload.camera_id is not None:
        camera = db.get(Camera, payload.camera_id)
        if camera is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response("CAMERA_NOT_FOUND", "카메라를 찾을 수 없습니다."),
            )
        return build_camera_source(camera, confidence=payload.yolo_confidence, yolo_enabled=payload.yolo_enabled)

    if payload.robot_id is not None:
        robot = db.get(Robot, payload.robot_id)
        if robot is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response("ROBOT_NOT_FOUND", "로봇을 찾을 수 없습니다."),
            )
        # Robot cameras are always plain passthrough — YOLO overlay is a
        # fixed-camera concept (zones are defined per fixed camera view).
        return RtspCameraSource(robot.camera_rtsp_url)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=error_response("INVALID_REQUEST", "cameraId 또는 robotId 중 하나가 필요합니다."),
    )


@router.post("/offer")
async def create_webrtc_answer(payload: WebRTCOfferRequest, db: Session = Depends(get_db)):
    session_id = str(uuid.uuid4())
    peer_connection = RTCPeerConnection()

    try:
        camera_source = resolve_camera_source(payload, db)
        video_track = await asyncio.to_thread(camera_source.create_video_track)
        peer_connection.addTrack(video_track)

        @peer_connection.on("connectionstatechange")
        async def on_connectionstatechange() -> None:
            if peer_connection.connectionState in {"failed", "closed", "disconnected"}:
                await close_session(session_id)

        await peer_connection.setRemoteDescription(RTCSessionDescription(sdp=payload.sdp, type=payload.type))
        answer = await peer_connection.createAnswer()
        await peer_connection.setLocalDescription(answer)

        active_sessions[session_id] = WebRTCSession(peer_connection=peer_connection, camera_source=camera_source)
        response = WebRTCAnswerResponse(
            sdp=peer_connection.localDescription.sdp,
            type="answer",
            session_id=session_id,
        )
        return success_response(data=response.model_dump(mode="json", by_alias=True), message="WebRTC answer가 생성되었습니다.")
    except HTTPException:
        await peer_connection.close()
        raise
    except Exception as exc:
        await peer_connection.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response("WEBRTC_OFFER_FAILED", str(exc)),
        ) from exc


@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    session = active_sessions.get(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response("SESSION_NOT_FOUND", "WebRTC 세션을 찾을 수 없습니다."),
        )

    data = WebRTCSessionResponse(session_id=session_id, state=session.peer_connection.connectionState)
    return success_response(data=data.model_dump(mode="json", by_alias=True))


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str):
    await close_session(session_id)


async def close_all_sessions() -> None:
    await asyncio.gather(*(close_session(session_id) for session_id in list(active_sessions)))
