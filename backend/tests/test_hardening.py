"""Tests for input validation, rate limiting, HTTP status codes, uploads and token handling."""

import io
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import jwt
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import ValidationError
from slowapi.errors import RateLimitExceeded
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.auth import router as auth_router
from app.api.files import router as files_router
from app.common.exceptions import (
    BusinessException,
    business_exception_handler,
    global_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.config import Settings, settings
from app.database import Base, get_db
from app.models import User
from app.rate_limit import limiter, rate_limit_exceeded_handler
from app.schemas.auth import RegisterRequest
from app.schemas.chat import MAX_HISTORY_MESSAGES, MAX_MESSAGE_CHARS, MAX_QUESTION_CHARS, ChatRequest
from app.schemas.course import CourseCreateRequest
from app.schemas.user import PasswordUpdateRequest, UserCreateRequest, UserUpdateRequest
from app.services.course_service import create_course
from app.services.user_service import ensure_admin
from app.utils.jwt import create_access_token
from app.utils.password import hash_password, verify_password

GOOD_PASSWORD = "Passw0rd123"


def build_app(*routers) -> FastAPI:
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(BusinessException, business_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_exception_handler(Exception, global_exception_handler)
    for router in routers:
        app.include_router(router, prefix="/api")
    return app


class ApiTestCase(unittest.TestCase):
    """A real app over an in-memory database with one active and one disabled student."""

    routers: tuple = ()

    def setUp(self):
        limiter.reset()
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine, autoflush=False)
        with self.sessions() as db:
            db.add_all([
                User(id=1, username="alice", password=hash_password(GOOD_PASSWORD), name="Alice", role="student", status=1),
                User(id=2, username="dave", password=hash_password(GOOD_PASSWORD), name="Dave", role="student", status=0),
            ])
            db.commit()
        app = build_app(*self.routers)

        def test_db():
            with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = test_db
        self.client = TestClient(app)
        self.client.__enter__()
        self.alice = {"Authorization": f"Bearer {create_access_token(1)}"}

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.engine.dispose()
        limiter.reset()

    def login(self, username="alice", password=GOOD_PASSWORD):
        return self.client.post("/api/auth/login", json={"username": username, "password": password})


class PasswordPolicyTests(unittest.TestCase):
    def test_weak_passwords_are_rejected_when_set(self):
        too_long_in_bytes = "a1" + "密" * 24  # 26 characters but 74 UTF-8 bytes
        for password in ("short1", "lettersonly", "12345678", "a1" * 40, too_long_in_bytes):
            with self.subTest(password=password[:12]):
                with self.assertRaises(ValidationError):
                    RegisterRequest(username="alice", password=password)
                with self.assertRaises(ValidationError):
                    PasswordUpdateRequest(old_password="x", new_password=password)

    def test_strong_password_is_accepted(self):
        self.assertEqual(RegisterRequest(username="alice", password=GOOD_PASSWORD).password, GOOD_PASSWORD)

    def test_admin_created_users_have_no_default_password(self):
        with self.assertRaises(ValidationError):
            UserCreateRequest(username="alice")

    def test_usernames_and_roles_are_constrained(self):
        for username in ("ab", "has space", "x" * 51, "semi;colon"):
            with self.subTest(username=username), self.assertRaises(ValidationError):
                RegisterRequest(username=username, password=GOOD_PASSWORD)
        for model in (UserUpdateRequest(), UserCreateRequest(username="alice", password=GOOD_PASSWORD)):
            with self.subTest(model=type(model).__name__), self.assertRaises(ValidationError):
                type(model)(**{**model.model_dump(exclude_none=True), "role": "superuser"})

    def test_login_never_raises_for_inputs_bcrypt_rejects(self):
        stored = hash_password(GOOD_PASSWORD)
        self.assertTrue(verify_password(GOOD_PASSWORD, stored))
        self.assertFalse(verify_password("x" * 100, stored))
        self.assertFalse(verify_password(GOOD_PASSWORD, "not-a-bcrypt-hash"))


class AuthApiTests(ApiTestCase):
    routers = (auth_router,)

    def test_validation_errors_use_422_and_explain_the_problem(self):
        response = self.client.post("/api/auth/register", json={"username": "newuser", "password": "12345678"})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["message"], "Password must contain at least one letter and one digit.")

    def test_business_errors_use_real_http_statuses(self):
        self.assertEqual(
            self.client.post("/api/auth/register", json={"username": "newuser", "password": GOOD_PASSWORD}).status_code, 200
        )
        duplicate = self.client.post("/api/auth/register", json={"username": "alice", "password": GOOD_PASSWORD})
        self.assertEqual((duplicate.status_code, duplicate.json()["code"]), (409, 409))

        wrong = self.login(password="WrongPass1")
        self.assertEqual((wrong.status_code, wrong.json()["code"]), (400, 400))
        self.assertEqual(self.login("dave").status_code, 403)
        self.assertEqual(self.login().status_code, 200)

    def test_overlong_password_is_a_failed_login_not_a_server_error(self):
        self.assertEqual(self.login(password="x" * 500).status_code, 400)

    def test_login_is_rate_limited_and_token_endpoint_shares_the_bucket(self):
        for _ in range(10):
            self.assertEqual(self.login(password="WrongPass1").status_code, 400)
        blocked = self.login(password="WrongPass1")
        self.assertEqual((blocked.status_code, blocked.json()["code"]), (429, 429))
        # The OAuth2 form endpoint checks the same credentials and must not be a second way to guess them.
        via_token = self.client.post("/api/auth/token", data={"username": "alice", "password": GOOD_PASSWORD})
        self.assertEqual(via_token.status_code, 429)

    def test_registration_is_rate_limited(self):
        statuses = [
            self.client.post("/api/auth/register", json={"username": f"user{i:02d}", "password": GOOD_PASSWORD}).status_code
            for i in range(11)
        ]
        self.assertEqual(statuses, [200] * 10 + [429])


