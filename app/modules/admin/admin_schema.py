"""Pydantic schemas for admin module."""

import uuid
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr


# ─── Dashboard stats ─────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_users: int = 0
    total_job_seekers: int = 0
    total_employers: int = 0
    total_admins: int = 0
    total_jobs: int = 0
    open_jobs: int = 0
    closed_jobs: int = 0
    total_applications: int = 0
    total_companies: int = 0
    total_feed_posts: int = 0
    new_users_last_7_days: int = 0
    new_jobs_last_7_days: int = 0
    new_applications_last_7_days: int = 0


# ─── User management ─────────────────────────────────────────────────────────

class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str
    phone: str | None = None
    role_id: int
    profile_image: str | None = None
    status: str
    email_verified: bool
    created_at: datetime


class AdminUserListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AdminUserOut]


class UpdateUserStatusRequest(BaseModel):
    status: str  # ACTIVE, SUSPENDED, BANNED


class UpdateUserRoleRequest(BaseModel):
    role_id: int  # 1=JobSeeker, 2=Employer, 3=Admin


# ─── Job management ──────────────────────────────────────────────────────────

class AdminJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    company_name: str | None = None
    location: str | None = None
    employment_type: str | None = None
    status: str
    posted_by: uuid.UUID
    poster_name: str | None = None
    application_count: int = 0
    created_at: datetime


class AdminJobListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AdminJobOut]


class UpdateJobStatusRequest(BaseModel):
    status: str  # OPEN, CLOSED, PAUSED, REMOVED


# ─── Feed moderation ─────────────────────────────────────────────────────────

class AdminFeedPostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    author_id: uuid.UUID | None
    author_name: str | None = None
    post_type: str
    title: str | None = None
    content: str | None = None
    visibility: str
    like_count: int = 0
    comment_count: int = 0
    created_at: datetime


class AdminFeedListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AdminFeedPostOut]


# ─── Reports / flagged content ───────────────────────────────────────────────

class AdminCompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_name: str
    industry: str | None = None
    company_size: str | None = None
    headquarters: str | None = None
    job_count: int = 0
    created_at: datetime


class AdminCompanyListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AdminCompanyOut]


class MessageResponse(BaseModel):
    message: str
