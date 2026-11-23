import json
from langchain_mcp_adapters.client import MultiServerMCPClient

from app.common.exceptions import BusinessException
from app.config import settings


async def call_get_my_schedules(authorization: str, date: str | None = None) -> dict:
    """Client for calling the MCP service."""
    # 1. Create the client using the standard configuration.
    client = MultiServerMCPClient(
        {
            "campus": {
                "transport": "streamable_http",
                "url": f"http://{settings.MCP_HOST}:{settings.MCP_PORT}{settings.MCP_PATH}",  # http://127.0.0.1:8001/mcp
                "headers": {"Authorization": authorization},
            }
        }
    )
    # 2. Load the tool.
    tools = await client.get_tools(server_name="campus")
    tool = next((t for t in tools if t.name == "get_my_schedules"), None)
    if tool is None:
        raise BusinessException(
            message="Tool [get_my_schedules] was not found. Check that the MCP service is running.",
            code=503,
        )
    # 3. Invoke the tool.
    payload = {}
    if date:
        payload["date"] = date
    result = await tool.ainvoke(payload)

    return json.loads(result[0]["text"])
