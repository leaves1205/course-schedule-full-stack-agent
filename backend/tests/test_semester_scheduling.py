import unittest
from datetime import date

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.schedule import router as schedule_router
from app.api.schedule_rule import router as rule_router
from app.api.semester import router as semester_router
from app.common.exceptions import BusinessException, business_exception_handler, validation_excpetion_hadler
from app.database import Base, get_db
from app.database_migrations import initialize_database
from app.models import Course, Schedule, ScheduleRule, Semester, User
from app.services.schedule_service import list_schedules_as_dict
from app.utils.jwt import create_access_token


class SemesterSchedulingTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine, autoflush=False)
        with self.sessions() as db:
            db.add_all([
                User(id=1, username="admin", password="unused", name="Admin", role="admin", status=1),
                User(id=2, username="alice", password="unused", name="Alice", role="student", status=1),
                User(id=3, username="bob", password="unused", name="Bob", role="student", status=1),
                Course(id=1, name="Python", code="PY", description="Programming"),
                Course(id=2, name="Math", code="MA", description="Mathematics"),
                Semester(id=1, name="Semester 2", first_monday=date(2026, 8, 3), total_weeks=16),
            ])
            db.commit()
        app = FastAPI()
        app.add_exception_handler(BusinessException, business_exception_handler)
        app.add_exception_handler(RequestValidationError, validation_excpetion_hadler)
        for router in (schedule_router, rule_router, semester_router):
            app.include_router(router, prefix="/api")
        def test_db():
            with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = test_db
        self.client = TestClient(app)
        self.client.__enter__()
        self.admin = {"Authorization": f"Bearer {create_access_token(1)}"}
        self.alice = {"Authorization": f"Bearer {create_access_token(2)}"}
        self.bob = {"Authorization": f"Bearer {create_access_token(3)}"}

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.engine.dispose()

    def payload(self, **changes):
        return {"semester_id": 1, "user_id": 2, "course_id": 1, "start_week": 1, "end_week": 16,
                "meetings": [
                    {"weekday": 1, "start_period": 1, "end_period": 2, "location": "A201"},
                    {"weekday": 4, "start_period": 3, "end_period": 4, "location": "A201"},
                ], **changes}

    def generate(self, **changes):
        return self.client.post("/api/schedules/generate", headers=self.admin, json=self.payload(**changes)).json()

    def counts(self):
        with self.sessions() as db:
            return db.scalar(select(func.count()).select_from(Schedule)), db.scalar(select(func.count()).select_from(ScheduleRule))

    def first_class(self):
        return self.client.get("/api/schedules?date=2026-08-03", headers=self.admin).json()["data"]["list"][0]

    def one_off(self, **changes):
        return self.client.post("/api/schedules", headers=self.admin, json={
            "user_id": 2, "course_id": 2, "class_date": "2026-08-03", "period": "1-2", "location": "B101", **changes,
        }).json()

    def test_two_rows_generate_32_classes_and_repeat_without_duplicates(self):
        result = self.generate()
        self.assertEqual(result["code"], 200)
        self.assertEqual(result["data"]["created_count"], 32)
        self.assertEqual(self.counts(), (32, 2))
        with self.sessions() as db:
            rows = db.scalars(select(Schedule).order_by(Schedule.class_date)).all()
            self.assertEqual(rows[0].class_date, date(2026, 8, 3))
            self.assertEqual(rows[-1].class_date, date(2026, 11, 19))
            self.assertEqual({row.class_date.isoweekday() for row in rows}, {1, 4})
            self.assertTrue(all(row.source_date == row.class_date and row.rule_id for row in rows))
            self.assertEqual({(row.start_period, row.end_period) for row in rows}, {(1, 2), (3, 4)})
        second = self.generate()
        self.assertEqual(second["data"]["created_count"], 0)
        self.assertEqual(second["data"]["preserved_count"], 32)
        self.assertEqual(second["data"]["rule_ids"], result["data"]["rule_ids"])
        self.assertEqual(self.counts(), (32, 2))
        rules = self.client.get("/api/schedule-rules?semester_id=1&user_id=2", headers=self.admin).json()["data"]
        self.assertEqual(rules["total"], 2)
        self.assertEqual({item["session_count"] for item in rules["list"]}, {16})

    def test_conflicts_return_details_and_roll_back_whole_batch(self):
        self.assertEqual(self.one_off(period="2-3")["code"], 200)
        result = self.generate()
        self.assertEqual(result["code"], 409)
        self.assertEqual(result["data"]["conflict_count"], 1)
        self.assertEqual(result["data"]["conflicts"][0]["date"], "2026-08-03")
        self.assertEqual(result["data"]["conflicts"][0]["existing_period"], "2-3")
        self.assertEqual(self.counts(), (1, 0))

    def test_overlapping_batch_rows_are_rejected_before_inserting_rules(self):
        result = self.generate(meetings=[
            {"weekday": 1, "start_period": 1, "end_period": 2},
            {"weekday": 1, "start_period": 2, "end_period": 3},
        ])
        self.assertEqual(result["code"], 409)
        self.assertEqual(result["data"]["conflict_count"], 16)
        self.assertEqual(self.counts(), (0, 0))

    def test_adjacent_periods_and_other_students_do_not_conflict(self):
        self.one_off(period="3-4")
        self.one_off(user_id=3)
        self.assertEqual(self.generate()["code"], 200)
        self.assertEqual(self.counts(), (34, 2))

    def test_invalid_dates_week_ranges_and_periods_are_rejected(self):
        response = self.client.post("/api/semesters", headers=self.admin, json={"name": "Bad", "first_monday": "2026-08-04", "total_weeks": 16})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.generate(end_week=17)["code"], 400)
        for changes in ({"end_week": 0}, {"start_week": 5, "end_week": 3}, {"meetings": []}, {"meetings": [{"weekday": 8, "start_period": 1, "end_period": 2}]}, {"meetings": [{"weekday": 1, "start_period": 3, "end_period": 2}]}):
            self.assertEqual(self.generate(**changes)["code"], 422)
        for changes in ({"semester_id": 999}, {"user_id": 999}, {"course_id": 999}, {"user_id": 1}):
            self.assertNotEqual(self.generate(**changes)["code"], 200)
        self.assertEqual(self.counts(), (0, 0))

    def test_one_class_move_survives_regeneration_with_original_identity(self):
        self.generate()
        original = self.first_class()
        result = self.client.put(f'/api/schedules/{original["id"]}', headers=self.admin, json={"class_date": "2026-08-04", "period": "5-6", "location": "B202"}).json()
        self.assertEqual(result["code"], 200)
        self.assertTrue(result["data"]["is_exception"])
        self.assertEqual(result["data"]["source_date"], "2026-08-03")
        self.assertEqual(self.generate()["data"]["created_count"], 0)
        with self.sessions() as db:
            moved = db.get(Schedule, original["id"])
            self.assertEqual((moved.class_date, moved.period, moved.location), (date(2026, 8, 4), "5-6", "B202"))
            self.assertEqual(db.scalar(select(func.count()).select_from(Schedule).where(Schedule.class_date == date(2026, 8, 3))), 0)
        self.assertEqual(self.counts(), (32, 2))

    def test_cancellation_is_preserved_and_hidden_from_student_and_mcp_queries(self):
        self.generate()
        original = self.first_class()
        self.client.delete(f'/api/schedules/{original["id"]}', headers=self.admin)
        self.assertEqual(self.generate()["data"]["created_count"], 0)
        student = self.client.get("/api/schedules?include_cancelled=true&user_id=3", headers=self.alice).json()["data"]
        self.assertEqual(student["total"], 31)
        self.assertEqual(self.client.get("/api/schedules?include_cancelled=true&semester_id=1", headers=self.admin).json()["data"]["total"], 32)
        self.assertEqual(self.client.get("/api/schedules", headers=self.bob).json()["data"]["total"], 0)
        with self.sessions() as db:
            self.assertEqual(len(list_schedules_as_dict(db, 2)), 31)
            self.assertEqual(list_schedules_as_dict(db, 2, "2026-08-03"), [])
        self.assertEqual(self.client.post(f'/api/schedule-rules/{original["rule_id"]}/generate', headers=self.admin).json()["data"]["created_count"], 0)

    def test_restore_rechecks_conflicts_before_reactivating_a_cancelled_class(self):
        self.generate()
        original = self.first_class()
        self.client.delete(f'/api/schedules/{original["id"]}', headers=self.admin)
        one_off = self.one_off()
        self.assertEqual(one_off["code"], 200)
        self.assertEqual(self.client.post(f'/api/schedules/{original["id"]}/restore', headers=self.admin).json()["code"], 409)
        self.client.delete(f'/api/schedules/{one_off["data"]["id"]}', headers=self.admin)
        restored = self.client.post(f'/api/schedules/{original["id"]}/restore', headers=self.admin).json()
        self.assertEqual(restored["code"], 200)
        self.assertFalse(restored["data"]["is_cancelled"])
        self.assertEqual(self.counts(), (32, 2))

    def test_single_edits_check_conflicts_and_keep_generated_ownership(self):
        self.generate()
        original = self.first_class()
        self.one_off(class_date="2026-08-04", period="5-6")
        self.assertEqual(self.client.put(f'/api/schedules/{original["id"]}', headers=self.admin, json={"class_date": "2026-08-04", "period": "6-7"}).json()["code"], 409)
        for changes in ({"user_id": 3}, {"course_id": 2}):
            self.assertEqual(self.client.put(f'/api/schedules/{original["id"]}', headers=self.admin, json=changes).json()["code"], 400)
        with self.sessions() as db:
            self.assertFalse(db.get(Schedule, original["id"]).is_exception)

    def test_used_semester_calendar_is_locked_but_name_can_change(self):
        self.generate()
        changed = {"name": "Renamed", "first_monday": "2026-08-10", "total_weeks": 16}
        self.assertEqual(self.client.put("/api/semesters/1", headers=self.admin, json=changed).json()["code"], 409)
        changed["first_monday"] = "2026-08-03"
        self.assertEqual(self.client.put("/api/semesters/1", headers=self.admin, json=changed).json()["code"], 200)
        self.assertEqual(self.client.delete("/api/semesters/1", headers=self.admin).json()["code"], 409)
        item = self.client.get("/api/semesters", headers=self.admin).json()["data"][0]
        self.assertEqual((item["name"], item["rule_count"], item["end_date"]), ("Renamed", 2, "2026-11-22"))

    def test_create_duplicate_and_delete_empty_semester(self):
        payload = {"name": "New semester", "first_monday": "2027-03-01", "total_weeks": 16}
        created = self.client.post("/api/semesters", headers=self.admin, json=payload).json()
        self.assertEqual(created["code"], 200)
        self.assertEqual(self.client.post("/api/semesters", headers=self.admin, json=payload).json()["code"], 409)
        self.assertEqual(self.client.delete(f'/api/semesters/{created["data"]["id"]}', headers=self.admin).json()["code"], 200)

    def test_management_apis_require_admin_and_students_cannot_read_rules(self):
        self.generate()
        rule_id = self.first_class()["rule_id"]
        requests = [
            ("get", "/api/semesters", None), ("post", "/api/schedules/generate", self.payload()),
            ("get", "/api/schedule-rules", None), ("post", f"/api/schedule-rules/{rule_id}/generate", None),
            ("post", "/api/schedules/1/restore", None),
            ("post", "/api/semesters", {"name": "Forbidden", "first_monday": "2027-03-01", "total_weeks": 16}),
            ("put", "/api/semesters/1", {"name": "Forbidden", "first_monday": "2026-08-03", "total_weeks": 16}),
            ("delete", "/api/semesters/1", None),
        ]
        for method, endpoint, payload in requests:
            with self.subTest(endpoint=endpoint, method=method):
                self.assertEqual(self.client.request(method, endpoint, headers=self.alice, json=payload).json()["code"], 403)
        self.assertEqual(self.client.get("/api/semesters").status_code, 401)

    def test_uniqueness_protects_original_occurrences(self):
        self.generate()
        original = self.first_class()
        with self.sessions() as db:
            db.add(Schedule(user_id=2, course_id=1, rule_id=original["rule_id"], source_date=date(2026, 8, 3), class_date=date(2026, 8, 4), period="8-9", location="A201"))
            with self.assertRaises(IntegrityError):
                db.commit()
            db.rollback()
        self.assertEqual(self.counts(), (32, 2))

    def test_unparseable_legacy_periods_block_new_overlapping_dates(self):
        with self.sessions() as db:
            db.add(Schedule(user_id=2, course_id=2, class_date=date(2026, 8, 3), period="morning", location="B101"))
            db.commit()
        self.assertEqual(self.generate()["code"], 409)
        self.assertEqual(self.counts(), (1, 0))


