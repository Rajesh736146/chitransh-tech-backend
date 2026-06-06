"""Pydantic schemas for the feed module."""

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class CreatePostRequest(BaseModel):
    content: str = Field(..., min_length=1)
    title: str | None = None
    media_url: str | None = None
    external_link: str | None = None
    category: str | None = Field(None, description="blue_collar or white_collar")
    visibility: str = "PUBLIC"


class UpdatePostRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    media_url: str | None = None
    external_link: str | None = None
    visibility: str | None = None


class CommentRequest(BaseModel):
    comment_text: str = Field(..., min_length=1)


class UpdateCommentRequest(BaseModel):
    comment_text: str = Field(..., min_length=1)


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    comment_text: str
    created_at: datetime
    author_name: str | None = None


class FeedPostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    author_id: uuid.UUID | None
    post_type: str
    title: str | None
    content: str | None
    media_url: str | None
    external_link: str | None
    category: str | None = None
    visibility: str
    created_at: datetime

    # enriched fields (from raw query)
    author_name: str | None = None
    author_email: str | None = None
    like_count: int = 0
    comment_count: int = 0
    is_liked: bool = False


class FeedListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[FeedPostOut]


class MessageResponse(BaseModel):
    message: str
