from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.datetime_utils import UtcDatetime


ControlProtocol = Literal["SERIAL", "NETWORK"]


class EquipmentCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    control_protocol: ControlProtocol = Field(alias="controlProtocol")
    control_address: str = Field(alias="controlAddress", min_length=1, max_length=100)

    model_config = ConfigDict(populate_by_name=True)


class EquipmentUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    control_protocol: Optional[ControlProtocol] = Field(default=None, alias="controlProtocol")
    control_address: Optional[str] = Field(default=None, alias="controlAddress", min_length=1, max_length=100)

    model_config = ConfigDict(populate_by_name=True)


class EquipmentResponse(BaseModel):
    id: int
    name: str
    control_protocol: str = Field(serialization_alias="controlProtocol")
    control_address: str = Field(serialization_alias="controlAddress")
    updated_at: UtcDatetime = Field(serialization_alias="updatedAt")

    model_config = ConfigDict(from_attributes=True)
