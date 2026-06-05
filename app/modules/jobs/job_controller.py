"""Job routes — post, list, update, delete jobs (employer-only write ops)."""

import uuid
from fastapi import APIRouter, Depends, Query, File, UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user
from app.modules.auth.model import User
from app.modules.jobs.job_service import JobService
from app.modules.jobs.job_schema import (
    JobCreateRequest,
    JobUpdateRequest,
    JobResponse,
    JobListResponse,
    FeaturedJobListResponse,
    JobApplicationResponse,
    JobApplicationListResponse,
    CompanyCreateRequest,
    CompanyResponse,
)
from app.services.r2_storage_service import R2StorageService

router = APIRouter(prefix="/jobs", tags=["jobs"])

ALLOWED_RESUME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_RESUME_SIZE = 10 * 1024 * 1024  # 10 MB


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

@router.get(
    "/featured",
    response_model=FeaturedJobListResponse,
    summary="Get featured/trending jobs (public)",
)
async def get_featured_jobs(
    limit: int = Query(10, ge=1, le=50, description="Number of featured jobs to return"),
    service: JobService = Depends(get_job_service),
):
    """
    Returns top featured jobs ranked by popularity score.
    Score is based on view count, application count, and recency.
    No authentication required.
    """
    return await service.get_featured_jobs(limit=limit)


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
    "/my-applications",
    response_model=JobApplicationListResponse,
    summary="Get current user's job applications",
)
async def get_my_applications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
):
    return await service.get_my_applications(current_user, page=page, page_size=page_size)


@router.post(
    "/{job_id}/apply",
    response_model=JobApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Apply to a job with resume upload",
)
async def apply_to_job(
    job_id: uuid.UUID,
    resume: UploadFile = File(None, description="Resume file (PDF, DOC, DOCX) — optional if resume_url provided"),
    current_user: User = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
):
    """
    Apply to a job by uploading your resume.
    Accepts PDF, DOC, or DOCX files up to 10 MB.
    """
    resume_url = None

    if resume and resume.filename:
        if resume.content_type not in ALLOWED_RESUME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid resume format. Allowed: PDF, DOC, DOCX",
            )

        content = await resume.read()
        if len(content) > MAX_RESUME_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Resume file must be under 10 MB",
            )
        await resume.seek(0)

        # Upload resume to R2
        r2 = R2StorageService()
        key = r2.upload_file(
            file=resume.file,
            filename=resume.filename or "resume.pdf",
            folder="resumes",
            content_type=resume.content_type,
        )
        resume_url = r2.generate_presigned_url(key, expires_in=90 * 24 * 3600)

    return await service.apply_to_job(
        job_id=job_id,
        current_user=current_user,
        resume_url=resume_url or "pending",
    )


from pydantic import BaseModel as _BaseModel

class _ApplyWithUrlBody(_BaseModel):
    resume_url: str


@router.post(
    "/{job_id}/apply-with-url",
    response_model=JobApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Apply to a job with a pre-uploaded resume URL",
)
async def apply_to_job_with_url(
    job_id: uuid.UUID,
    body: _ApplyWithUrlBody,
    current_user: User = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
):
    """Apply to a job using a resume URL obtained from /upload/document."""
    return await service.apply_to_job(
        job_id=job_id,
        current_user=current_user,
        resume_url=body.resume_url,
    )


@router.get(
    "/{job_id}/applicants",
    response_model=JobApplicationListResponse,
    summary="Get applicants for a job (employer only)",
)
async def get_job_applicants(
    job_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
):
    return await service.get_job_applicants(job_id, current_user, page=page, page_size=page_size)


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
