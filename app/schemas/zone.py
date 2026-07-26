from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ZonePoint(BaseModel):
    x: float
    y: float


class ZoneCreate(BaseModel):
    name: str
    camera_id: Optional[int] = Field(default=None, alias="cameraId")
    points: list[ZonePoint]

    model_config = ConfigDict(populate_by_name=True)


class ZoneResponse(BaseModel):
    id: int
    camera_id: Optional[int] = Field(serialization_alias="cameraId")
    name: str
    points: list[ZonePoint]
    is_active: bool = Field(serialization_alias="isActive")

    model_config = ConfigDict(from_attributes=True)
