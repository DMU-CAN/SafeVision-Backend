from dataclasses import dataclass


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