class ChatRequestTests(unittest.TestCase):
    def test_size_limits(self):
        with self.assertRaises(ValidationError):
            ChatRequest(question="x" * (MAX_QUESTION_CHARS + 1))
        with self.assertRaises(ValidationError):
            ChatRequest(question="hi", history=[{"role": "user", "content": "x" * (MAX_MESSAGE_CHARS + 1)}])
        self.assertEqual(ChatRequest(question="x" * MAX_QUESTION_CHARS).question, "x" * MAX_QUESTION_CHARS)

    def test_long_history_is_trimmed_to_recent_turns_starting_with_a_user_message(self):
        history = [
            {"role": "user" if index % 2 == 0 else "assistant", "content": f"m{index}"} for index in range(30)
        ]
        trimmed = ChatRequest(question="now", history=history).history
        self.assertEqual(len(trimmed), MAX_HISTORY_MESSAGES)
        self.assertEqual(trimmed[0].role, "user")
        self.assertEqual(trimmed[-1].content, "m29")

    def test_trimming_never_leaves_a_leading_assistant_message(self):
        history = [{"role": "assistant", "content": "a"}, {"role": "user", "content": "u"}]
        self.assertEqual([m.role for m in ChatRequest(question="q", history=history).history], ["user"])


class BusinessExceptionStatusTests(unittest.TestCase):
    def test_status_follows_code_and_defaults_to_client_error(self):
        app = build_app()

        @app.get("/raise/{code}")
        def raise_with(code: int):
            raise BusinessException("boom", code=code)

        @app.get("/default")
        def raise_default():
            raise BusinessException("boom")

        @app.get("/crash")
        def crash():
            raise RuntimeError("secret internal detail")

        with TestClient(app, raise_server_exceptions=False) as client:
            for code, expected in ((404, 404), (409, 409), (503, 503), (200, 500), (0, 500)):
                with self.subTest(code=code):
                    response = client.get(f"/raise/{code}")
                    self.assertEqual((response.status_code, response.json()["code"]), (expected, code))
            self.assertEqual(client.get("/default").status_code, 400)
            # The traceback goes to the log for operators, never into the response body.
            with self.assertLogs("app.common.exceptions", level="ERROR"):
                crashed = client.get("/crash")
            self.assertEqual(crashed.status_code, 500)
            self.assertNotIn("secret", crashed.text)


class JwtTests(unittest.TestCase):
    def test_expiry_is_correct_regardless_of_server_timezone(self):
        original_tz = os.environ.get("TZ")
        try:
            for zone in ("Asia/Shanghai", "America/Los_Angeles", "UTC"):
                os.environ["TZ"] = zone
                time.tzset()
                with self.subTest(zone=zone):
                    token = create_access_token(7)
                    payload = jwt.decode(
                        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
                        options={"verify_exp": False},
                    )
                    expected = time.time() + settings.JWT_EXPIRE_HOURS * 3600
                    self.assertAlmostEqual(payload["exp"], expected, delta=10)
                    self.assertAlmostEqual(payload["iat"], time.time(), delta=10)
        finally:
            if original_tz is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = original_tz
            time.tzset()


