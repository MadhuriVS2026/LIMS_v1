"""Pydantic schemas for user management endpoints."""
from pydantic import BaseModel


class CreateUserRequest(BaseModel):
    username: str
    password: str
    full_name: str
    role: str
    email: str | None = None
    department: str | None = None


class UpdateUserRequest(BaseModel):
    full_name: str | None = None
    role: str | None = None
    email: str | None = None
    department: str | None = None
    is_active: bool | None = None
