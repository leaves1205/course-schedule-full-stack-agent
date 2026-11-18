from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SemesterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    first_monday: date
    total_weeks: int = Field(ge=1, le=60)

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("first_monday")
    @classmethod
    def require_monday(cls, value: date) -> date:
        if value.weekday() != 0:
            raise ValueError("The first teaching week must start on a Monday.")
        return value


class SemesterResponse(SemesterRequest):
    id: int
    end_date: date
    rule_count: int = 0
