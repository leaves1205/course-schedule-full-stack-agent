"""Semester scheduling: semesters, weekly rules, and per-class exception columns.

Additive and repeatable. Existing schedule rows and their original period text are preserved, and
parseable legacy periods such as "1-2" are backfilled into numeric bounds. Tables, columns and indexes
that a database already has (from the startup upgrade used before Alembic) are not created again.

Revision ID: 0002
Revises: 0001
"""
import re

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

MYSQL = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}

# A frozen copy of the period grammar: a migration must not change when application code does.
PERIOD = re.compile(r"^(\d{1,2})(?:\s*[-–—]\s*(\d{1,2}))?$")


def _id() -> sa.Column:
    return sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, comment="Primary key ID")


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("create_time", sa.DateTime(), nullable=False, comment="Created at"),
        sa.Column("update_time", sa.DateTime(), nullable=False, comment="Updated at"),
    ]


def upgrade() -> None:
    bind = op.get_bind()
    sqlite = bind.dialect.name == "sqlite"
    tables = set(sa.inspect(bind).get_table_names())

    if "semesters" not in tables:
        op.create_table(
            "semesters",
            _id(),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("first_monday", sa.Date(), nullable=False),
            sa.Column("total_weeks", sa.Integer(), nullable=False),
            *_timestamps(),
            sa.UniqueConstraint("name"),
            **MYSQL,
        )

    if "schedule_rules" not in tables:
        op.create_table(
            "schedule_rules",
            _id(),
            sa.Column("semester_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("course_id", sa.Integer(), nullable=False),
            sa.Column("weekday", sa.Integer(), nullable=False),
            sa.Column("start_week", sa.Integer(), nullable=False),
            sa.Column("end_week", sa.Integer(), nullable=False),
            sa.Column("start_period", sa.Integer(), nullable=False),
            sa.Column("end_period", sa.Integer(), nullable=False),
            sa.Column("location", sa.String(100), nullable=False),
            *_timestamps(),
            sa.ForeignKeyConstraint(["semester_id"], ["semesters.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["course_id"], ["course.id"]),
            sa.UniqueConstraint(
                "semester_id", "user_id", "course_id", "weekday", "start_week", "end_week",
                "start_period", "end_period", name="uq_schedule_rule_pattern",
            ),
            **MYSQL,
        )
        op.create_index("ix_schedule_rules_semester_id", "schedule_rules", ["semester_id"])
        op.create_index("ix_schedule_rules_user_id", "schedule_rules", ["user_id"])

    columns = {column["name"] for column in sa.inspect(bind).get_columns("schedules")}
    for name, type_ in (("source_date", sa.Date()), ("start_period", sa.Integer()), ("end_period", sa.Integer())):
        if name not in columns:
            op.add_column("schedules", sa.Column(name, type_, nullable=True))
    for name in ("is_exception", "is_cancelled"):
        if name not in columns:
            op.add_column(
                "schedules", sa.Column(name, sa.Boolean(), nullable=False, server_default=sa.false())
            )
    if "rule_id" not in columns:
        if sqlite:
            # SQLite cannot add a constraint afterwards, but it accepts a reference on a new nullable column.
            op.execute("ALTER TABLE schedules ADD COLUMN rule_id INTEGER REFERENCES schedule_rules(id)")
        else:
            op.add_column("schedules", sa.Column("rule_id", sa.Integer(), nullable=True))
    if not sqlite:
        foreign_keys = sa.inspect(bind).get_foreign_keys("schedules")
        if not any(key["constrained_columns"] == ["rule_id"] for key in foreign_keys):
            op.create_foreign_key("fk_schedule_rule", "schedules", "schedule_rules", ["rule_id"], ["id"])

    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("schedules")}
    for name, columns_, unique in (
        ("ix_schedule_student_date", ["user_id", "class_date"], False),
        ("uq_schedule_rule_date", ["rule_id", "class_date"], True),
        ("uq_schedule_rule_source", ["rule_id", "source_date"], True),
    ):
        if name not in indexes:
            op.create_index(name, "schedules", columns_, unique=unique)

    legacy = bind.execute(
        sa.text("SELECT id, period FROM schedules WHERE start_period IS NULL OR end_period IS NULL")
    ).all()
    for schedule_id, period in legacy:
        match = PERIOD.fullmatch((period or "").strip())
        if not match:
            # Keep unparseable text such as "morning"; conflict checks treat it conservatively.
            continue
        start, end = int(match[1]), int(match[2] or match[1])
        if not 1 <= start <= end <= 30:
            continue
        bind.execute(
            sa.text("UPDATE schedules SET start_period=:start, end_period=:end WHERE id=:id"),
            {"start": start, "end": end, "id": schedule_id},
        )


def downgrade() -> None:
    """Remove semester scheduling. Generated classes keep their rows; their rule links are dropped.

    Exercised on SQLite by the test suite; review it against a copy of a MySQL database before relying on it.
    """
    bind = op.get_bind()
    for name in ("uq_schedule_rule_source", "uq_schedule_rule_date", "ix_schedule_student_date"):
        op.drop_index(name, table_name="schedules")
    if bind.dialect.name != "sqlite":
        op.drop_constraint("fk_schedule_rule", "schedules", type_="foreignkey")
    with op.batch_alter_table("schedules") as batch:
        for name in ("is_cancelled", "is_exception", "end_period", "start_period", "source_date", "rule_id"):
            batch.drop_column(name)
    op.drop_table("schedule_rules")
    op.drop_table("semesters")
