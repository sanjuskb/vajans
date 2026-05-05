"""VAJANS — Authentication service: password hashing and JWT tokens."""

import warnings
from datetime import datetime, timedelta

import bcrypt
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings

ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 8

# Suppress passlib bcrypt version warning
warnings.filterwarnings("ignore", ".*bcrypt.*", UserWarning)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def create_access_token(user_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Raises JWTError if invalid or expired."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


async def authenticate_user(db: AsyncSession, username: str, password: str):
    """Return User if credentials are valid. Accepts username OR email."""
    from app.models.user import User
    from sqlalchemy import or_

    result = await db.execute(
        select(User).where(or_(User.username == username, User.email == username))
    )
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user
