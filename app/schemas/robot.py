from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.datetime_utils import UtcDatetime


RobotStatus = Literal["IDLE", "DISPATCHED", "OFFLINE"]
PtzDirection = Literal["up", "down", "left", "right", "zoomIn", "zoomOut", "stop"]


class RobotCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    control_address: str = Field(alias="controlAddress", min_length=1, max_length=100)
    camera_rtsp_url: str = Field(alias="cameraRtspUrl", min_length=1, max_length=255)
    location_x: Optional[float] = Field(default=None, alias="locationX")
    location_y: Optional[float] = Field(default=None, alias="locationY")

    model_config = ConfigDict(populate_by_name=True)


class RobotRegisterRequest(BaseModel):
    """Sent by the robot itself on boot (see SafeVision-Robot's register_client.py)
    rather than filled in by hand — the backend just needs a stable identity
    (hardware_id, e.g. its Pi's MAC address) to upsert against. control_address
    is stored for display/debugging only — actual commands go over the
    robot's WebSocket connection (see /robots/ws), not this address, since
    robots may be behind NAT the backend can't dial into."""

    hardware_id: str = Field(alias="hardwareId", min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=100)
    control_address: str = Field(alias="controlAddress", min_length=1, max_length=100)
    camera_rtsp_url: str = Field(alias="cameraRtspUrl", min_length=1, max_length=255)

    model_config = ConfigDict(populate_by_name=True)


class RobotUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    control_address: Optional[str] = Field(default=None, alias="controlAddress", min_length=1, max_length=100)
    camera_rtsp_url: Optional[str] = Field(default=None, alias="cameraRtspUrl", min_length=1, max_length=255)
    location_x: Optional[float] = Field(default=None, alias="locationX")
    location_y: Optional[float] = Field(default=None, alias="locationY")
    status: Optional[RobotStatus] = None

    model_config = ConfigDict(populate_by_name=True)


class RobotResponse(BaseModel):
    id: int
    hardware_id: Optional[str] = Field(default=None, serialization_alias="hardwareId")
    name: str
    control_address: str = Field(serialization_alias="controlAddress")
    camera_rtsp_url: str = Field(serialization_alias="cameraRtspUrl")
    location_x: Optional[float] = Field(default=None, serialization_alias="locationX")
    location_y: Optional[float] = Field(default=None, serialization_alias="locationY")
    status: str
    created_at: UtcDatetime = Field(serialization_alias="createdAt")

    model_config = ConfigDict(from_attributes=True)


class RobotPtzRequest(BaseModel):
    direction: PtzDirection


class RobotDispatchRequest(BaseModel):
    safety_event_id: Optional[int] = Field(default=None, alias="safetyEventId")

    model_config = ConfigDict(populate_by_name=True)


class RobotDispatchResponse(BaseModel):
    id: int
    robot_id: int = Field(serialization_alias="robotId")
    safety_event_id: Optional[int] = Field(default=None, serialization_alias="safetyEventId")
    target_x: Optional[float] = Field(default=None, serialization_alias="targetX")
    target_y: Optional[float] = Field(default=None, serialization_alias="targetY")
    dispatched_at: UtcDatetime = Field(serialization_alias="dispatchedAt")

    model_config = ConfigDict(from_attributes=True)
