from sqlalchemy.orm import Session
from app.common.exceptions import BusinessException
from app.models.user import User
from app.schemas.user import UserResponse
from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.auth import LoginResponse
from app.utils.password import verify_password, hash_password
from app.utils.jwt import create_access_token


def login(db: Session, data: LoginRequest):
    # Query the database by username.
    user = db.query(User).filter(User.username == data.username).first()

    # Check the username and password. One message for both cases avoids revealing which usernames exist.
    if not user or not verify_password(data.password, user.password):
        raise BusinessException(message="Incorrect username or password.")
    # Check the account status.
    if user.status != 1:
        raise BusinessException(message="This account is disabled.", code=403)
    # Create a token.
    token = create_access_token(user.id)
    return LoginResponse(token=token, user=UserResponse.model_validate(user))


def register(db: Session, data: RegisterRequest):
    # Query the database by username.
    user = db.query(User).filter(User.username == data.username).first()
    if user:
        raise BusinessException(message="This username is already registered.", code=409)
    user_model = User(
        username=data.username,
        password=hash_password(data.password),
        name=data.name or data.username,
        role="student",
        status=1,
    )
    db.add(user_model)
    db.commit()
    db.refresh(user_model)
