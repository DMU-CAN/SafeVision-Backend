import asyncio
import math
import time
from dataclasses import dataclass
from functools import lru_cache

import cv2
from aiortc import VideoStreamTrack
from av import VideoFrame

from app.core.config import get_settings
from app.services.safety_event_logger import record_fall_detected_event


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

    async def recv(self) -> VideoFrame:
        frame = await self.source_track.recv()
        image = frame.to_ndarray(format="bgr24")
        detector = get_yolo_detector()
        detections = await asyncio.to_thread(detector.detect, image, self.confidence)
        fall_detections = self._find_fall_detections(detections)
        self._record_fall_event_if_needed(fall_detections)

        for detection in detections:
            self._draw_detection(image, detection, detection in fall_detections)

        annotated_frame = VideoFrame.from_ndarray(image, format="bgr24")
        annotated_frame.pts = frame.pts
        annotated_frame.time_base = frame.time_base
        return annotated_frame

    def _draw_detection(self, image, detection: Detection, is_fall: bool) -> None:
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

    def _find_fall_detections(self, detections: list[Detection]) -> list[Detection]:
        settings = get_settings()
        if not settings.fall_detection_enabled:
            return []

        return [detection for detection in detections if self._is_pose_fall(detection)]

    def _is_pose_fall(self, detection: Detection) -> bool:
        if detection.class_name != "person":
            return False

        torso_angle = self._torso_angle_from_vertical(detection.keypoints)
        if torso_angle is None:
            return False

        x1, y1, x2, y2 = detection.box
        width = max(x2 - x1, 1.0)
        height = max(y2 - y1, 1.0)
        aspect_ratio = width / height
        settings = get_settings()

        return (
            torso_angle >= settings.fall_pose_angle_threshold
            and aspect_ratio >= settings.fall_aspect_ratio_threshold
        )

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
