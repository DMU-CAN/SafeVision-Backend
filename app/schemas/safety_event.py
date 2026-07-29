from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SafetyEventResponse(BaseModel):
    id: int
    camera_id: Optional[int] = Field(serialization_alias="cameraId")
    equipment_id: Optional[int] = Field(serialization_alias="equipmentId")
    zone_id: Optional[int] = Field(serialization_alias="zoneId")
    event_type: str = Field(serialization_alias="eventType")
    event_level: int = Field(serialization_alias="eventLevel")
    clip_path: Optional[str] = Field(default=None, serialization_alias="clipPath")
    created_at: datetime = Field(serialization_alias="createdAt")

    model_config = ConfigDict(from_attributes=True)
