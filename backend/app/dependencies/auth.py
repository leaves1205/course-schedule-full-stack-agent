from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.database import get_db
from app.models.user import User
from app.utils.jwt import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """Validate the JWT and resolve the authenticated user."""
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Your session has expired. Please sign in again."
        )
    # Get the user ID.
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid login credentials."
        )
    # Query user information from the database by user ID.
    user = db.query(User).filter(User.id == user_id, User.status == 1).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired or your account is disabled.",
        )
    return user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Check whether the JWT user has the admin role."""
    if current_user.role != "admin":
        raise BusinessException(message="Access denied.", code=403)
    return current_user
