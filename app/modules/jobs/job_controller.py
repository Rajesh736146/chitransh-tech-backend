"""Job routes — post, list, update, delete jobs (employer-only write ops)."""

import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user
from app.modules.auth.model import User
from app.modules.jobs.job_service import JobService
from app.modules.jobs.job_schema import (
    JobCreateRequest,
    JobUpdateRequest,
    JobResponse,
    JobListResponse,
    CompanyCreateRequest,
    CompanyResponse,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


def get_job_service(db: AsyncSession = Depends(get_db)) -> JobService:
    return JobService(db)


# ─── Companies ────────────────────────────────────────────────────────────────

@router.post(
    "/companies",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a company (employer only)",
)
async def create_company(
    payload: CompanyCreateRequest,
    current_user: User = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
):
    return await service.create_company(payload, current_user)


@router.get(
    "/companies",
    response_model=list[CompanyResponse],
    summary="List all companies",
)
async def list_companies(
    service: JobService = Depends(get_job_service),
):
    return await service.list_companies()


# ─── Jobs ─────────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Post a new job (employer only)",
)
async def create_job(
    payload: JobCreateRequest,
    current_user: User = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
):
    return await service.create_job(payload, current_user)


@router.get(
    "/",
    response_model=JobListResponse,
    summary="List / search all open jobs (public)",
)
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Search in title and description"),
    location: str | None = Query(None),
    employment_type: str | None = Query(None, description="e.g. Full-time, Part-time, Contract, Internship, Freelance"),
    remote_type: str | None = Query(None, description="e.g. Remote, Hybrid, On-site"),
    company_name: str | None = Query(None, description="Filter by company name (partial match)"),
    service: JobService = Depends(get_job_service),
):
    return await service.list_jobs(
        page=page,
        page_size=page_size,
        search=search,
        location=location,
        employment_type=employment_type,
        remote_type=remote_type,
        company_name=company_name,
    )


@router.get(
    "/my",
    response_model=JobListResponse,
    summary="Get jobs posted by the current employer",
)
async def get_my_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
):
    return await service.get_my_jobs(current_user, page=page, page_size=page_size)


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get a single job by ID",
)
async def get_job(
    job_id: uuid.UUID,
    service: JobService = Depends(get_job_service),
):
    return await service.get_job(job_id)


@router.patch(
    "/{job_id}",
    response_model=JobResponse,
    summary="Update a job posting (employer only, own jobs)",
)
async def update_job(
    job_id: uuid.UUID,
    payload: JobUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
):
    return await service.update_job(job_id, payload, current_user)


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a job posting (employer only, own jobs)",
)
async def delete_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
):
    return await service.delete_job(job_id, current_user)
