"""Job routes — post, list, update, delete jobs (employer-only write ops)."""

import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel
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
from app.services.r2_storage_service import R2StorageService, get_s3_client
from app.core.config import get_settings

router = APIRouter(prefix="/jobs", tags=["jobs"])

settings = get_settings()

ALLOWED_RESUME_EXTENSIONS = {"pdf", "doc", "docx"}
ALLOWED_CONTENT_TYPES = {
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


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
    category: str | None = Query(None, description="Filter by job category: blue_collar or white_collar"),
    service: JobService = Depends(get_job_service),
):
    """
    Returns top featured jobs ranked by popularity score.
    Score is based on view count, application count, and recency.
    No authentication required.
    """
    return await service.get_featured_jobs(limit=limit, category=category)


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
    category: str | None = Query(None, description="Filter by job category: blue_collar or white_collar"),
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
        category=category,
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


# ─── Presigned URL for direct R2 upload ───────────────────────────────────────

class PresignedUrlRequest(BaseModel):
    filename: str
    content_type: str


class PresignedUrlResponse(BaseModel):
    upload_url: str
    object_key: str


@router.post(
    "/{job_id}/apply/presigned-url",
    response_model=PresignedUrlResponse,
    summary="Get a presigned URL to upload resume directly to R2",
)
async def get_resume_upload_url(
    job_id: uuid.UUID,
    body: PresignedUrlRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Returns a presigned PUT URL so the frontend can upload the resume
    directly to Cloudflare R2 without passing through the backend.

    Flow:
    1. Call this endpoint with filename & content_type
    2. PUT the file to the returned upload_url
    3. Call POST /{job_id}/apply with the returned object_key
    """
    ext = body.filename.rsplit(".", 1)[-1].lower() if "." in body.filename else ""
    if ext not in ALLOWED_RESUME_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_RESUME_EXTENSIONS)}",
        )

    # Generate a unique object key
    unique_name = f"{uuid.uuid4().hex}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.{ext}"
    object_key = f"resumes/{unique_name}"

    # Generate presigned PUT URL
    s3 = get_s3_client()
    upload_url = s3.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.r2_bucket_name,
            "Key": object_key,
            "ContentType": body.content_type,
        },
        ExpiresIn=600,  # 10 minutes to upload
    )

    return PresignedUrlResponse(upload_url=upload_url, object_key=object_key)


# ─── Apply to job ─────────────────────────────────────────────────────────────

class ApplyRequest(BaseModel):
    resume_key: str


@router.post(
    "/{job_id}/apply",
    response_model=JobApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Apply to a job (after uploading resume to R2)",
)
async def apply_to_job(
    job_id: uuid.UUID,
    body: ApplyRequest,
    current_user: User = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
):
    """
    Apply to a job after uploading the resume directly to R2.

    Flow:
    1. GET presigned URL from /{job_id}/apply/presigned-url
    2. PUT file to R2 using that URL
    3. Call this endpoint with the object_key returned in step 1
    """
    # Verify the object exists in R2
    try:
        s3 = get_s3_client()
        s3.head_object(Bucket=settings.r2_bucket_name, Key=body.resume_key)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume not found in storage. Please upload first using the presigned URL.",
        )

    # Generate a long-lived read URL for the resume
    r2 = R2StorageService()
    resume_url = r2.generate_presigned_url(body.resume_key, expires_in=90 * 24 * 3600)

    return await service.apply_to_job(
        job_id=job_id,
        current_user=current_user,
        resume_url=resume_url,
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
