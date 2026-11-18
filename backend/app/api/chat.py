from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.common.response import Response
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.chat import ChatRequest
from app.services import agent_service
from app.services import agent_service
import asyncio
import json

from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/ask")
async def ask(
    body: ChatRequest,
    request: Request,
    _current_user: Annotated[User, Depends(get_current_user)],
):
    """Handle chat ask requests, return complete assistant answer based on the user's input"""
    authorization = request.headers.get("Authorization") or ""
    data = await agent_service.ask(body.question, body.history, authorization)
    return Response.success(data=data)


@router.post("/stream")
async def stream(
    body: ChatRequest,
    request: Request,
    _current_user: Annotated[User, Depends(get_current_user)],
):
    authorization = request.headers.get("Authorization") or ""
    return StreamingResponse(
        # Pass an async generator for StreamingResponse to consume; do not await it here.
        agent_service.stream_ask(body.question, body.history, authorization),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
