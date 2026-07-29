from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.datetime_utils import UtcDatetime


Role = Literal["ADMIN", "MANAGER", "OPERATOR"]


class SignupRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=50)
    phone_number: str = Field(alias="phoneNumber", min_length=1, max_length=20)
    department: str = Field(min_length=1, max_length=100)
    role: Role = "OPERATOR"

    model_config = ConfigDict(populate_by_name=True)


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str = Field(alias="refreshToken")

    model_config = ConfigDict(populate_by_name=True)


class UserResponse(BaseModel):
    id: int
    username: str
    name: str
    phone_number: str = Field(serialization_alias="phoneNumber")
    department: str
    role: str
    created_at: UtcDatetime = Field(serialization_alias="createdAt")

    model_config = ConfigDict(from_attributes=True)


class TokenBundle(BaseModel):
    access_token: str = Field(serialization_alias="accessToken")
    refresh_token: str = Field(serialization_alias="refreshToken")
    expires_in: int = Field(serialization_alias="expiresIn")
    user: UserResponse


class AccessTokenResponse(BaseModel):
    access_token: str = Field(serialization_alias="accessToken")
    expires_in: int = Field(serialization_alias="expiresIn")
