from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


SourceKind = Literal["test_pattern", "rtsp", "webcam", "file", "ip_camera"]


class CameraSourceRequest(BaseModel):
    kind: SourceKind = "test_pattern"
    url: Optional[str] = None
    device_index: Optional[int] = Field(default=None, alias="deviceIndex")
    yolo_enabled: Optional[bool] = Field(default=None, alias="yoloEnabled")
    yolo_confidence: Optional[float] = Field(default=None, alias="yoloConfidence")

    model_config = ConfigDict(populate_by_name=True)


class WebRTCOfferRequest(BaseModel):
    sdp: str
    type: Literal["offer"] = "offer"
    camera_id: Optional[int] = Field(default=None, alias="cameraId")
    source: Optional[CameraSourceRequest] = None

    model_config = ConfigDict(populate_by_name=True)


class WebRTCAnswerResponse(BaseModel):
    sdp: str
    type: Literal["answer"] = "answer"
    session_id: str = Field(serialization_alias="sessionId")


class WebRTCSessionResponse(BaseModel):
    session_id: str = Field(serialization_alias="sessionId")
    state: str
