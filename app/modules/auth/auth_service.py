"""Business logic for auth module."""

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.modules.auth.model import User
from app.modules.auth.auth_schema import (
    SignUpRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
    MessageResponse,
)
from app.services.email_service import send_verification_email, send_password_reset_email

import hashlib

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _generate_otp() -> str:
    return f"{secrets.randbelow(900000) + 100000}"


def _hash_password(password: str) -> str:
    return pwd_context.hash(hashlib.sha256(password.encode()).hexdigest())


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(hashlib.sha256(plain.encode()).hexdigest(), hashed)
settings = get_settings()
ALGORITHM = "HS256"


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def sign_up(self, payload: SignUpRequest) -> UserResponse:
        result = await self.db.execute(select(User).where(User.email == payload.email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

        verification_token = secrets.token_urlsafe(32)
        user = User(
            full_name=payload.full_name,
            email=payload.email,
            password_hash=_hash_password(payload.password),
            role_id=payload.role_id,
            phone=payload.phone,
            verification_token=verification_token,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)

        send_verification_email(user.email, verification_token)
        return UserResponse.model_validate(user)

    async def login(self, payload: LoginRequest) -> TokenResponse:
        result = await self.db.execute(select(User).where(User.email == payload.email))
        user = result.scalar_one_or_none()
        if not user or not _verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        if user.status != "ACTIVE":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
        token = jwt.encode({"sub": str(user.id), "exp": expire}, settings.secret_key, algorithm=ALGORITHM)
        return TokenResponse(access_token=token)

    async def get_current_user(self, token: str) -> UserResponse:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
            user_id: str | None = payload.get("sub")
            if not user_id:
                raise credentials_exception
        except JWTError:
            raise credentials_exception
        try:
            parsed_user_id = uuid.UUID(user_id)
        except (TypeError, ValueError):
            raise credentials_exception

        result = await self.db.execute(select(User).where(User.id == parsed_user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise credentials_exception
        return UserResponse.model_validate(user)

    async def verify_email(self, token: str) -> MessageResponse:
        result = await self.db.execute(
            select(User).where(User.verification_token == token)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token",
            )

        user.email_verified = True
        user.verification_token = None
        await self.db.flush()
        return MessageResponse(message="Email verified successfully")

    async def forgot_password(self, email: str) -> MessageResponse:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            return MessageResponse(
                message="If the email is registered, a password reset code has been sent"
            )

        otp = _generate_otp()
        user.password_reset_otp = otp
        user.password_reset_expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)
        await self.db.flush()

        send_password_reset_email(user.email, otp)
        return MessageResponse(
            message="If the email is registered, a password reset code has been sent"
        )

    async def verify_password_reset_otp(self, email: str, otp: str) -> MessageResponse:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user or user.password_reset_otp != otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset code",
            )

        if (
            user.password_reset_expires_at
            and user.password_reset_expires_at
            < datetime.now(timezone.utc).replace(tzinfo=None)
        ):
            user.password_reset_otp = None
            user.password_reset_expires_at = None
            await self.db.flush()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset code",
            )

        return MessageResponse(message="Password reset code is valid")

    async def reset_password(self, email: str, otp: str, new_password: str) -> MessageResponse:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user or user.password_reset_otp != otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset code",
            )

        if (
            user.password_reset_expires_at
            and user.password_reset_expires_at
            < datetime.now(timezone.utc).replace(tzinfo=None)
        ):
            user.password_reset_otp = None
            user.password_reset_expires_at = None
            await self.db.flush()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset code",
            )

        user.password_hash = _hash_password(new_password)
        user.password_reset_otp = None
        user.password_reset_expires_at = None
        await self.db.flush()
        return MessageResponse(message="Password reset successfully")
