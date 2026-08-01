import asyncio
import contextlib
import time

from aiortc import VideoStreamTrack
from aiortc.contrib.media import MediaPlayer
from av import VideoFrame

from app.core.config import get_settings
from app.services.fall_detection import is_fall_detection, pose_metrics
from app.services.safety_event_logger import (
    record_camera_drift_event,
    record_fall_detected_event,
    record_zone_intrusion_event,
)
from app.services.yolo_detector import get_yolo_detector
from app.services.zone_calibration import check_and_correct_drift
from app.services.zone_service import find_zone_for_point


class LatestFrameTrack(VideoStreamTrack):
    def __init__(self, hub: "CameraStreamHub") -> None:
        super().__init__()
        self.hub = hub

    async def recv(self) -> VideoFrame:
        frame = await self.hub.wait_for_frame()
        image = frame.to_ndarray(format="bgr24")
        output = VideoFrame.from_ndarray(image, format="bgr24")
        output.pts, output.time_base = await self.next_timestamp()
        return output


class CameraStreamHub:
    def __init__(self, camera_id: int, rtsp_url: str) -> None:
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self._condition = asyncio.Condition()
        self._latest_frame: VideoFrame | None = None
        self._task: asyncio.Task | None = None
        self._stopped = False
        self._last_fall_event_at = 0.0
        self._last_zone_event_at = 0.0
        self._last_drift_event_at = 0.0
        self._last_inference_at = 0.0
        self._last_drift_check_at = 0.0

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._stopped = False
            self._task = asyncio.create_task(self._run(), name=f"camera-stream-hub-{self.camera_id}")

    async def stop(self) -> None:
        self._stopped = True
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task

    def create_video_track(self) -> VideoStreamTrack:
        self.start()
        return LatestFrameTrack(self)

    async def wait_for_frame(self) -> VideoFrame:
        self.start()
        async with self._condition:
            await self._condition.wait_for(lambda: self._latest_frame is not None or self._stopped)
            if self._latest_frame is None:
                raise RuntimeError("camera stream hub stopped before a frame was available")
            return self._latest_frame

    async def _run(self) -> None:
        while not self._stopped:
            player: MediaPlayer | None = None
            try:
                player = MediaPlayer(
                    self.rtsp_url,
                    options={
                        "rtsp_transport": "udp",
                        "stimeout": "5000000",
                        "rw_timeout": "5000000",
                    },
                )
                if player.video is None:
                    raise RuntimeError(f"Video track is not available from source: {self.rtsp_url}")

                print(f"[BARO][CAMERA_HUB] camera_id={self.camera_id} connected url={self.rtsp_url}")
                while not self._stopped:
                    frame = await player.video.recv()
                    async with self._condition:
                        self._latest_frame = frame
                        self._condition.notify_all()
                    await self._analyze_frame_if_needed(frame)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                print(f"[BARO][CAMERA_HUB][ERROR] camera_id={self.camera_id} {exc}")
                await asyncio.sleep(3)
            finally:
                if player:
                    player.video and player.video.stop()
                    player.audio and player.audio.stop()

    async def _analyze_frame_if_needed(self, frame: VideoFrame) -> None:
        settings = get_settings()
        now = time.monotonic()
        should_infer = now - self._last_inference_at >= settings.yolo_inference_interval_seconds
        should_check_drift = now - self._last_drift_check_at >= settings.zone_drift_check_interval_seconds
        if not should_infer and not should_check_drift:
            return

        image = frame.to_ndarray(format="bgr24")

        if should_check_drift:
            self._last_drift_check_at = now
            flagged = await asyncio.to_thread(check_and_correct_drift, self.camera_id, image.copy())
            if flagged and now - self._last_drift_event_at >= settings.zone_drift_event_cooldown_seconds:
                self._last_drift_event_at = now
                record_camera_drift_event(camera_id=self.camera_id)

        if not should_infer:
            return

        self._last_inference_at = now
        detector = get_yolo_detector()
        detections = await asyncio.to_thread(detector.detect, image, settings.yolo_confidence)
        fall_detections = []
        person_detections = []
        for detection in detections:
            torso_angle, aspect_ratio = pose_metrics(detection)
            if is_fall_detection(detection, torso_angle, aspect_ratio):
                fall_detections.append(detection)
            if detection.class_name == "person":
                person_detections.append(detection)

        if fall_detections and now - self._last_fall_event_at >= settings.fall_event_cooldown_seconds:
            self._last_fall_event_at = now
            record_fall_detected_event(camera_id=self.camera_id)

        if not person_detections:
            return

        frame_height, frame_width = image.shape[:2]
        matched_zone = None
        for detection in person_detections:
            matched_zone = find_zone_for_point(self.camera_id, *self._foot_point(detection), frame_width, frame_height)
            if matched_zone is not None:
                break
        if matched_zone is None:
            return

        if now - self._last_zone_event_at < settings.zone_intrusion_cooldown_seconds:
            return

        self._last_zone_event_at = now
        record_zone_intrusion_event(
            camera_id=self.camera_id,
            zone_id=matched_zone.id,
            zone_type=matched_zone.zone_type,
        )

    def _foot_point(self, detection) -> tuple[float, float]:
        x1, _, x2, y2 = detection.box
        return (x1 + x2) / 2, y2


_hubs: dict[int, CameraStreamHub] = {}


def start_camera_hub(camera_id: int, rtsp_url: str) -> CameraStreamHub:
    existing = _hubs.get(camera_id)
    if existing and existing.rtsp_url == rtsp_url:
        existing.start()
        return existing

    if existing:
        asyncio.create_task(existing.stop())

    hub = CameraStreamHub(camera_id, rtsp_url)
    _hubs[camera_id] = hub
    hub.start()
    return hub


def get_camera_hub(camera_id: int, rtsp_url: str) -> CameraStreamHub:
    hub = _hubs.get(camera_id)
    if hub is None or hub.rtsp_url != rtsp_url:
        return start_camera_hub(camera_id, rtsp_url)
    hub.start()
    return hub


async def stop_camera_hub(camera_id: int) -> None:
    hub = _hubs.pop(camera_id, None)
    if hub:
        await hub.stop()


async def stop_all_camera_hubs() -> None:
    await asyncio.gather(*(hub.stop() for hub in list(_hubs.values())), return_exceptions=True)
    _hubs.clear()
