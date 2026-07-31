import cv2

from app.core.config import get_settings
from app.services.detection_types import Detection, Keypoint


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


def draw_detection(
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

    draw_pose(image, detection.keypoints, color)


def draw_pose(image, keypoints: list[Keypoint], color) -> None:
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
