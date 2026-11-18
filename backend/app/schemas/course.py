from pydantic import BaseModel
from pydantic import ConfigDict


class CourseCreateRequest(BaseModel):
    """Create course request."""

    name: str
    code: str
    description: str | None = None
    status: int = 1


class CourseUpdateRequest(BaseModel):
    """Update course fields (optional)."""

    name: str | None = None
    code: str | None = None
    description: str | None = None
    status: int | None = None


class CourseResponse(BaseModel):
    """Course response data."""

    id: int
    name: str
    code: str
    description: str | None = None
    status: int

    model_config = ConfigDict(from_attributes=True)
