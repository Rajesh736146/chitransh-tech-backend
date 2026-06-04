"""Pydantic schemas for the jobs module."""

import uuid
from decimal import Decimal
from datetime import datetime
from typing import Literal, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator


# ─── Skill sub-schemas ────────────────────────────────────────────────────────

class SkillIn(BaseModel):
    skill_name: str
    mandatory: bool = True

    @classmethod
    def from_any(cls, v: Union[str, dict]) -> "SkillIn":
        """Accept either a plain string or a {skill_name, mandatory} dict."""
        if isinstance(v, str):
            return cls(skill_name=v.strip(), mandatory=True)
        return cls(**v)


class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    skill_name: str
    mandatory: bool


# ─── Job create / update ──────────────────────────────────────────────────────

class JobCreateRequest(BaseModel):
    company_id: uuid.UUID
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=10)
    employment_type: Literal[
        "Full-time", "Part-time", "Contract", "Internship", "Freelance"
    ] | None = None
    experience_required: str | None = Field(
        None, description="e.g. '2-4 years', 'Fresher', '5+ years'"
    )
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    location: str | None = None
    remote_type: Literal["Remote", "Hybrid", "On-site"] | None = None
    skills: list[SkillIn] = []

    @field_validator("skills", mode="before")
    @classmethod
    def coerce_skills(cls, v: list) -> list:
        """Accept list[str] or list[dict] or mixed."""
        return [SkillIn.from_any(item) for item in v]


class JobUpdateRequest(BaseModel):
    title: str | None = Field(None, min_length=3, max_length=255)
    description: str | None = Field(None, min_length=10)
    employment_type: Literal[
        "Full-time", "Part-time", "Contract", "Internship", "Freelance"
    ] | None = None
    experience_required: str | None = None
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    location: str | None = None
    remote_type: Literal["Remote", "Hybrid", "On-site"] | None = None
    status: Literal["OPEN", "CLOSED", "PAUSED"] | None = None
    skills: list[SkillIn] | None = None

    @field_validator("skills", mode="before")
    @classmethod
    def coerce_skills(cls, v: list | None) -> list | None:
        if v is None:
            return None
        return [SkillIn.from_any(item) for item in v]


# ─── Job response ─────────────────────────────────────────────────────────────

class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    title: str
    description: str
    employment_type: str | None
    experience_required: str | None
    salary_min: Decimal | None
    salary_max: Decimal | None
    location: str | None
    remote_type: str | None
    status: str
    posted_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    skills: list[SkillOut] = []
    # enriched by raw-query search
    company_name: str | None = None


class JobListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[JobResponse]


class FeaturedJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    title: str
    description: str
    employment_type: str | None
    experience_required: str | None
    salary_min: Decimal | None
    salary_max: Decimal | None
    location: str | None
    remote_type: str | None
    status: str
    posted_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    skills: list[SkillOut] = []
    company_name: str | None = None
    company_logo: str | None = None
    view_count: int = 0
    application_count: int = 0


class FeaturedJobListResponse(BaseModel):
    total: int
    items: list[FeaturedJobResponse]


# ─── Company schemas ──────────────────────────────────────────────────────────

class CompanyCreateRequest(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=255)
    company_description: str | None = None
    website: str | None = None
    logo_url: str | None = None
    company_size: str | None = None
    industry: str | None = None
    headquarters: str | None = None


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_name: str
    company_description: str | None
    website: str | None
    logo_url: str | None
    company_size: str | None
    industry: str | None
    headquarters: str | None
    created_at: datetime


# ─── Job Application schemas ─────────────────────────────────────────────────

class JobApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    applicant_id: uuid.UUID
    resume_id: uuid.UUID | None
    resume_url: str | None = None
    application_status: str
    ai_match_score: Decimal | None = None
    applied_at: datetime
    job_title: str | None = None
    company_name: str | None = None


class JobApplicationListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[JobApplicationResponse]
