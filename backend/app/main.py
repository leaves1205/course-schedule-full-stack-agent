from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from starlette.datastructures import MutableHeaders
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.api import api
from app.common.exceptions import (
    BusinessException,
    business_exception_handler,
    global_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.config import UPLOAD_DIR, settings
from app.rate_limit import limiter, rate_limit_exceeded_handler

# The database schema is managed by Alembic (`alembic upgrade head`), not created on import.

app = FastAPI()
app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # Allowed frontend origins; do not use ["*"].
    allow_credentials=True,  # Allow the frontend to include the Authorization token.
    allow_methods=["*"],  # Allow all request methods: GET, POST, PUT, DELETE and OPTIONS.
    allow_headers=["*"],  # Allow all request headers, including Authorization.
)



class SecurityHeadersMiddleware:
    """Stop browsers from guessing a different content type for uploaded files.

    A plain ASGI middleware, not ``@app.middleware("http")``: the latter wraps responses in
    BaseHTTPMiddleware, which interferes with cancellation of streaming (SSE) responses.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message):
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message).setdefault("X-Content-Type-Options", "nosniff")
            await send(message)

        await self.app(scope, receive, send_with_headers)


app.add_middleware(SecurityHeadersMiddleware)


app.include_router(api)

# Register exception handlers.
app.add_exception_handler(BusinessException, business_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
# Register the fallback exception handler last.
app.add_exception_handler(Exception, global_exception_handler)

# Mount the static file directory.  http://127.0.0.1:8000/uploads/xxx.jpg
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/")
def root():
    return {"message": "The FastAPI application is running."}
