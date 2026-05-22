"""ORM model for the resumes table (matches existing DDL exactly)."""

import uuid
from sqlalchemy import Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from app.db.session import Base


class Resume(Base):
    __tablename__ = "resumes"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    resume_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    parsed_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_keywords: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
