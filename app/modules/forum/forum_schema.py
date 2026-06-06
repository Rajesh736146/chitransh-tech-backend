"""Pydantic schemas for the forum module."""

import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


# ─── Candidate Search ─────────────────────────────────────────────────────────

class CandidateOut(BaseModel):
    user_id: uuid.UUID
    full_name: str
    email: str
    profile_image: str | None = None
    headline: str | None = None
    current_position: str | None = None
    current_company: str | None = None
    experience_years: Decimal | None = None
    location: str | None = None
    skills: list[str] = []
    notice_period: str | None = None


class CandidateSearchResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[CandidateOut]


# ─── Hiring Invitations ───────────────────────────────────────────────────────

class SendInvitationRequest(BaseModel):
    receiver_id: uuid.UUID
    job_title: str | None = None
    message: str = Field(..., min_length=10)


class InvitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sender_id: uuid.UUID
    receiver_id: uuid.UUID
    sender_name: str | None = None
    receiver_name: str | None = None
    job_title: str | None = None
    message: str
    status: str
    created_at: datetime


class InvitationListResponse(BaseModel):
    total: int
    items: list[InvitationOut]


class UpdateInvitationRequest(BaseModel):
    status: str  # ACCEPTED or DECLINED


# ─── Chat / Messages ─────────────────────────────────────────────────────────

class SendMessageRequest(BaseModel):
    receiver_id: uuid.UUID
    content: str = Field(..., min_length=1)


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sender_id: uuid.UUID
    receiver_id: uuid.UUID
    content: str
    is_read: bool
    created_at: datetime
    sender_name: str | None = None


class ConversationOut(BaseModel):
    user_id: uuid.UUID
    full_name: str
    profile_image: str | None = None
    last_message: str | None = None
    last_message_at: datetime | None = None
    unread_count: int = 0


class MessageResponse(BaseModel):
    message: str
