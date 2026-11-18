import unittest

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.middleware.cors import CORSMiddleware

from app.api.study_plan import router
from app.common.exceptions import (
    BusinessException,
    business_exception_handler,
    global_excpetion_hadler,
    http_excpetion_hadler,
    validation_excpetion_hadler,
)
from app.database import Base, get_db
from app.models import StudyPlan, User
from app.utils.jwt import create_access_token


class StudyPlanAPITests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine)
        with self.sessions() as db:
            db.add_all([
                User(id=1, username="alice", password="unused", name="Alice", role="student", status=1),
                User(id=2, username="bob", password="unused", name="Bob", role="student", status=1),
                StudyPlan(id=1, user_id=1, content="Review Python"),
                StudyPlan(id=2, user_id=2, content="Bob study plan"),
            ])
            db.commit()

        app = FastAPI()
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        app.add_exception_handler(BusinessException, business_exception_handler)
        app.add_exception_handler(HTTPException, http_excpetion_hadler)
        app.add_exception_handler(RequestValidationError, validation_excpetion_hadler)
        app.add_exception_handler(Exception, global_excpetion_hadler)
        app.include_router(router, prefix="/api")

        def test_db():
            with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = test_db
        self.client = TestClient(app, raise_server_exceptions=False)
        self.client.__enter__()
        self.headers = {
            "Authorization": f"Bearer {create_access_token(1)}",
            "Origin": "http://localhost:5173",
        }

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.engine.dispose()

    def test_list_matches_frontend_url_and_returns_cors_headers(self):
        for origin in ("http://localhost:5173", "http://127.0.0.1:5173"):
            with self.subTest(origin=origin):
                response = self.client.get(
                    "/api/study-plans?page=1&page_size=10",
                    headers={**self.headers, "Origin": origin},
                    follow_redirects=False,
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers.get("access-control-allow-origin"), origin)
                self.assertNotIn("location", response.headers)
                result = response.json()
                self.assertEqual(result["code"], 200)
                self.assertEqual(result["data"]["total"], 1)
                self.assertEqual(result["data"]["list"][0]["content"], "Review Python")

    def test_create_and_delete_return_success_without_redirects(self):
        created = self.client.post(
            "/api/study-plans",
            json={"content": "Practice SQL"},
            headers=self.headers,
            follow_redirects=False,
        )
        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.json()["code"], 200)
        self.assertEqual(created.headers.get("access-control-allow-origin"), self.headers["Origin"])
        plan_id = created.json()["data"]["id"]
        self.assertEqual(created.json()["data"]["content"], "Practice SQL")

        deleted = self.client.delete(
            f"/api/study-plans/{plan_id}", headers=self.headers, follow_redirects=False
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.json()["code"], 200)
        self.assertEqual(deleted.headers.get("access-control-allow-origin"), self.headers["Origin"])
        with self.sessions() as db:
            self.assertIsNone(db.get(StudyPlan, plan_id))
            self.assertIsNotNone(db.get(StudyPlan, 2))

    def test_preflight_accepts_authorization_and_post(self):
        response = self.client.options(
            "/api/study-plans",
            headers={
                "Origin": self.headers["Origin"],
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), self.headers["Origin"])
        self.assertIn("POST", response.headers["access-control-allow-methods"])

    def test_missing_token_returns_auth_error_with_cors_header(self):
        response = self.client.get(
            "/api/study-plans", headers={"Origin": self.headers["Origin"]}
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], 401)
        self.assertEqual(response.headers.get("access-control-allow-origin"), self.headers["Origin"])


if __name__ == "__main__":
    unittest.main()
