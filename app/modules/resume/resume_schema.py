"""Pydantic schemas for generic ATS resume builder."""

import uuid
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Any


class PersonalDetails(BaseModel):
    name: str
    email: str
    phone: str | None = None
    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None
    location: str | None = None


class Education(BaseModel):
    institution: str
    degree: str
    field_of_study: str | None = None
    grade: str | None = None          # CGPA, GPA, percentage, grade — any format
    start_year: int | None = None
    end_year: int | None = None


class Skill(BaseModel):
    category: str                     # e.g. "Programming", "Design Tools", "Soft Skills", "Languages"
    items: list[str]


class Project(BaseModel):
    title: str
    description: str
    role: str | None = None
    technologies_or_tools: list[str] = []
    url: str | None = None
    impact: str | None = None


class WorkExperience(BaseModel):
    company: str
    role: str
    responsibilities: list[str] = []
    tools_or_technologies: list[str] = []
    achievements: list[str] = []
    start_date: str | None = None     # e.g. "Aug 2021"
    end_date: str | None = None       # e.g. "Present" or "Jul 2024"


class Certification(BaseModel):
    name: str
    issuer: str | None = None
    year: int | None = None


class BuildResumeRequest(BaseModel):
    title: str
    target_role: str                  # e.g. "Java Backend Developer", "Marketing Manager", "UX Designer"
    personal_details: PersonalDetails
    education: list[Education] = []
    skills: list[Skill] = []          # flexible categories, not hardcoded
    projects: list[Project] = []
    work_experience: list[WorkExperience] = []
    certifications: list[Certification] = []
    extra_sections: dict[str, Any] = {}   # anything else: publications, awards, languages, etc.


class BuildResumeResponse(BaseModel):
    title: str
    target_role: str
    personal_details: dict[str, Any]
    education: list[dict[str, Any]]
    ai_enhanced: dict[str, Any]
