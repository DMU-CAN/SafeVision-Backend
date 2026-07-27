import socket
from abc import ABC, abstractmethod
from urllib.parse import urlparse

from aiortc import VideoStreamTrack
from aiortc.contrib.media import MediaPlayer

from app.core.config import get_settings
from app.models.camera import Camera
from app.services.yolo_detector import YoloAnnotatedTrack


class CameraSource(ABC):
    @abstractmethod
    def create_video_track(self) -> VideoStreamTrack:
        raise NotImplementedError

    async def close(self) -> None:
        return None


class YoloCameraSource(CameraSource):
    def __init__(self, source: CameraSource, confidence: float, camera_id: int | None = None) -> None:
        self.source = source
        self.confidence = confidence
        self.camera_id = camera_id

    def create_video_track(self) -> VideoStreamTrack:
        return YoloAnnotatedTrack(self.source.create_video_track(), self.confidence, camera_id=self.camera_id)

    async def close(self) -> None:
        await self.source.close()


class RtspCameraSource(CameraSource):
    def __init__(self, url: str) -> None:
        self.url = url
        self.player: MediaPlayer | None = None

    def create_video_track(self) -> VideoStreamTrack:
        parsed_url = urlparse(self.url)
        host = parsed_url.hostname
        port = parsed_url.port or 554

        if not host:
            raise ValueError("rtsp source requires a valid host")

        try:
            with socket.create_connection((host, port), timeout=3):
                pass
        except OSError as exc:
            raise ValueError(f"RTSP source is not reachable: {host}:{port}") from exc

        self.player = MediaPlayer(
            self.url,
            options={
                "rtsp_transport": "tcp",
                "stimeout": "5000000",
                "rw_timeout": "5000000",
            },
        )
        if self.player.video is None:
            raise ValueError(f"Video track is not available from source: {self.url}")
        return self.player.video

    async def close(self) -> None:
        if self.player:
            self.player.video and self.player.video.stop()
            self.player.audio and self.player.audio.stop()


def build_camera_source(camera: Camera, confidence: float | None = None) -> CameraSource:
    settings = get_settings()
    source: CameraSource = RtspCameraSource(camera.rtsp_url)
    resolved_confidence = confidence if confidence is not None else settings.yolo_confidence
    return YoloCameraSource(source, resolved_confidence, camera_id=camera.id)
