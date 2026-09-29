"""Pydantic schemas for authentication endpoints."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    email: str | None = None
    department: str | None = None
    is_active: bool
    created_date: datetime | None = None
    last_login: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class ESignRequest(BaseModel):
    password: str
    comments: str | None = None
