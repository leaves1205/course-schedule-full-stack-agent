from app.common.exceptions import BusinessException
from app.common.response import PageResponse
from app.models.user import User
from app.schemas.user import (
    PasswordUpdateRequest,
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.utils.password import hash_password, verify_password


def get_user_info(user: User) -> UserResponse:
    return UserResponse.model_validate(user)


def update_user_info(db: Session, user: User, data: UserUpdateRequest):
    user_dict = data.model_dump(
        exclude_none=True, exclude={"role", "status"}
    )  # Convert the Pydantic model to a dictionary.
    for field, value in user_dict.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


def update_password(db: Session, user: User, data: PasswordUpdateRequest):
    """Change password"""
    if not verify_password(data.old_password, user.password):
        raise BusinessException(message="The current password is incorrect.")
    if data.old_password == data.new_password:
        raise BusinessException(message="The new password must differ from the current password.")
    user.password = hash_password(data.new_password)
    db.commit()


def get_user_page_list(
    db: Session, page: int, page_size: int, keywords: str | None = None
):
    """List users with pagination and fuzzy search."""
    # select * from user where username like '%Zhang%' or name like '%Zhang%';
    query = db.query(User)
    if keywords:
        query = query.filter(
            or_(User.username.ilike(f"%{keywords}%"), User.name.ilike(f"%{keywords}%"))
        )
    total = query.count()
    items = (
        query.order_by(User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PageResponse(
        list=[UserResponse.model_validate(item) for item in items], total=total
    )


def create_user(db: Session, data: UserCreateRequest):
    """Add user"""
    exist = db.query(User).filter(User.username == data.username).first()
    if exist:
        raise BusinessException(message="This username is already registered.", code=409)

    user = User(
        username=data.username,
        password=hash_password(data.password),
        # The name column is NOT NULL; fall back to the username as registration does.
        name=data.name or data.username,
        role=data.role,
        email=data.email,
        phone=data.phone,
        avatar=data.avatar,
        status=data.status,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


def ensure_admin(db: Session, username: str, password: str | None = None) -> str:
    """Create an administrator or promote an existing account.

    Returns "created", "promoted" or "unchanged". A new account needs a password that satisfies the
    password policy; an existing account keeps its current password.
    """
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        if not password:
            raise BusinessException(message="A password is required to create a new administrator.")
        create_user(db, UserCreateRequest(username=username, password=password, role="admin"))
        return "created"
    if user.role == "admin" and user.status == 1:
        return "unchanged"
    user.role = "admin"
    user.status = 1
    db.commit()
    return "promoted"


def update_user(db: Session, user_id: int, data: UserUpdateRequest):
    """Update user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BusinessException(message="User not found.", code=404)
    payload = data.model_dump(exclude_none=True)
    for field, value in payload.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


def delete_user(db: Session, user_id: int, current_user: User):
    """Delete user"""
    if user_id == current_user.id:
        raise BusinessException(message="You cannot delete the account you are currently using.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BusinessException(message="User not found.", code=404)
    db.delete(user)
    db.commit()
