import asyncio

import cv2
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.responses import error_response, success_response
from app.db.session import get_db
from app.models.camera import Camera
from app.schemas.camera import CameraCreateRequest, CameraResponse, CameraUpdateRequest, StreamUrlResponse
from app.services.camera_sources import build_camera_source
from app.services.recording_service import start_recording, stop_recording


router = APIRouter()


def serialize_camera(camera: Camera) -> dict:
    return CameraResponse.model_validate(camera).model_dump(mode="json", by_alias=True)


def get_camera_or_404(camera_id: int, db: Session) -> Camera:
    camera = db.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response("CAMERA_NOT_FOUND", "카메라를 찾을 수 없습니다."),
        )
    return camera


@router.get("")
def list_cameras(db: Session = Depends(get_db)):
    cameras = db.scalars(select(Camera).order_by(Camera.id.desc())).all()
    return success_response(data={"items": [serialize_camera(camera) for camera in cameras]})


@router.post("", status_code=status.HTTP_201_CREATED)
def create_camera(payload: CameraCreateRequest, db: Session = Depends(get_db)):
    camera = Camera(
        name=payload.name,
        rtsp_url=payload.rtsp_url,
        location=payload.location,
        status=payload.status,
        location_x=payload.location_x,
        location_y=payload.location_y,
    )
    db.add(camera)
    db.commit()
    db.refresh(camera)
    start_recording(camera.id, camera.rtsp_url)
    return success_response(data=serialize_camera(camera), message="카메라가 등록되었습니다.")


@router.get("/{camera_id}")
def get_camera(camera_id: int, db: Session = Depends(get_db)):
    camera = get_camera_or_404(camera_id, db)
    return success_response(data=serialize_camera(camera))


@router.put("/{camera_id}")
def update_camera(camera_id: int, payload: CameraUpdateRequest, db: Session = Depends(get_db)):
    camera = get_camera_or_404(camera_id, db)
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(camera, key, value)
    db.commit()
    db.refresh(camera)
    if "rtsp_url" in update_data:
        stop_recording(camera.id)
        start_recording(camera.id, camera.rtsp_url)
    return success_response(data=serialize_camera(camera), message="카메라 정보가 수정되었습니다.")


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_camera(camera_id: int, db: Session = Depends(get_db)):
    camera = get_camera_or_404(camera_id, db)
    db.delete(camera)
    db.commit()
    stop_recording(camera_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{camera_id}/stream-url")
def get_camera_stream_url(camera_id: int, db: Session = Depends(get_db)):
    camera = get_camera_or_404(camera_id, db)
    data = StreamUrlResponse(camera_id=camera.id, stream_url=camera.rtsp_url).model_dump(mode="json", by_alias=True)
    return success_response(data=data)


async def _mjpeg_frames(camera: Camera, confidence: float | None):
    camera_source = build_camera_source(camera, confidence=confidence)
    try:
        track = await asyncio.to_thread(camera_source.create_video_track)
        while True:
            frame = await track.recv()
            image = frame.to_ndarray(format="bgr24")
            ok, buffer = await asyncio.to_thread(cv2.imencode, ".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ok:
                continue
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
            )
    finally:
        await camera_source.close()


@router.get("/{camera_id}/mjpeg")
async def stream_camera_mjpeg(
    camera_id: int,
    yolo_confidence: float | None = Query(default=None),
    db: Session = Depends(get_db),
):
    camera = get_camera_or_404(camera_id, db)
    return StreamingResponse(
        _mjpeg_frames(camera, yolo_confidence),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
