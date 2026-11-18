from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StudyPlanCreateRequest(BaseModel):
    """Save a study plan."""

    content: str

    model_config = ConfigDict(str_strip_whitespace=True)


class StudyPlanResponse(BaseModel):
    """Study plan response."""

    id: int
    content: str
    created_time: datetime | None = None
    model_config = ConfigDict(from_attributes=True)
