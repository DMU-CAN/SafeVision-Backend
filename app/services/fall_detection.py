import math

from app.core.config import get_settings
from app.services.detection_types import Detection, Keypoint


def pose_metrics(detection: Detection) -> tuple[float | None, float | None]:
    x1, y1, x2, y2 = detection.box
    width = max(x2 - x1, 1.0)
    height = max(y2 - y1, 1.0)
    aspect_ratio = width / height

    if detection.class_name != "person" or not get_settings().fall_detection_enabled:
        return None, aspect_ratio

    torso_angle = torso_angle_from_vertical(detection.keypoints)
    return torso_angle, aspect_ratio


def is_fall_detection(detection: Detection, torso_angle: float | None, aspect_ratio: float | None) -> bool:
    settings = get_settings()
    return (
        detection.class_name == "person"
        and torso_angle is not None
        and aspect_ratio is not None
        and torso_angle >= settings.fall_pose_angle_threshold
        and aspect_ratio >= settings.fall_aspect_ratio_threshold
    )


def torso_angle_from_vertical(keypoints: list[Keypoint]) -> float | None:
    left_shoulder = visible_keypoint(keypoints, 5)
    right_shoulder = visible_keypoint(keypoints, 6)
    left_hip = visible_keypoint(keypoints, 11)
    right_hip = visible_keypoint(keypoints, 12)

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


def visible_keypoint(keypoints: list[Keypoint], index: int) -> Keypoint | None:
    if index >= len(keypoints):
        return None
    keypoint = keypoints[index]
    return keypoint if keypoint.confidence >= 0.3 else None
