import asyncio
import json
import unittest
from datetime import date
from unittest.mock import patch

from fastmcp import Client
import httpx
from langchain_mcp_adapters.client import MultiServerMCPClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import mcp_server
from app.common.exceptions import BusinessException
from app.database import Base
from app.dependencies import mcp_auth
from app.models import Course, Schedule, StudyPlan, User
from app.services.schedule_service import list_schedules_as_dict
from app.utils.jwt import create_access_token


class MCPServerTests(unittest.TestCase):
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
                User(id=3, username="disabled", password="unused", name="Disabled", role="student", status=0),
                Course(id=1, name="Python", code="PY", description="Python course"),
            ])
            db.flush()
            db.add_all([
                Schedule(user_id=1, course_id=1, class_date=date(2026, 11, 16), period="1-2", location="A101"),
                Schedule(user_id=1, course_id=1, class_date=date(2026, 11, 17), period="3-4", location="A102"),
                Schedule(user_id=2, course_id=1, class_date=date(2026, 11, 16), period="5-6", location="B101"),
            ])
            db.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_model_exports_resolve_foreign_keys(self):
        self.assertEqual(StudyPlan.__tablename__, "study_plan")
        self.assertIs(
            Schedule.__table__.c.course_id.foreign_keys.copy().pop().column,
            Course.__table__.c.id,
        )

    def test_invalid_authorization_headers_are_rejected_before_database_access(self):
        with patch.object(mcp_auth, "SessionLocal") as sessions:
            for header in (None, "", "Basic abc", "Bearer", "Bearer ", "Bearer    "):
                with self.subTest(header=header):
                    with self.assertRaises(BusinessException) as caught:
                        mcp_auth.user_id_form_authorization(header)
                    self.assertEqual(caught.exception.code, 401)
            sessions.assert_not_called()

    def test_valid_bearer_token_resolves_active_user(self):
        with patch.object(mcp_auth, "SessionLocal", self.sessions):
            user_id = mcp_auth.user_id_form_authorization(
                f"bEaReR {create_access_token(1)}"
            )
        self.assertEqual(user_id, 1)

    def test_disabled_and_missing_users_are_rejected(self):
        with patch.object(mcp_auth, "SessionLocal", self.sessions):
            for user_id in (3, 999):
                with self.subTest(user_id=user_id):
                    with self.assertRaises(BusinessException) as caught:
                        mcp_auth.user_id_form_authorization(
                            f"Bearer {create_access_token(user_id)}"
                        )
                    self.assertEqual(caught.exception.code, 401)

    def test_schedules_are_serialized_and_isolated_by_user(self):
        with self.sessions() as db:
            items = list_schedules_as_dict(db, 1)
        self.assertEqual(len(items), 2)
        self.assertEqual({item["location"] for item in items}, {"A101", "A102"})
        self.assertEqual(items[0]["date"], "2026-11-17")
        self.assertEqual(items[0]["course_name"], "Python")

    def test_schedule_date_filter_and_empty_results(self):
        with self.sessions() as db:
            items = list_schedules_as_dict(db, 1, "2026-11-16")
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["location"], "A101")
            self.assertEqual(list_schedules_as_dict(db, 1, "2026-11-18"), [])

    def test_mcp_client_can_discover_and_call_schedule_tool(self):
        async def check_tool():
            async with Client(mcp_server.mcp) as client:
                tools = await client.list_tools()
                self.assertIn("get_my_schedules", {tool.name for tool in tools})
                result = await client.call_tool(
                    "get_my_schedules", {"date": "2026-11-16"}
                )
                self.assertFalse(result.is_error)
                self.assertEqual(result.data["count"], 1)
                self.assertEqual(result.data["items"][0]["location"], "A101")

        with patch.object(mcp_server, "_current_user_id", return_value=1), patch.object(
            mcp_server, "SessionLocal", self.sessions
        ):
            asyncio.run(check_tool())

    def test_http_queries_use_json_preserve_jwt_and_close_without_sse_errors(self):
        async def check_http_tools():
            app = mcp_server.mcp.http_app(path="/mcp", **mcp_server.MCP_HTTP_OPTIONS)
            requests = []
            responses = []

            async def record_request(request):
                requests.append(request.method)

            async def record_response(response):
                responses.append((
                    response.status_code,
                    response.headers.get("content-type", ""),
                    response.headers.get("mcp-session-id"),
                ))

            def http_client_factory(headers=None, timeout=None, auth=None):
                return httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    headers=headers,
                    timeout=timeout,
                    auth=auth,
                    event_hooks={"request": [record_request], "response": [record_response]},
                )

            async def query(authorization):
                client = MultiServerMCPClient({
                    "campus": {
                        "transport": "streamable_http",
                        "url": "http://127.0.0.1:8001/mcp",
                        "headers": {"Authorization": authorization} if authorization else {},
                        "httpx_client_factory": http_client_factory,
                    }
                })
                tools = await client.get_tools(server_name="campus")
                schedules = next(tool for tool in tools if tool.name == "get_my_schedules")
                result = await schedules.ainvoke({"date": "2026-11-16"})
                return json.loads(result[0]["text"])

            async with app.router.lifespan_context(app):
                alice, bob = await asyncio.gather(
                    query(f"Bearer {create_access_token(1)}"),
                    query(f"Bearer {create_access_token(2)}"),
                )
                self.assertEqual(alice["count"], 1)
                self.assertEqual(alice["items"][0]["location"], "A101")
                self.assertEqual(bob["count"], 1)
                self.assertEqual(bob["items"][0]["location"], "B101")

                for authorization in (None, f"Bearer {create_access_token(3)}"):
                    denied = await query(authorization)
                    self.assertIn("error", denied)
                    self.assertEqual(denied["items"], [])

            self.assertTrue(requests)
            self.assertEqual(set(requests), {"POST"})
            self.assertTrue(any(status == 200 for status, _, _ in responses))
            for status, content_type, session_id in responses:
                self.assertIsNone(session_id)
                self.assertNotIn("text/event-stream", content_type)
                if status == 200:
                    self.assertIn("application/json", content_type)

        with patch.object(mcp_server, "SessionLocal", self.sessions), patch.object(
            mcp_auth, "SessionLocal", self.sessions
        ), self.assertNoLogs("mcp.server.streamable_http", level="ERROR"):
            asyncio.run(check_http_tools())


if __name__ == "__main__":
    unittest.main()
