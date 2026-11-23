"""Alembic migrations: fresh install, upgrade of pre-Alembic databases, reversibility and model drift."""

import unittest

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers the tables on Base.metadata)
from app import db_migrate
from app.database import Base

APPLICATION_TABLES = {
    "users", "course", "study_plan", "kb_documents", "schedules", "semesters", "schedule_rules",
}


def memory_engine():
    return create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)


def table_names(connection) -> set[str]:
    return set(inspect(connection).get_table_names()) - {"alembic_version"}


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = memory_engine()
        self.addCleanup(self.engine.dispose)

    def upgrade(self, revision="head"):
        with self.engine.begin() as connection:
            db_migrate.upgrade(connection, revision)

    def current_revision(self):
        with self.engine.connect() as connection:
            return connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()

    def test_there_is_exactly_one_head(self):
        heads = ScriptDirectory.from_config(db_migrate.alembic_config()).get_heads()
        self.assertEqual(heads, ["0002"])

    def test_fresh_database_matches_the_models(self):
        """Fails when a model changes without a migration, so the two cannot drift apart."""
        self.upgrade()
        with self.engine.connect() as connection:
            self.assertEqual(table_names(connection), APPLICATION_TABLES)
            context = MigrationContext.configure(
                connection, opts={"compare_type": True, "compare_server_default": True}
            )
            self.assertEqual(compare_metadata(context, Base.metadata), [])

    def test_upgrade_is_repeatable(self):
        self.upgrade()
        self.upgrade()
        self.assertEqual(self.current_revision(), "0002")

    def test_downgrade_then_upgrade_round_trips(self):
        self.upgrade()
        with self.engine.begin() as connection:
            db_migrate.downgrade(connection, "0001")
        with self.engine.connect() as connection:
            self.assertNotIn("schedule_rules", table_names(connection))
            columns = {column["name"] for column in inspect(connection).get_columns("schedules")}
            self.assertEqual(
                columns,
                {"id", "user_id", "class_date", "period", "course_id", "location", "create_time", "update_time"},
            )
        with self.engine.begin() as connection:
            db_migrate.downgrade(connection, "base")
        with self.engine.connect() as connection:
            self.assertEqual(table_names(connection), set())
        self.upgrade()
        with self.engine.connect() as connection:
            self.assertEqual(table_names(connection), APPLICATION_TABLES)

    def test_legacy_schedules_table_keeps_its_rows_and_gains_numeric_periods(self):
        """A database from before semester scheduling: only the old schedules table exists."""
        with self.engine.begin() as connection:
            connection.execute(text("""CREATE TABLE schedules (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, course_id INTEGER NOT NULL,
                class_date DATE NOT NULL, period VARCHAR(50) NOT NULL, location VARCHAR(100),
                create_time DATETIME NOT NULL, update_time DATETIME NOT NULL
            )"""))
            connection.execute(text("""INSERT INTO schedules VALUES
                (11,2,1,'2026-08-03','1–2','A201','2026-07-01 10:00:00','2026-07-01 10:00:00'),
                (12,2,1,'2026-08-04','morning','B101','2026-07-01 10:00:00','2026-07-01 10:00:00'),
                (13,2,1,'2026-08-05','7','C301','2026-07-01 10:00:00','2026-07-01 10:00:00'),
                (14,2,1,'2026-08-06','0-2','D401','2026-07-01 10:00:00','2026-07-01 10:00:00')"""))
        self.upgrade()
        self.upgrade()
        with self.engine.connect() as connection:
            rows = connection.execute(text(
                "SELECT id, period, location, start_period, end_period, rule_id, is_cancelled, is_exception "
                "FROM schedules ORDER BY id"
            )).all()
            self.assertEqual(tuple(rows[0]), (11, "1–2", "A201", 1, 2, None, 0, 0))
            # Text that is not a period, or is out of range, is preserved and left without bounds.
            self.assertEqual(tuple(rows[1]), (12, "morning", "B101", None, None, None, 0, 0))
            self.assertEqual(tuple(rows[2]), (13, "7", "C301", 7, 7, None, 0, 0))
            self.assertEqual(tuple(rows[3]), (14, "0-2", "D401", None, None, None, 0, 0))
            names = {item["name"] for item in inspect(connection).get_indexes("schedules")}
            self.assertTrue({"uq_schedule_rule_date", "uq_schedule_rule_source", "ix_schedule_student_date"} <= names)
            self.assertEqual(table_names(connection), APPLICATION_TABLES)

    def test_database_created_by_the_old_startup_code_can_adopt_alembic(self):
        """Before Alembic the app ran create_all on startup, so existing installs have every table and no history."""
        Base.metadata.create_all(self.engine)
        with self.engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO users (id, username, password, name, role, status, create_time, update_time) "
                "VALUES (1, 'alice', 'hash', 'Alice', 'student', 1, '2026-07-01 10:00:00', '2026-07-01 10:00:00')"
            ))
        self.upgrade()
        self.assertEqual(self.current_revision(), "0002")
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(text("SELECT username FROM users")).scalar_one(), "alice")
            context = MigrationContext.configure(connection, opts={"compare_type": True})
            self.assertEqual(compare_metadata(context, Base.metadata), [])


if __name__ == "__main__":
    unittest.main()
