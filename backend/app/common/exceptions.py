import logging

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.common.response import Response

logger = logging.getLogger(__name__)


class BusinessException(Exception):
    """A business-rule failure that is reported to the client.

    ``code`` is both the HTTP status of the response and the ``code`` field of the response envelope.
    It defaults to 400 because most business errors are caused by the request; raise it with an
    explicit 5xx code when the failure is on the server side (for example a model provider outage).
    """

    def __init__(self, message: str, code: int = 400, data=None):
        self.message = message
        self.code = code
        self.data = data
        super().__init__(message)


async def business_exception_handler(request: Request, exc: BusinessException):
    """Handle custom business exceptions with a real HTTP status."""
    status_code = exc.code if 400 <= exc.code <= 599 else 500
    return JSONResponse(
        status_code=status_code,
        content=Response(code=exc.code, message=exc.message, data=exc.data).model_dump(),
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=Response.error(code=exc.status_code, message=exc.detail).model_dump(),
    )


def _validation_message(exc: RequestValidationError) -> str:
    """Turn the first validation error into a readable sentence for the UI."""
    errors = exc.errors()
    if not errors:
        return "Request parameter validation failed."
    first = errors[0]
    message = str(first.get("msg", "")).removeprefix("Value error, ")
    field = ".".join(str(part) for part in first.get("loc", ()) if part not in ("body", "query", "path"))
    # Value errors already carry a complete sentence written for people; other types need the field name.
    if field and first.get("type") != "value_error":
        return f"{field}: {message}"
    return message or "Request parameter validation failed."


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    return JSONResponse(
        status_code=422,
        content=Response.error(code=422, message=_validation_message(exc)).model_dump(),
    )


async def global_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions; log the traceback and hide details from the client."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=Response.error(code=500, message="Internal server error.").model_dump(),
    )
