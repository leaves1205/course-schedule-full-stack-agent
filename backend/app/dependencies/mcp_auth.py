from app.common.exceptions import BusinessException
from app.database import SessionLocal
from app.models.user import User
from app.utils.jwt import decode_access_token


def user_id_form_authorization(authorization: str | None) -> int:
    """Extract user ID from the Authorization header."""

    if not authorization:
        raise BusinessException(message="Authorization header is missing", code=401)

    scheme, separator, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not separator:
        raise BusinessException(message="Invalid Authorization header", code=401)
    token = token.strip()
    if not token:
        raise BusinessException(message="Token is missing", code=401)
    try:
        payload = decode_access_token(token)
    except Exception:
        raise BusinessException(message="Your session has expired. Please sign in again.", code=401)
    # Get the user ID.
    user_id = payload.get("user_id")
    if not user_id:
        raise BusinessException(message="Invalid login credentials.", code=401)
    # Query user information from the database by user ID.
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id, User.status == 1).first()
        if not user:
            raise BusinessException(message="Your session has expired or your account is disabled.", code=401)
        return user_id
    finally:
        db.close()
