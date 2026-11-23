from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Text
from app.database import Base


class StudyPlan(Base):
    __tablename__ = "study_plan"
    __table_args__ = {"comment": "Study plan table"}

    user_id: Mapped[int] = mapped_column(comment="User ID", nullable=False)
    content: Mapped[str] = mapped_column(Text, comment="Study plan content", nullable=False)
