import asyncio
import math
import time
from dataclasses import dataclass
from functools import lru_cache

import cv2
from aiortc import VideoStreamTrack
from av import VideoFrame

from app.core.config import get_settings
from app.services.safety_event_logger import (
    record_camera_drift_event,
    record_fall_detected_event,
    record_zone_intrusion_event,
)
from app.services.zone_calibration import check_and_correct_drift
from app.services.zone_service import find_zone_for_point


@dataclass(frozen=True)
class Keypoint:
    x: float
    y: float
    confidence: float


@dataclass(frozen=True)
class Detection:
    box: list[float]
    class_name: str
    confidence: float
    keypoints: list[Keypoint]


POSE_CONNECTIONS = [
    (5, 6),
    (5, 7),
    (7, 9),
    (6, 8),
    (8, 10),
    (5, 11),
    (6, 12),
    (11, 12),
    (11, 13),
    (13, 15),
    (12, 14),
    (14, 16),
]


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
            if flagged:
                record_camera_drift_event(camera_id=self.camera_id)

        fall_detections: list[Detection] = []
        person_detections: list[Detection] = []
        for detection in self.cached_detections:
            torso_angle, aspect_ratio = self._pose_metrics(detection)
            is_fall = (
                detection.class_name == "person"
                and torso_angle is not None
                and torso_angle >= settings.fall_pose_angle_threshold
                and aspect_ratio >= settings.fall_aspect_ratio_threshold
            )
            if is_fall:
                fall_detections.append(detection)
            if detection.class_name == "person":
                person_detections.append(detection)
            self._draw_detection(image, detection, is_fall, torso_angle, aspect_ratio)

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

    def _draw_detection(
        self,
        image,
        detection: Detection,
        is_fall: bool,
        torso_angle: float | None,
        aspect_ratio: float | None,
    ) -> None:
        x1, y1, x2, y2 = [int(value) for value in detection.box]
        color = (0, 0, 255) if is_fall else (0, 255, 0)
        label = f"FALL {detection.confidence:.2f}" if is_fall else f"{detection.class_name} {detection.confidence:.2f}"

        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            image,
            label,
            (x1, max(y1 - 8, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
            cv2.LINE_AA,
        )

        if detection.class_name == "person":
            settings = get_settings()
            angle_text = f"{torso_angle:.0f}deg" if torso_angle is not None else "n/a"
            ratio_text = f"{aspect_ratio:.2f}" if aspect_ratio is not None else "n/a"
            debug_text = (
                f"angle {angle_text}/{settings.fall_pose_angle_threshold:.0f} "
                f"ratio {ratio_text}/{settings.fall_aspect_ratio_threshold:.2f}"
            )
            cv2.putText(
                image,
                debug_text,
                (x1, min(y2 + 20, image.shape[0] - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 255),
                1,
                cv2.LINE_AA,
            )

        self._draw_pose(image, detection.keypoints, color)

    def _draw_pose(self, image, keypoints: list[Keypoint], color) -> None:
        for start_index, end_index in POSE_CONNECTIONS:
            if start_index >= len(keypoints) or end_index >= len(keypoints):
                continue
            start = keypoints[start_index]
            end = keypoints[end_index]
            if start.confidence < 0.3 or end.confidence < 0.3:
                continue
            cv2.line(image, (int(start.x), int(start.y)), (int(end.x), int(end.y)), color, 2, cv2.LINE_AA)

        for point in keypoints:
            if point.confidence >= 0.3:
                cv2.circle(image, (int(point.x), int(point.y)), 3, color, -1, cv2.LINE_AA)

    def _pose_metrics(self, detection: Detection) -> tuple[float | None, float | None]:
        x1, y1, x2, y2 = detection.box
        width = max(x2 - x1, 1.0)
        height = max(y2 - y1, 1.0)
        aspect_ratio = width / height

        if detection.class_name != "person" or not get_settings().fall_detection_enabled:
            return None, aspect_ratio

        torso_angle = self._torso_angle_from_vertical(detection.keypoints)
        return torso_angle, aspect_ratio

    def _torso_angle_from_vertical(self, keypoints: list[Keypoint]) -> float | None:
        left_shoulder = self._visible_keypoint(keypoints, 5)
        right_shoulder = self._visible_keypoint(keypoints, 6)
        left_hip = self._visible_keypoint(keypoints, 11)
        right_hip = self._visible_keypoint(keypoints, 12)

        if not all([left_shoulder, right_shoulder, left_hip, right_hip]):
            return None

        shoulder_x = (left_shoulder.x + right_shoulder.x) / 2
        shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
        hip_x = (left_hip.x + right_hip.x) / 2
        hip_y = (left_hip.y + right_hip.y) / 2
        dx = hip_x - shoulder_x
        dy = hip_y - shoulder_y

        if abs(dx) < 1 and abs(dy) < 1:
            return None

        return abs(math.degrees(math.atan2(dx, dy)))

    def _visible_keypoint(self, keypoints: list[Keypoint], index: int) -> Keypoint | None:
        if index >= len(keypoints):
            return None
        keypoint = keypoints[index]
        return keypoint if keypoint.confidence >= 0.3 else None

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
        record_zone_intrusion_event(camera_id=self.camera_id, zone_id=matched_zone.id)

    def _foot_point(self, detection: Detection) -> tuple[float, float]:
        x1, _, x2, y2 = detection.box
        return (x1 + x2) / 2, y2
