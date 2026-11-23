from pydantic import BaseModel, Field

from app.schemas.user import UserResponse
from app.schemas.validators import NewPassword, Username


class LoginRequest(BaseModel):
    username: str
    # Login accepts whatever password is stored so accounts created before the password policy still work.
    password: str


class LoginResponse(BaseModel):
    token: str
    user: UserResponse


class RegisterRequest(BaseModel):
    username: Username
    password: NewPassword
    name: str | None = Field(default=None, max_length=50)
