"""Business logic for admin module."""

import uuid
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text

from app.modules.auth.model import User
from app.modules.admin.admin_schema import (
    DashboardStats,
    AdminUserOut,
    AdminUserListResponse,
    AdminJobOut,
    AdminJobListResponse,
    AdminFeedPostOut,
    AdminFeedListResponse,
    AdminCompanyOut,
    AdminCompanyListResponse,
    UpdateUserStatusRequest,
    UpdateUserRoleRequest,
    UpdateJobStatusRequest,
    MessageResponse,
)

ADMIN_ROLE_ID = 3


def _require_admin(user) -> None:
    if user.role_id != ADMIN_ROLE_ID:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


class AdminService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── Dashboard ────────────────────────────────────────────────────────────

    async def get_dashboard_stats(self, current_user) -> DashboardStats:
        _require_admin(current_user)

        sql = text("""
            SELECT
                (SELECT COUNT(*) FROM public.users) AS total_users,
                (SELECT COUNT(*) FROM public.users WHERE role_id = 1) AS total_job_seekers,
                (SELECT COUNT(*) FROM public.users WHERE role_id = 2) AS total_employers,
                (SELECT COUNT(*) FROM public.users WHERE role_id = 3) AS total_admins,
                (SELECT COUNT(*) FROM public.jobs) AS total_jobs,
                (SELECT COUNT(*) FROM public.jobs WHERE status = 'OPEN') AS open_jobs,
                (SELECT COUNT(*) FROM public.jobs WHERE status = 'CLOSED') AS closed_jobs,
                (SELECT COUNT(*) FROM public.job_applications) AS total_applications,
                (SELECT COUNT(*) FROM public.companies) AS total_companies,
                (SELECT COUNT(*) FROM public.feed_posts) AS total_feed_posts,
                (SELECT COUNT(*) FROM public.users WHERE created_at >= NOW() - INTERVAL '7 days') AS new_users_last_7_days,
                (SELECT COUNT(*) FROM public.jobs WHERE created_at >= NOW() - INTERVAL '7 days') AS new_jobs_last_7_days,
                (SELECT COUNT(*) FROM public.job_applications WHERE applied_at >= NOW() - INTERVAL '7 days') AS new_applications_last_7_days
        """)

        row = (await self.db.execute(sql)).mappings().first()
        return DashboardStats(**row)

    # ─── User Management ──────────────────────────────────────────────────────

    async def list_users(
        self,
        current_user,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        role_id: int | None = None,
        user_status: str | None = None,
    ) -> AdminUserListResponse:
        _require_admin(current_user)

        filters = []
        params: dict = {}

        if search:
            filters.append("(u.full_name ILIKE :search OR u.email ILIKE :search)")
            params["search"] = f"%{search}%"
        if role_id:
            filters.append("u.role_id = :role_id")
            params["role_id"] = role_id
        if user_status:
            filters.append("u.status = :user_status")
            params["user_status"] = user_status

        where_clause = " AND ".join(filters) if filters else "1=1"

        count_sql = text(f"SELECT COUNT(*) FROM public.users u WHERE {where_clause}")
        total = (await self.db.execute(count_sql, params)).scalar_one()

        offset = (page - 1) * page_size
        params["limit"] = page_size
        params["offset"] = offset

        data_sql = text(f"""
            SELECT
                u.id, u.full_name, u.email, u.phone, u.role_id,
                u.profile_image, u.status, u.email_verified, u.created_at
            FROM public.users u
            WHERE {where_clause}
            ORDER BY u.created_at DESC
            LIMIT :limit OFFSET :offset
        """)

        rows = (await self.db.execute(data_sql, params)).mappings().all()
        items = [AdminUserOut(**r) for r in rows]
        return AdminUserListResponse(total=total, page=page, page_size=page_size, items=items)

    async def update_user_status(
        self, user_id: uuid.UUID, payload: UpdateUserStatusRequest, current_user
    ) -> MessageResponse:
        _require_admin(current_user)

        if payload.status not in ("ACTIVE", "SUSPENDED", "BANNED"):
            raise HTTPException(status_code=400, detail="Invalid status. Use ACTIVE, SUSPENDED, or BANNED")

        user = await self.db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.status = payload.status
        await self.db.flush()
        return MessageResponse(message=f"User status updated to {payload.status}")

    async def update_user_role(
        self, user_id: uuid.UUID, payload: UpdateUserRoleRequest, current_user
    ) -> MessageResponse:
        _require_admin(current_user)

        if payload.role_id not in (1, 2, 3):
            raise HTTPException(status_code=400, detail="Invalid role_id. Use 1 (JobSeeker), 2 (Employer), or 3 (Admin)")

        user = await self.db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.role_id = payload.role_id
        await self.db.flush()

        role_names = {1: "JobSeeker", 2: "Employer", 3: "Admin"}
        return MessageResponse(message=f"User role updated to {role_names[payload.role_id]}")

    async def delete_user(self, user_id: uuid.UUID, current_user) -> MessageResponse:
        _require_admin(current_user)

        user = await self.db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.id == current_user.id:
            raise HTTPException(status_code=400, detail="Cannot delete yourself")

        await self.db.delete(user)
        await self.db.flush()
        return MessageResponse(message="User deleted")

    # ─── Job Management ───────────────────────────────────────────────────────

    async def list_all_jobs(
        self,
        current_user,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        job_status: str | None = None,
    ) -> AdminJobListResponse:
        _require_admin(current_user)

        filters = []
        params: dict = {}

        if search:
            filters.append("(j.title ILIKE :search OR c.company_name ILIKE :search)")
            params["search"] = f"%{search}%"
        if job_status:
            filters.append("j.status = :job_status")
            params["job_status"] = job_status

        where_clause = " AND ".join(filters) if filters else "1=1"

        count_sql = text(f"""
            SELECT COUNT(*)
            FROM public.jobs j
            JOIN public.companies c ON c.id = j.company_id
            WHERE {where_clause}
        """)
        total = (await self.db.execute(count_sql, params)).scalar_one()

        offset = (page - 1) * page_size
        params["limit"] = page_size
        params["offset"] = offset

        data_sql = text(f"""
            SELECT
                j.id, j.title, c.company_name, j.location, j.employment_type,
                j.status, j.posted_by, u.full_name AS poster_name,
                COALESCE(a.cnt, 0)::int AS application_count,
                j.created_at
            FROM public.jobs j
            JOIN public.companies c ON c.id = j.company_id
            JOIN public.users u ON u.id = j.posted_by
            LEFT JOIN (
                SELECT job_id, COUNT(*) AS cnt FROM public.job_applications GROUP BY job_id
            ) a ON a.job_id = j.id
            WHERE {where_clause}
            ORDER BY j.created_at DESC
            LIMIT :limit OFFSET :offset
        """)

        rows = (await self.db.execute(data_sql, params)).mappings().all()
        items = [AdminJobOut(**r) for r in rows]
        return AdminJobListResponse(total=total, page=page, page_size=page_size, items=items)

    async def update_job_status(
        self, job_id: uuid.UUID, payload: UpdateJobStatusRequest, current_user
    ) -> MessageResponse:
        _require_admin(current_user)

        if payload.status not in ("OPEN", "CLOSED", "PAUSED", "REMOVED"):
            raise HTTPException(status_code=400, detail="Invalid status")

        sql = text("UPDATE public.jobs SET status = :status WHERE id = :job_id")
        result = await self.db.execute(sql, {"status": payload.status, "job_id": str(job_id)})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Job not found")
        return MessageResponse(message=f"Job status updated to {payload.status}")

    async def delete_job(self, job_id: uuid.UUID, current_user) -> MessageResponse:
        _require_admin(current_user)

        sql = text("DELETE FROM public.jobs WHERE id = :job_id")
        result = await self.db.execute(sql, {"job_id": str(job_id)})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Job not found")
        return MessageResponse(message="Job deleted by admin")

    # ─── Feed Moderation ──────────────────────────────────────────────────────

    async def list_all_posts(
        self,
        current_user,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> AdminFeedListResponse:
        _require_admin(current_user)

        filters = []
        params: dict = {}

        if search:
            filters.append("(fp.content ILIKE :search OR fp.title ILIKE :search)")
            params["search"] = f"%{search}%"

        where_clause = " AND ".join(filters) if filters else "1=1"

        count_sql = text(f"SELECT COUNT(*) FROM public.feed_posts fp WHERE {where_clause}")
        total = (await self.db.execute(count_sql, params)).scalar_one()

        offset = (page - 1) * page_size
        params["limit"] = page_size
        params["offset"] = offset

        data_sql = text(f"""
            SELECT
                fp.id, fp.author_id, u.full_name AS author_name,
                fp.post_type, fp.title, fp.content, fp.visibility,
                COUNT(DISTINCT fr.id)::int AS like_count,
                COUNT(DISTINCT fc.id)::int AS comment_count,
                fp.created_at
            FROM public.feed_posts fp
            LEFT JOIN public.users u ON u.id = fp.author_id
            LEFT JOIN public.feed_reactions fr ON fr.post_id = fp.id
            LEFT JOIN public.feed_comments fc ON fc.post_id = fp.id
            WHERE {where_clause}
            GROUP BY fp.id, u.full_name
            ORDER BY fp.created_at DESC
            LIMIT :limit OFFSET :offset
        """)

        rows = (await self.db.execute(data_sql, params)).mappings().all()
        items = [AdminFeedPostOut(**r) for r in rows]
        return AdminFeedListResponse(total=total, page=page, page_size=page_size, items=items)

    async def delete_post(self, post_id: uuid.UUID, current_user) -> MessageResponse:
        _require_admin(current_user)

        sql = text("DELETE FROM public.feed_posts WHERE id = :post_id")
        result = await self.db.execute(sql, {"post_id": str(post_id)})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Post not found")
        return MessageResponse(message="Post removed by admin")

    # ─── Company Management ───────────────────────────────────────────────────

    async def list_companies(
        self, current_user, page: int = 1, page_size: int = 20, search: str | None = None
    ) -> AdminCompanyListResponse:
        _require_admin(current_user)

        filters = []
        params: dict = {}

        if search:
            filters.append("c.company_name ILIKE :search")
            params["search"] = f"%{search}%"

        where_clause = " AND ".join(filters) if filters else "1=1"

        count_sql = text(f"SELECT COUNT(*) FROM public.companies c WHERE {where_clause}")
        total = (await self.db.execute(count_sql, params)).scalar_one()

        offset = (page - 1) * page_size
        params["limit"] = page_size
        params["offset"] = offset

        data_sql = text(f"""
            SELECT
                c.id, c.company_name, c.industry, c.company_size, c.headquarters,
                COALESCE(j.cnt, 0)::int AS job_count,
                c.created_at
            FROM public.companies c
            LEFT JOIN (
                SELECT company_id, COUNT(*) AS cnt FROM public.jobs GROUP BY company_id
            ) j ON j.company_id = c.id
            WHERE {where_clause}
            ORDER BY c.created_at DESC
            LIMIT :limit OFFSET :offset
        """)

        rows = (await self.db.execute(data_sql, params)).mappings().all()
        items = [AdminCompanyOut(**r) for r in rows]
        return AdminCompanyListResponse(total=total, page=page, page_size=page_size, items=items)

    async def delete_company(self, company_id: uuid.UUID, current_user) -> MessageResponse:
        _require_admin(current_user)

        sql = text("DELETE FROM public.companies WHERE id = :company_id")
        result = await self.db.execute(sql, {"company_id": str(company_id)})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Company not found")
        return MessageResponse(message="Company deleted by admin (associated jobs cascade-deleted)")
