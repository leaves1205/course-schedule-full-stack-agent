from fastapi import APIRouter, Depends, Request
from pydantic import ValidationError
from app.common.response import Response
from app.config import settings
from app.rate_limit import limiter
from app.schemas.auth import LoginRequest
from app.schemas.auth import RegisterRequest
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import auth_service
from typing import Annotated
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from app.common.exceptions import BusinessException

router = APIRouter(prefix="/auth", tags=["Authentication"])

# /token and /login check the same credentials, so they share one bucket; otherwise the
# unused one would be a second, unthrottled way to guess passwords.
LOGIN_SCOPE = "login"


@router.post("/token")
@limiter.shared_limit(settings.LOGIN_RATE_LIMIT, scope=LOGIN_SCOPE)
def token(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    """Used by Swagger Authorize; follows the OAuth2 password flow.
    Accept form data and return top-level access_token / token_type without a Response.success envelope.
    Return errors as OAuth2 JSONResponse objects so Swagger can read them.
    The frontend should continue using /api/auth/login with JSON instead of this endpoint.
    """
    try:
        result = auth_service.login(
            db, LoginRequest(username=form.username, password=form.password)
        )
    except (BusinessException, ValidationError) as exc:
        message = exc.message if isinstance(exc, BusinessException) else "Invalid request."
        return JSONResponse(
            status_code=400,
            content={"error": "invalid_grant", "error_description": message},
        )
    return {"access_token": result.token, "token_type": "bearer"}


@router.post("/login")
@limiter.shared_limit(settings.LOGIN_RATE_LIMIT, scope=LOGIN_SCOPE)
def login(request: Request, data: LoginRequest, db: Session = Depends(get_db)):
    """Sign in"""
    result = auth_service.login(db, data)
    # Return response data.
    return Response.success(
        message="Signed in successfully",
        data=result,
    )


@router.post("/register")
@limiter.limit(settings.REGISTER_RATE_LIMIT)
def register(request: Request, data: RegisterRequest, db: Session = Depends(get_db)):
    """Register"""
    auth_service.register(db, data)
    # Return response data.
    return Response.success(message="Registered successfully")