class ScheduleMigrationTests(unittest.TestCase):
    def test_additive_migration_preserves_legacy_rows_and_is_repeatable(self):
        engine = create_engine("sqlite://")
        with engine.begin() as connection:
            connection.execute(text("""CREATE TABLE schedules (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, course_id INTEGER NOT NULL,
                class_date DATE NOT NULL, period VARCHAR(50) NOT NULL, location VARCHAR(100),
                create_time DATETIME NOT NULL, update_time DATETIME NOT NULL
            )"""))
            connection.execute(text("""INSERT INTO schedules VALUES
                (11,2,1,'2026-08-03','1–2','A201','2026-07-01 10:00:00','2026-07-01 10:00:00'),
                (12,2,1,'2026-08-04','morning','B101','2026-07-01 10:00:00','2026-07-01 10:00:00')"""))
        try:
            initialize_database(engine)
            initialize_database(engine)
            with engine.connect() as connection:
                rows = connection.execute(text("SELECT id, period, location, start_period, end_period, rule_id, is_cancelled FROM schedules ORDER BY id")).all()
                self.assertEqual(tuple(rows[0]), (11, '1–2', 'A201', 1, 2, None, 0))
                self.assertEqual(tuple(rows[1]), (12, 'morning', 'B101', None, None, None, 0))
                names = {item["name"] for item in inspect(connection).get_indexes("schedules")}
                self.assertTrue({"uq_schedule_rule_date", "uq_schedule_rule_source"}.issubset(names))
                self.assertTrue({"semesters", "schedule_rules"}.issubset(inspect(connection).get_table_names()))
        finally:
            engine.dispose()
