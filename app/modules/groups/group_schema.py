"""Pydantic schemas for the groups module."""

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


# ─── Group ────────────────────────────────────────────────────────────────────

class GroupCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = None
    cover_image: str | None = None
    category: str | None = Field(None, description="blue_collar or white_collar")


class GroupUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    description: str | None = None
    cover_image: str | None = None
    category: str | None = None


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    cover_image: str | None = None
    category: str | None = None
    created_by: uuid.UUID
    member_count: int = 0
    is_member: bool = False
    created_at: datetime


class GroupListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[GroupOut]


# ─── Group Members ───────────────────────────────────────────────────────────

class GroupMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    full_name: str
    profile_image: str | None = None
    role: str
    joined_at: datetime


# ─── Group Posts ──────────────────────────────────────────────────────────────

class GroupPostCreateRequest(BaseModel):
    title: str | None = None
    content: str = Field(..., min_length=1)
    media_url: str | None = None


class GroupPostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    group_id: uuid.UUID
    author_id: uuid.UUID
    title: str | None = None
    content: str
    media_url: str | None = None
    created_at: datetime
    author_name: str | None = None
    group_name: str | None = None
    like_count: int = 0
    comment_count: int = 0
    is_liked: bool = False


class GroupPostListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[GroupPostOut]


# ─── Group Post Comments ─────────────────────────────────────────────────────

class GroupCommentRequest(BaseModel):
    comment_text: str = Field(..., min_length=1)


class GroupCommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    comment_text: str
    created_at: datetime
    author_name: str | None = None


class MessageResponse(BaseModel):
    message: str
