from datetime import datetime, timedelta, timezone
import jwt
from app.config import settings


def create_access_token(user_id: int) -> str:
    """Create a JWT token.

    Timestamps are timezone-aware UTC. A naive local datetime would be read as UTC by PyJWT,
    which shifts every token's lifetime by the server's UTC offset.
    """
    now = datetime.now(timezone.utc)
    # exp is a required key; do not rename it.
    payload = {
        "user_id": user_id,
        "iat": now,
        "exp": now + timedelta(hours=settings.JWT_EXPIRE_HOURS),
    }

    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def decode_access_token(token: str) -> dict:
    """Decode a JWT token."""
    return jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
