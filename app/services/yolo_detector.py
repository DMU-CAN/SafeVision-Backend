import asyncio
import time
from functools import lru_cache

from aiortc import VideoStreamTrack
from av import VideoFrame

from app.core.config import get_settings
from app.services.detection_types import Detection, Keypoint
from app.services.fall_detection import is_fall_detection, pose_metrics
from app.services.safety_event_logger import (
    record_camera_drift_event,
    record_fall_detected_event,
    record_zone_intrusion_event,
)
from app.services.yolo_annotation import draw_detection
from app.services.zone_calibration import check_and_correct_drift
from app.services.zone_service import find_zone_for_point


class YoloDetector:
    def __init__(self, model_path: str) -> None:
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError("ultralytics is required when YOLO detection is enabled") from exc

        self.model = YOLO(model_path)

    def detect(self, image, confidence: float) -> list[Detection]:
        results = self.model(image, conf=confidence, verbose=False)
        detections: list[Detection] = []

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            class_ids = boxes.cls.tolist()
            confidences = boxes.conf.tolist()
            xyxy_list = boxes.xyxy.tolist()
            keypoints_list = self._extract_keypoints(result)
            class_names = self.model.names

            for index, (box, class_id, score) in enumerate(zip(xyxy_list, class_ids, confidences)):
                detections.append(
                    Detection(
                        box=[float(value) for value in box],
                        class_name=class_names[int(class_id)],
                        confidence=float(score),
                        keypoints=keypoints_list[index] if index < len(keypoints_list) else [],
                    )
                )

        return detections

    def _extract_keypoints(self, result) -> list[list[Keypoint]]:
        if result.keypoints is None:
            return []

        xy_list = result.keypoints.xy.tolist()
        conf_tensor = result.keypoints.conf
        conf_list = conf_tensor.tolist() if conf_tensor is not None else []
        detections: list[list[Keypoint]] = []

        for person_index, person_points in enumerate(xy_list):
            person_conf = conf_list[person_index] if person_index < len(conf_list) else []
            keypoints: list[Keypoint] = []
            for point_index, point in enumerate(person_points):
                confidence = person_conf[point_index] if point_index < len(person_conf) else 1.0
                keypoints.append(Keypoint(x=float(point[0]), y=float(point[1]), confidence=float(confidence)))
            detections.append(keypoints)

        return detections


@lru_cache(maxsize=1)
def get_yolo_detector() -> YoloDetector:
    settings = get_settings()
    return YoloDetector(settings.yolo_model_path)


class YoloAnnotatedTrack(VideoStreamTrack):
    def __init__(self, source_track: VideoStreamTrack, confidence: float, camera_id: int | None = None) -> None:
        super().__init__()
        self.source_track = source_track
        self.confidence = confidence
        self.camera_id = camera_id
        self.last_fall_event_at = 0.0
        self.last_zone_event_at = 0.0
        self.last_drift_event_at = 0.0
        self.last_inference_at = 0.0
        self.last_drift_check_at = 0.0
        self.cached_detections: list[Detection] = []

    async def recv(self) -> VideoFrame:
        frame = await self.source_track.recv()
        image = frame.to_ndarray(format="bgr24")

        settings = get_settings()
        now = time.monotonic()
        # Every frame is still pulled from the source track above (so the
        # upstream reader never stalls/backs up), but the expensive
        # detect() call only runs a few times a second — frames in between
        # reuse the last detections instead of re-running inference.
        if now - self.last_inference_at >= settings.yolo_inference_interval_seconds:
            self.last_inference_at = now
            detector = get_yolo_detector()
            self.cached_detections = await asyncio.to_thread(detector.detect, image, self.confidence)

        # Runs against the clean (pre-annotation) frame, on its own slow
        # cadence — a bumped/vibrated camera mount is corrected (or flagged)
        # long before it matters, no need to check every frame.
        if self.camera_id is not None and now - self.last_drift_check_at >= settings.zone_drift_check_interval_seconds:
            self.last_drift_check_at = now
            flagged = await asyncio.to_thread(check_and_correct_drift, self.camera_id, image.copy())
            if flagged and now - self.last_drift_event_at >= settings.zone_drift_event_cooldown_seconds:
                self.last_drift_event_at = now
                record_camera_drift_event(camera_id=self.camera_id)

        fall_detections: list[Detection] = []
        person_detections: list[Detection] = []
        for detection in self.cached_detections:
            torso_angle, aspect_ratio = pose_metrics(detection)
            is_fall = is_fall_detection(detection, torso_angle, aspect_ratio)
            if is_fall:
                fall_detections.append(detection)
            if detection.class_name == "person":
                person_detections.append(detection)
            draw_detection(image, detection, is_fall, torso_angle, aspect_ratio)

        frame_height, frame_width = image.shape[:2]
        # Falls are recorded everywhere, independent of danger zones — a
        # collapse matters no matter where it happens. Zone intrusion is a
        # separate, zone-gated signal for anyone (fallen or not) standing
        # inside a configured danger zone.
        self._record_fall_event_if_needed(fall_detections)
        self._record_zone_intrusion_if_needed(person_detections, frame_width, frame_height)

        annotated_frame = VideoFrame.from_ndarray(image, format="bgr24")
        # Use our own monotonic timestamp for the outgoing WebRTC track
        # rather than propagating the source's pts/time_base verbatim —
        # source clocks (e.g. an RTSP stream's own timebase) can confuse
        # aiortc's encoder and result in a black/undecodable output.
        annotated_frame.pts, annotated_frame.time_base = await self.next_timestamp()
        return annotated_frame

    def _record_fall_event_if_needed(self, fall_detections: list[Detection]) -> None:
        if not fall_detections:
            return

        settings = get_settings()
        now = time.monotonic()
        if now - self.last_fall_event_at < settings.fall_event_cooldown_seconds:
            return

        self.last_fall_event_at = now
        record_fall_detected_event(camera_id=self.camera_id)

    def _record_zone_intrusion_if_needed(
        self, person_detections: list[Detection], frame_width: int, frame_height: int
    ) -> None:
        if not person_detections:
            return

        matched_zone = None
        for detection in person_detections:
            matched_zone = find_zone_for_point(self.camera_id, *self._foot_point(detection), frame_width, frame_height)
            if matched_zone is not None:
                break
        if matched_zone is None:
            return

        settings = get_settings()
        now = time.monotonic()
        if now - self.last_zone_event_at < settings.zone_intrusion_cooldown_seconds:
            return

        self.last_zone_event_at = now
        record_zone_intrusion_event(
            camera_id=self.camera_id,
            zone_id=matched_zone.id,
            zone_type=matched_zone.zone_type,
        )

    def _foot_point(self, detection: Detection) -> tuple[float, float]:
        x1, _, x2, y2 = detection.box
        return (x1 + x2) / 2, y2
