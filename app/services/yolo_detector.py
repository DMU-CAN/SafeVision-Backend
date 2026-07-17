import asyncio
from dataclasses import dataclass
from functools import lru_cache

import cv2
from aiortc import VideoStreamTrack
from av import VideoFrame

from app.core.config import get_settings


@dataclass(frozen=True)
class Detection:
    box: list[float]
    class_name: str
    confidence: float


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
            class_names = self.model.names

            for box, class_id, score in zip(xyxy_list, class_ids, confidences):
                detections.append(
                    Detection(
                        box=[float(value) for value in box],
                        class_name=class_names[int(class_id)],
                        confidence=float(score),
                    )
                )

        return detections


@lru_cache(maxsize=1)
def get_yolo_detector() -> YoloDetector:
    settings = get_settings()
    return YoloDetector(settings.yolo_model_path)


class YoloAnnotatedTrack(VideoStreamTrack):
    def __init__(self, source_track: VideoStreamTrack, confidence: float) -> None:
        super().__init__()
        self.source_track = source_track
        self.confidence = confidence

    async def recv(self) -> VideoFrame:
        frame = await self.source_track.recv()
        image = frame.to_ndarray(format="bgr24")
        detector = get_yolo_detector()
        detections = await asyncio.to_thread(detector.detect, image, self.confidence)

        for detection in detections:
            x1, y1, x2, y2 = [int(value) for value in detection.box]
            label = f"{detection.class_name} {detection.confidence:.2f}"
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                image,
                label,
                (x1, max(y1 - 8, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )

        annotated_frame = VideoFrame.from_ndarray(image, format="bgr24")
        annotated_frame.pts = frame.pts
        annotated_frame.time_base = frame.time_base
        return annotated_frame