class SettingsTests(unittest.TestCase):
    def build(self, secret: str, **extra):
        return Settings(DATABASE_URL="sqlite://", JWT_SECRET_KEY=secret, _env_file=None, **extra)

    def test_weak_or_placeholder_jwt_secrets_stop_startup(self):
        for secret in ("short", "x" * 31, "replace-with-a-long-random-secret"):
            with self.subTest(secret=secret), self.assertRaises(ValidationError):
                self.build(secret)
        self.assertEqual(self.build("x" * 32).JWT_SECRET_KEY, "x" * 32)

    def test_cors_origins_are_configurable(self):
        built = self.build("x" * 32, CORS_ORIGINS=" https://app.example.com , http://localhost:5173,, ")
        self.assertEqual(built.cors_origins, ["https://app.example.com", "http://localhost:5173"])


class UploadTests(ApiTestCase):
    routers = (files_router,)

    def setUp(self):
        super().setUp()
        self.folder = tempfile.TemporaryDirectory()
        for target, value in (
            ("app.api.files.UPLOAD_DIR", Path(self.folder.name)),
            ("app.api.files.MAX_UPLOAD_SIZE", 1024),
        ):
            patcher = patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def tearDown(self):
        self.folder.cleanup()
        super().tearDown()

    def upload(self, name: str, content: bytes):
        return self.client.post("/api/files/upload", headers=self.alice, files={"file": (name, io.BytesIO(content))})

    def stored(self):
        return list(Path(self.folder.name).iterdir())

    def test_small_image_is_stored_with_its_real_size(self):
        response = self.upload("me.PNG", b"x" * 100)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["size"], 100)
        self.assertEqual(len(self.stored()), 1)

    def test_oversized_upload_is_rejected_by_bytes_received_and_cleaned_up(self):
        response = self.upload("big.png", b"x" * 2048)
        self.assertEqual((response.status_code, response.json()["code"]), (413, 413))
        self.assertEqual(self.stored(), [])

    def test_only_images_are_accepted(self):
        for name in ("archive.zip", "report.pdf", "noextension", "page.html", "image.svg"):
            with self.subTest(name=name):
                self.assertEqual(self.upload(name, b"x" * 10).status_code, 400)
        self.assertEqual(self.stored(), [])

    def test_empty_file_is_rejected_and_cleaned_up(self):
        self.assertEqual(self.upload("empty.png", b"").status_code, 400)
        self.assertEqual(self.stored(), [])

    def test_upload_requires_authentication(self):
        response = self.client.post("/api/files/upload", files={"file": ("a.png", io.BytesIO(b"x"))})
        self.assertEqual(response.status_code, 401)


class AdminBootstrapTests(ApiTestCase):
    def test_admin_is_created_promoted_or_left_alone(self):
        with self.sessions() as db:
            self.assertEqual(ensure_admin(db, "root_admin", GOOD_PASSWORD), "created")
            created = db.query(User).filter(User.username == "root_admin").one()
            self.assertEqual((created.role, created.status, created.name), ("admin", 1, "root_admin"))
            self.assertTrue(verify_password(GOOD_PASSWORD, created.password))
            self.assertEqual(ensure_admin(db, "root_admin"), "unchanged")

            # Promoting keeps the existing password and re-enables a disabled account.
            before = db.query(User).filter(User.username == "dave").one().password
            self.assertEqual(ensure_admin(db, "dave"), "promoted")
            dave = db.query(User).filter(User.username == "dave").one()
            self.assertEqual((dave.role, dave.status, dave.password), ("admin", 1, before))

    def test_new_admin_needs_a_policy_compliant_password(self):
        with self.sessions() as db:
            with self.assertRaises(BusinessException):
                ensure_admin(db, "newcomer")
            with self.assertRaises(ValidationError):
                ensure_admin(db, "newcomer", "123")
            self.assertIsNone(db.query(User).filter(User.username == "newcomer").first())


class CourseServiceTests(ApiTestCase):
    def test_course_can_be_created_without_a_description(self):
        with self.sessions() as db:
            created = create_course(db, CourseCreateRequest(name="Math", code="MA"))
        self.assertEqual((created.name, created.description), ("Math", ""))

    def test_duplicate_course_code_is_a_conflict(self):
        with self.sessions() as db:
            create_course(db, CourseCreateRequest(name="Math", code="MA", description="Numbers"))
            with self.assertRaises(BusinessException) as caught:
                create_course(db, CourseCreateRequest(name="Maths", code="MA"))
        self.assertEqual(caught.exception.code, 409)


class ApplicationTests(unittest.TestCase):
    def test_security_header_is_added_without_breaking_responses(self):
        from app.main import app

        with TestClient(app) as client:
            response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")


if __name__ == "__main__":
    unittest.main()
