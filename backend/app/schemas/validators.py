"""Reusable field types for request schemas."""

import re
from typing import Annotated

from pydantic import AfterValidator, StringConstraints

from app.utils.password import BCRYPT_MAX_BYTES

PASSWORD_MIN_LENGTH = 8


def _check_new_password(value: str) -> str:
    if len(value) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters.")
    if len(value.encode("utf-8")) > BCRYPT_MAX_BYTES:
        raise ValueError(f"Password must be at most {BCRYPT_MAX_BYTES} bytes.")
    if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise ValueError("Password must contain at least one letter and one digit.")
    return value


# Applied when a password is created or changed. Login still accepts any stored password.
NewPassword = Annotated[str, AfterValidator(_check_new_password)]

Username = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_.-]{3,50}$")]
