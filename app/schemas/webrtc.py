from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class WebRTCOfferRequest(BaseModel):
    sdp: str
    type: Literal["offer"] = "offer"
    camera_id: int = Field(alias="cameraId")
    yolo_confidence: Optional[float] = Field(default=None, alias="yoloConfidence")

    model_config = ConfigDict(populate_by_name=True)


class WebRTCAnswerResponse(BaseModel):
    sdp: str
    type: Literal["answer"] = "answer"
    session_id: str = Field(serialization_alias="sessionId")


class WebRTCSessionResponse(BaseModel):
    session_id: str = Field(serialization_alias="sessionId")
    state: str
