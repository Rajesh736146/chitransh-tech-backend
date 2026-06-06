"""Pydantic schemas for the profile module."""

import uuid
from decimal import Decimal
from datetime import datetime, date
from pydantic import BaseModel, ConfigDict, Field


# ─── Profile ─────────────────────────────────────────────────────────────────

class ProfileUpdateRequest(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    profile_image: str | None = None
    headline: str | None = None
    bio: str | None = None
    current_company: str | None = None
    current_position: str | None = None
    experience_years: Decimal | None = None
    location: str | None = None
    notice_period: str | None = None
    portfolio_url: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    full_name: str
    email: str
    phone: str | None = None
    profile_image: str | None = None
    headline: str | None = None
    bio: str | None = None
    current_company: str | None = None
    current_position: str | None = None
    experience_years: Decimal | None = None
    location: str | None = None
    notice_period: str | None = None
    portfolio_url: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    follower_count: int = 0
    following_count: int = 0
    is_following: bool = False
    profile_view_count: int = 0


class ProfileSearchItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    full_name: str
    email: str
    profile_image: str | None = None
    headline: str | None = None
    bio: str | None = None
    current_company: str | None = None
    current_position: str | None = None
    experience_years: Decimal | None = None
    location: str | None = None
    skills: list[str] = []


class ProfileSearchResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ProfileSearchItem]


# ─── Skills ──────────────────────────────────────────────────────────────────

class SkillCreateRequest(BaseModel):
    skill_name: str = Field(..., min_length=1, max_length=255)
    experience_years: Decimal | None = None
    skill_level: str | None = Field(None, description="e.g. Beginner, Intermediate, Expert")


class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    skill_name: str
    experience_years: Decimal | None
    skill_level: str | None
    endorsement_count: int = 0
    is_endorsed_by_me: bool = False


# ─── Education ───────────────────────────────────────────────────────────────

class EducationCreateRequest(BaseModel):
    institution_name: str = Field(..., min_length=2, max_length=255)
    degree: str | None = None
    specialization: str | None = None
    start_year: int | None = None
    end_year: int | None = None


class EducationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    institution_name: str
    degree: str | None
    specialization: str | None
    start_year: int | None
    end_year: int | None


# ─── Experience ──────────────────────────────────────────────────────────────

class ExperienceCreateRequest(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=255)
    designation: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None


class ExperienceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_name: str
    designation: str | None
    start_date: date | None
    end_date: date | None
    description: str | None


# ─── Social interactions ─────────────────────────────────────────────────────

class FollowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    full_name: str
    headline: str | None = None
    profile_image: str | None = None


class FollowListResponse(BaseModel):
    total: int
    items: list[FollowOut]


class ProfileViewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    viewer_id: uuid.UUID
    full_name: str
    headline: str | None = None
    profile_image: str | None = None
    viewed_at: datetime


class ShareProfileRequest(BaseModel):
    platform: str | None = Field(None, description="e.g. linkedin, twitter, internal, copy_link")


class MessageResponse(BaseModel):
    message: str
