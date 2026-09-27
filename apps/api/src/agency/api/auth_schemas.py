"""Request/response contracts for authentication."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BootstrapRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    org_name: str = Field(min_length=1, max_length=200)
    org_slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=120)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=256)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class MemberCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=256)
    role: Literal["owner", "operator", "reviewer"]


class AuthUserOut(BaseModel):
    id: str
    email: str
    is_active: bool


class MembershipOut(BaseModel):
    org_id: str
    org_name: str
    role: str


class MeResponse(BaseModel):
    user: AuthUserOut
    memberships: list[MembershipOut]


class AuthResponse(MeResponse):
    pass
