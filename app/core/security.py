import secrets
from datetime import datetime, timezone
from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def generate_session_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)