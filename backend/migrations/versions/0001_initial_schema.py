"""Initial schema: users, course, study_plan, kb_documents and the original schedules table.

Before Alembic the application created its tables on startup, so a database that is being put under
Alembic for the first time may already contain these tables with real data. Every table is therefore
created only when it is missing, and existing tables are left exactly as they are.

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# Ignored by every dialect except MySQL, where it matches the character set the README requires.
MYSQL = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}


def _id() -> sa.Column:
    return sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, comment="Primary key ID")


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("create_time", sa.DateTime(), nullable=False, comment="Created at"),
        sa.Column("update_time", sa.DateTime(), nullable=False, comment="Updated at"),
    ]


def upgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())

    if "users" not in existing:
        op.create_table(
            "users",
            _id(),
            sa.Column("username", sa.String(50), nullable=False, comment="Username"),
            sa.Column("password", sa.String(255), nullable=False, comment="Password"),
            sa.Column("name", sa.String(50), nullable=False, comment="Name"),
            sa.Column("role", sa.String(50), nullable=False, comment="Role: student = student, admin = administrator"),
            sa.Column("email", sa.String(50), nullable=True, comment="Email"),
            sa.Column("phone", sa.String(50), nullable=True, comment="Phone number"),
            sa.Column("avatar", sa.String(50), nullable=True, comment="Avatar"),
            sa.Column("status", sa.Integer(), nullable=False, comment="Status: 0 = disabled, 1 = active"),
            *_timestamps(),
            sa.UniqueConstraint("username"),
            comment="User information table",
            **MYSQL,
        )

    if "course" not in existing:
        op.create_table(
            "course",
            _id(),
            sa.Column("name", sa.String(50), nullable=False, comment="Course name"),
            sa.Column("code", sa.String(50), nullable=False, comment="Course code"),
            sa.Column("description", sa.String(255), nullable=False, comment="Course description"),
            sa.Column("status", sa.Integer(), nullable=False, comment="Status: 0 = inactive, 1 = active"),
            *_timestamps(),
            sa.UniqueConstraint("code"),
            comment="Course information table",
            **MYSQL,
        )

    if "study_plan" not in existing:
        op.create_table(
            "study_plan",
            _id(),
            sa.Column("user_id", sa.Integer(), nullable=False, comment="User ID"),
            sa.Column("content", sa.Text(), nullable=False, comment="Study plan content"),
            *_timestamps(),
            comment="Study plan table",
            **MYSQL,
        )

    if "kb_documents" not in existing:
        op.create_table(
            "kb_documents",
            _id(),
            sa.Column("original_name", sa.String(255), nullable=False, comment="Original filename"),
            sa.Column("disk_name", sa.String(255), nullable=False, comment="Filename on disk"),
            sa.Column("rel_path", sa.String(512), nullable=False, comment="Path relative to data/kb"),
            sa.Column("size", sa.Integer(), nullable=False, comment="Size in bytes"),
            sa.Column("ext", sa.String(20), nullable=False, comment="File extension"),
            *_timestamps(),
            sa.UniqueConstraint("original_name"),
            comment="Knowledge base documents",
            **MYSQL,
        )

    if "schedules" not in existing:
        # The shape before semester scheduling; revision 0002 adds the rule, exception and period columns.
        op.create_table(
            "schedules",
            _id(),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, comment="student ID"),
            sa.Column("class_date", sa.Date(), nullable=False, comment="course date"),
            sa.Column("period", sa.String(50), nullable=False, comment="course period"),
            sa.Column("course_id", sa.Integer(), sa.ForeignKey("course.id"), nullable=False, comment="course ID"),
            sa.Column("location", sa.String(100), nullable=True, comment="course location"),
            *_timestamps(),
            comment="Class schedule table",
            **MYSQL,
        )


def downgrade() -> None:
    for table in ("schedules", "kb_documents", "study_plan", "course", "users"):
        op.drop_table(table)
