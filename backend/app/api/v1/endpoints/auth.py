"""VAJANS — Auth endpoints: login, logout, current user."""

import uuid as uuid_lib
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    decode_token,
)

router = APIRouter(prefix="/auth")


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, body.username, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Record login time
    user.last_login = datetime.utcnow()
    await db.commit()

    token = create_access_token(str(user.id), user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user.username,
        "role": user.role,
    }


@router.post("/logout")
async def logout():
    return {"message": "logged out"}


@router.get("/me")
async def me(
    authorization: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
):
    """Return current user info from JWT token."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No token")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    from app.models.user import User

    user = await db.get(User, uuid_lib.UUID(payload["sub"]))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user.to_dict()
