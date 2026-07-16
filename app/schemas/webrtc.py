from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


SourceKind = Literal["test_pattern", "rtsp", "webcam", "file"]


class CameraSourceRequest(BaseModel):
    kind: SourceKind = "test_pattern"
    url: Optional[str] = None
    device_index: Optional[int] = Field(default=None, alias="deviceIndex")

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
