from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


CameraStatus = Literal["ONLINE", "OFFLINE", "MAINTENANCE"]


class CameraCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    rtsp_url: str = Field(alias="rtspUrl", min_length=1, max_length=255)
    location: str = Field(min_length=1, max_length=255)
    status: CameraStatus = "ONLINE"

    model_config = ConfigDict(populate_by_name=True)


class CameraUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    rtsp_url: Optional[str] = Field(default=None, alias="rtspUrl", min_length=1, max_length=255)
    location: Optional[str] = Field(default=None, min_length=1, max_length=255)
    status: Optional[CameraStatus] = None

    model_config = ConfigDict(populate_by_name=True)


class CameraResponse(BaseModel):
    id: int
    name: str
    rtsp_url: str = Field(serialization_alias="rtspUrl")
    location: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class StreamUrlResponse(BaseModel):
    camera_id: int = Field(serialization_alias="cameraId")
    stream_url: str = Field(serialization_alias="streamUrl")
