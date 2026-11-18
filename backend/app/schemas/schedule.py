from datetime import date

from pydantic import BaseModel, ConfigDict


class ScheduleCreateRequest(BaseModel):
    """Administrator request to create a schedule."""

    user_id: int
    class_date: date
    period: str
    course_id: int
    location: str

    model_config = ConfigDict(str_strip_whitespace=True)


class ScheduleUpdateRequest(BaseModel):
    """Administrator request to update a schedule."""

    user_id: int | None = None
    class_date: date | None = None
    period: str | None = None
    course_id: int | None = None
    location: str | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class ScheduleResponse(BaseModel):
    """Schedule response with joined username, user name and course name for display."""

    id: int
    user_id: int
    username: str
    user_name: str
    class_date: date
    period: str
    course_id: int
    course_name: str
    location: str

    model_config = ConfigDict(from_attributes=True)
