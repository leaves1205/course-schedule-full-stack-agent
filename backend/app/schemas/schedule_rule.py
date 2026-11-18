from pydantic import BaseModel, ConfigDict, Field, model_validator


class WeeklyMeeting(BaseModel):
    weekday: int = Field(ge=1, le=7)
    start_period: int = Field(ge=1, le=30)
    end_period: int = Field(ge=1, le=30)
    location: str = Field(default="", max_length=100)

    model_config = ConfigDict(str_strip_whitespace=True)

    @model_validator(mode="after")
    def ordered_periods(self):
        if self.end_period < self.start_period:
            raise ValueError("The last period must not precede the first period.")
        return self


class ScheduleGenerateRequest(BaseModel):
    semester_id: int = Field(gt=0)
    user_id: int = Field(gt=0)
    course_id: int = Field(gt=0)
    start_week: int = Field(ge=1, le=60)
    end_week: int = Field(ge=1, le=60)
    meetings: list[WeeklyMeeting] = Field(min_length=1, max_length=35)

    @model_validator(mode="after")
    def ordered_weeks(self):
        if self.end_week < self.start_week:
            raise ValueError("The last week must not precede the first week.")
        return self


class ScheduleRuleResponse(WeeklyMeeting):
    id: int
    semester_id: int
    semester_name: str
    user_id: int
    user_name: str
    username: str
    course_id: int
    course_name: str
    start_week: int
    end_week: int
    session_count: int = 0
    exception_count: int = 0
    cancelled_count: int = 0


class GenerationResponse(BaseModel):
    created_count: int
    preserved_count: int
    rule_ids: list[int]
