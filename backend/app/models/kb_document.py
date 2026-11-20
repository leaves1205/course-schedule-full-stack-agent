from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class KbDocument(Base):
    __tablename__ = "kb_documents"
    __table_args__ = {"comment": "Knowledge base documents"}

    original_name: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, comment="Original filename"
    )
    disk_name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Filename on disk"
    )
    rel_path: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="Path relative to data/kb"
    )
    size: Mapped[int] = mapped_column(Integer, nullable=False, comment="Size in bytes")
    ext: Mapped[str] = mapped_column(String(20), nullable=False, comment="File extension")
