import bcrypt

# bcrypt only uses the first 72 bytes and bcrypt 5.x raises ValueError for longer input.
BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    """Hash a password."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password. Inputs bcrypt cannot handle never match instead of raising."""
    encoded = password.encode("utf-8")
    if len(encoded) > BCRYPT_MAX_BYTES:
        return False
    try:
        return bcrypt.checkpw(encoded, hashed_password.encode("utf-8"))
    except ValueError:
        # A malformed stored hash must not turn a login attempt into a 500.
        return False
