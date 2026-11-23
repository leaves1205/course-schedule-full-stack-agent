"""Request rate limiting shared by the authentication and chat endpoints."""

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.common.response import Response
from app.config import settings
from app.utils.jwt import decode_access_token


def user_or_ip_key(request: Request) -> str:
    """Throttle signed-in callers per account and anonymous callers per IP.

    Per-account keys stop users behind one shared NAT address from throttling each other.
    The token is only read to build a bucket name; authorization is still enforced by the endpoint.
    """
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() == "bearer" and token.strip():
        try:
            user_id = decode_access_token(token.strip()).get("user_id")
        except Exception:
            user_id = None
        if user_id:
            return f"user:{user_id}"
    return get_remote_address(request)


limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.RATE_LIMIT_STORAGE_URI,
    enabled=settings.RATE_LIMIT_ENABLED,
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Answer with HTTP 429 in the standard response envelope."""
    return JSONResponse(
        status_code=429,
        content=Response.error(
            code=429, message="Too many requests. Please wait a moment and try again."
        ).model_dump(),
    )
