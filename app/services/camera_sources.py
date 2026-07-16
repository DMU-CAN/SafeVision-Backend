import asyncio
import math
import socket
import time
from abc import ABC, abstractmethod
from fractions import Fraction
from urllib.parse import urlparse

import cv2
import numpy as np
from aiortc import VideoStreamTrack
from aiortc.contrib.media import MediaPlayer
from av import VideoFrame

from app.core.config import get_settings
from app.schemas.webrtc import CameraSourceRequest


class CameraSource(ABC):
    @abstractmethod
    def create_video_track(self) -> VideoStreamTrack:
        raise NotImplementedError

    async def close(self) -> None:
        return None


class MediaPlayerSource(CameraSource):
    def __init__(self, url: str, options: dict[str, str] | None = None) -> None:
        self.url = url
        self.options = options or {}
        self.player: MediaPlayer | None = None

    def create_video_track(self) -> VideoStreamTrack:
        self.player = MediaPlayer(self.url, options=self.options)
        if self.player.video is None:
            raise ValueError(f"Video track is not available from source: {self.url}")
        return self.player.video

    async def close(self) -> None:
        if self.player:
            self.player.video and self.player.video.stop()
            self.player.audio and self.player.audio.stop()


class RtspCameraSource(MediaPlayerSource):
    def __init__(self, url: str) -> None:
        super().__init__(
            url,
            options={
                "rtsp_transport": "tcp",
                "stimeout": "5000000",
                "rw_timeout": "5000000",
            },
        )

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

        return super().create_video_track()


class FileCameraSource(MediaPlayerSource):
    pass


class OpenCVCameraTrack(VideoStreamTrack):
    def __init__(self, device_index: int) -> None:
        super().__init__()
        self.capture = cv2.VideoCapture(device_index)
        if not self.capture.isOpened():
            raise ValueError(f"Could not open webcam device index {device_index}")

    async def recv(self) -> VideoFrame:
        pts, time_base = await self.next_timestamp()
        ok, frame = await asyncio.to_thread(self.capture.read)
        if not ok:
            raise ValueError("Could not read frame from webcam")

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        return video_frame

    def stop(self) -> None:
        super().stop()
        self.capture.release()


class WebcamCameraSource(CameraSource):
    def __init__(self, device_index: int) -> None:
        self.device_index = device_index
        self.track: OpenCVCameraTrack | None = None

    def create_video_track(self) -> VideoStreamTrack:
        self.track = OpenCVCameraTrack(self.device_index)
        return self.track

    async def close(self) -> None:
        if self.track:
            self.track.stop()


class TestPatternTrack(VideoStreamTrack):
    def __init__(self) -> None:
        super().__init__()
        self.start_time = time.monotonic()
        self.frame_index = 0

    async def recv(self) -> VideoFrame:
        await asyncio.sleep(1 / 30)
        width, height = 1280, 720
        elapsed = time.monotonic() - self.start_time
        x = np.linspace(0, 255, width, dtype=np.uint8)
        y = np.linspace(0, 255, height, dtype=np.uint8)
        gradient_x = np.tile(x, (height, 1))
        gradient_y = np.tile(y[:, None], (1, width))
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:, :, 0] = gradient_x
        frame[:, :, 1] = gradient_y
        frame[:, :, 2] = ((gradient_x.astype(int) + gradient_y.astype(int)) // 2).astype(np.uint8)

        center_x = int(width / 2 + math.sin(elapsed) * width / 4)
        center_y = int(height / 2 + math.cos(elapsed * 0.8) * height / 5)
        cv2.circle(frame, (center_x, center_y), 70, (255, 255, 255), -1)
        cv2.putText(
            frame,
            "BARO WebRTC test source",
            (40, height - 48),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (255, 255, 255),
            3,
            cv2.LINE_AA,
        )

        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts = self.frame_index
        video_frame.time_base = Fraction(1, 30)
        self.frame_index += 1
        return video_frame


class TestPatternSource(CameraSource):
    def __init__(self) -> None:
        self.track: TestPatternTrack | None = None

    def create_video_track(self) -> VideoStreamTrack:
        self.track = TestPatternTrack()
        return self.track

    async def close(self) -> None:
        if self.track:
            self.track.stop()


def build_camera_source(request: CameraSourceRequest | None = None) -> CameraSource:
    settings = get_settings()
    source = request or CameraSourceRequest(
        kind=settings.default_camera_source_kind, url=settings.default_camera_source_url or None
    )

    if source.kind == "test_pattern":
        return TestPatternSource()

    if source.kind == "rtsp":
        if not source.url:
            raise ValueError("rtsp source requires url")
        return RtspCameraSource(source.url)

    if source.kind == "file":
        if not source.url:
            raise ValueError("file source requires url")
        return FileCameraSource(source.url)

    if source.kind == "webcam":
        return WebcamCameraSource(source.device_index if source.device_index is not None else settings.default_webcam_index)

    raise ValueError(f"Unsupported camera source kind: {source.kind}")
