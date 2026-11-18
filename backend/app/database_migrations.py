"""Add semester scheduling fields to existing MySQL/SQLite installations without deleting data."""
from sqlalchemy import inspect, text
from sqlalchemy.schema import AddConstraint

from app.database import Base
from app.models import Schedule
from app.services.schedule_validation import parse_period
from app.common.exceptions import BusinessException


def initialize_database(engine):
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        dialect = connection.dialect.name
        columns = {column["name"] for column in inspect(connection).get_columns("schedules")}
        definitions = {
            "rule_id": "INTEGER REFERENCES schedule_rules(id)" if dialect == "sqlite" else "INTEGER NULL",
            "source_date": "DATE", "start_period": "INTEGER", "end_period": "INTEGER",
            "is_exception": "BOOLEAN NOT NULL DEFAULT 0", "is_cancelled": "BOOLEAN NOT NULL DEFAULT 0",
        }
        for name, definition in definitions.items():
            if name not in columns:
                connection.execute(text(f"ALTER TABLE schedules ADD COLUMN {name} {definition}"))
        if dialect == "mysql":
            foreign_keys = inspect(connection).get_foreign_keys("schedules")
            if not any(key["constrained_columns"] == ["rule_id"] for key in foreign_keys):
                constraint = next(key for key in Schedule.__table__.foreign_key_constraints if key.name == "fk_schedule_rule")
                connection.execute(AddConstraint(constraint))
        for index in Schedule.__table__.indexes:
            index.create(bind=connection, checkfirst=True)
        legacy = connection.execute(text(
            "SELECT id, period FROM schedules WHERE start_period IS NULL OR end_period IS NULL"
        )).all()
        for schedule_id, period in legacy:
            try:
                start, end = parse_period(period)
            except BusinessException:
                # Preserve legacy text; later conflict checks reject ambiguous dates conservatively.
                continue
            connection.execute(text(
                "UPDATE schedules SET start_period=:start, end_period=:end WHERE id=:id"
            ), {"start": start, "end": end, "id": schedule_id})
