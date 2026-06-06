"""ORM model for the users table."""

import uuid
from sqlalchemy import String, Boolean, DateTime, BigInteger, func, text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from app.db.session import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("uuid_generate_v4()"),
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    password_hash: Mapped[str] = mapped_column(nullable=False)
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    profile_image: Mapped[str | None] = mapped_column(nullable=True)
    preferred_category: Mapped[str] = mapped_column(String(50), server_default="white_collar")
    status: Mapped[str] = mapped_column(String(50), server_default="ACTIVE")
    email_verified: Mapped[bool] = mapped_column(Boolean, server_default="false")
    verification_token: Mapped[str | None] = mapped_column(nullable=True)
    password_reset_otp: Mapped[str | None] = mapped_column("password_reset_token", nullable=True)
    password_reset_expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
