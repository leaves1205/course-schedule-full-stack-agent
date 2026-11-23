from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.validators import NewPassword, Username


class UserResponse(BaseModel):
    id: int
    username: str
    name: str
    role: str
    email: str | None = None
    phone: str | None = None
    avatar: str | None = None
    status: int

    model_config = ConfigDict(from_attributes=True)


# Field limits match the 50-character database columns, so oversized input is a 422 rather than a database error.
class UserCreateRequest(BaseModel):
    username: Username
    password: NewPassword
    name: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=50)
    phone: str | None = Field(default=None, max_length=50)
    avatar: str | None = Field(default=None, max_length=50)
    role: Literal["student", "admin"] = "student"
    status: Literal[0, 1] = 1


class UserUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=50)
    phone: str | None = Field(default=None, max_length=50)
    avatar: str | None = Field(default=None, max_length=50)
    role: Literal["student", "admin"] | None = None
    status: Literal[0, 1] | None = None


class PasswordUpdateRequest(BaseModel):
    """Password change request parameters."""

    old_password: str
    new_password: NewPassword
