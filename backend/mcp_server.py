"""FastMCP Streamable HTTP server. Run in backend/: python mcp_server.py"""

from typing import Annotated
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers
from pydantic import Field
from app.config import settings
from app.database import SessionLocal
from app.dependencies.mcp_auth import user_id_form_authorization
from app.services.schedule_service import list_schedules_as_dict

mcp = FastMCP("campus-course-agent")

# Each read-only query authenticates its own JWT and needs no session backchannel.
MCP_HTTP_OPTIONS = {"stateless_http": True, "json_response": True}


def _current_user_id() -> int:
    """Read authorization from the current HTTP request headers and extract user_id."""

    headers = get_http_headers() or {}
    auth = headers.get("authorization") or headers.get("Authorization")
    return user_id_form_authorization(auth)


@mcp.tool()
def get_my_schedules(
    date: Annotated[
        str | None,
        Field(
            description="Optional class date in YYYY-MM-DD format; omit it or pass null to retrieve all schedules."
        ),
    ] = None,
) -> dict:
    """Query the current user schedule; parameters cannot select a different user.

    Query a specific date or all schedules; date-range parameters are not supported.
    For a week or another date range, omit date to fetch all schedules, then filter by the target range.

    On success, return items and count. Each record includes date, period, course_id,
    course_name and location: the class date, period, course ID, course name and location.
    On failure, return error and empty items; an error means the query failed, not that no classes exist.
    """
    try:
        user_id = _current_user_id()
        db = SessionLocal()
        try:
            items = list_schedules_as_dict(db, user_id, date)
            return {"items": items, "count": len(items)}
        finally:
            db.close()
    except Exception as exc:
        return {"error": f"Schedule query failed: {exc}", "items": []}


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host=settings.MCP_HOST,
        port=settings.MCP_PORT,
        path=settings.MCP_PATH,
        uvicorn_config={"ws": "websockets"},
        **MCP_HTTP_OPTIONS,
    )
