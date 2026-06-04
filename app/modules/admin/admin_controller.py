"""Admin routes — dashboard, user/job/feed/company management."""

import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user
from app.modules.auth.model import User
from app.modules.admin.admin_service import AdminService
from app.modules.admin.admin_schema import (
    DashboardStats,
    AdminUserListResponse,
    AdminJobListResponse,
    AdminFeedListResponse,
    AdminCompanyListResponse,
    UpdateUserStatusRequest,
    UpdateUserRoleRequest,
    UpdateJobStatusRequest,
    MessageResponse,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def get_admin_service(db: AsyncSession = Depends(get_db)) -> AdminService:
    return AdminService(db)


# ─── Dashboard ────────────────────────────────────────────────────────────────

@router.get(
    "/dashboard",
    response_model=DashboardStats,
    summary="Admin dashboard — platform-wide statistics",
)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
):
    return await service.get_dashboard_stats(current_user)


# ─── User Management ─────────────────────────────────────────────────────────

@router.get(
    "/users",
    response_model=AdminUserListResponse,
    summary="List all users (filterable)",
)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Search by name or email"),
    role_id: int | None = Query(None, description="Filter by role: 1=JobSeeker, 2=Employer, 3=Admin"),
    user_status: str | None = Query(None, alias="status", description="Filter by status: ACTIVE, SUSPENDED, BANNED"),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
):
    return await service.list_users(
        current_user, page=page, page_size=page_size,
        search=search, role_id=role_id, user_status=user_status,
    )


@router.patch(
    "/users/{user_id}/status",
    response_model=MessageResponse,
    summary="Suspend or ban a user",
)
async def update_user_status(
    user_id: uuid.UUID,
    payload: UpdateUserStatusRequest,
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
):
    return await service.update_user_status(user_id, payload, current_user)


@router.patch(
    "/users/{user_id}/role",
    response_model=MessageResponse,
    summary="Change a user's role",
)
async def update_user_role(
    user_id: uuid.UUID,
    payload: UpdateUserRoleRequest,
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
):
    return await service.update_user_role(user_id, payload, current_user)


@router.delete(
    "/users/{user_id}",
    response_model=MessageResponse,
    summary="Delete a user account",
)
async def delete_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
):
    return await service.delete_user(user_id, current_user)


# ─── Job Management ──────────────────────────────────────────────────────────

@router.get(
    "/jobs",
    response_model=AdminJobListResponse,
    summary="List all jobs with stats",
)
async def list_all_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Search by title or company"),
    job_status: str | None = Query(None, alias="status", description="Filter by status: OPEN, CLOSED, PAUSED"),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
):
    return await service.list_all_jobs(
        current_user, page=page, page_size=page_size,
        search=search, job_status=job_status,
    )


@router.patch(
    "/jobs/{job_id}/status",
    response_model=MessageResponse,
    summary="Change a job's status (close, pause, remove)",
)
async def update_job_status(
    job_id: uuid.UUID,
    payload: UpdateJobStatusRequest,
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
):
    return await service.update_job_status(job_id, payload, current_user)


@router.delete(
    "/jobs/{job_id}",
    response_model=MessageResponse,
    summary="Delete a job posting",
)
async def delete_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
):
    return await service.delete_job(job_id, current_user)


# ─── Feed Moderation ─────────────────────────────────────────────────────────

@router.get(
    "/feed",
    response_model=AdminFeedListResponse,
    summary="List all feed posts for moderation",
)
async def list_all_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Search in post content/title"),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
):
    return await service.list_all_posts(current_user, page=page, page_size=page_size, search=search)


@router.delete(
    "/feed/{post_id}",
    response_model=MessageResponse,
    summary="Remove a feed post (moderation)",
)
async def delete_post(
    post_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
):
    return await service.delete_post(post_id, current_user)


# ─── Company Management ──────────────────────────────────────────────────────

@router.get(
    "/companies",
    response_model=AdminCompanyListResponse,
    summary="List all companies with job counts",
)
async def list_companies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Search by company name"),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
):
    return await service.list_companies(current_user, page=page, page_size=page_size, search=search)


@router.delete(
    "/companies/{company_id}",
    response_model=MessageResponse,
    summary="Delete a company (cascade deletes associated jobs)",
)
async def delete_company(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
):
    return await service.delete_company(company_id, current_user)
