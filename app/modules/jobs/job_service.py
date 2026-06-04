"""Business logic for the jobs module."""

import uuid
from decimal import Decimal
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, text

from app.modules.jobs.model import Job, JobSkill, Company, JobApplication
from app.modules.auth.model import User
from app.modules.resume.model import Resume
from app.modules.feed.feed_service import FeedService as _FeedService
from app.modules.jobs.job_schema import (
    JobCreateRequest,
    JobUpdateRequest,
    JobResponse,
    JobListResponse,
    FeaturedJobResponse,
    FeaturedJobListResponse,
    JobApplicationResponse,
    JobApplicationListResponse,
    SkillOut,
    CompanyCreateRequest,
    CompanyResponse,
)

# role_id = 2 means Employer (from the roles table)
EMPLOYER_ROLE_ID = 2


def _require_employer(user: User) -> None:
    if user.role_id != EMPLOYER_ROLE_ID:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers can perform this action",
        )


class JobService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── Company ──────────────────────────────────────────────────────────────

    async def create_company(
        self, payload: CompanyCreateRequest, current_user: User
    ) -> CompanyResponse:
        _require_employer(current_user)

        company = Company(**payload.model_dump())
        self.db.add(company)
        await self.db.flush()
        await self.db.refresh(company)
        return CompanyResponse.model_validate(company)

    async def list_companies(self) -> list[CompanyResponse]:
        result = await self.db.execute(
            select(Company).order_by(Company.company_name)
        )
        return [CompanyResponse.model_validate(c) for c in result.scalars().all()]

    # ─── Jobs ─────────────────────────────────────────────────────────────────

    async def create_job(
        self, payload: JobCreateRequest, current_user: User
    ) -> JobResponse:
        _require_employer(current_user)

        # verify company exists
        company = await self.db.get(Company, payload.company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found",
            )

        job_data = payload.model_dump(exclude={"skills"})
        job = Job(**job_data, posted_by=current_user.id)
        self.db.add(job)
        await self.db.flush()  # get job.id

        # insert skills
        for skill_in in payload.skills:
            self.db.add(
                JobSkill(
                    job_id=job.id,
                    skill_name=skill_in.skill_name,
                    mandatory=skill_in.mandatory,
                )
            )

        await self.db.flush()
        await self.db.refresh(job)

        # ── auto-post to feed ─────────────────────────────────────────────────
        feed_svc = _FeedService(self.db)
        await feed_svc.create_job_feed_post(
            job_id=job.id,
            job_title=job.title,
            company_name=company.company_name,
            location=job.location,
            employment_type=job.employment_type,
            salary_min=float(job.salary_min) if job.salary_min else None,
            salary_max=float(job.salary_max) if job.salary_max else None,
            posted_by=current_user.id,
        )

        return JobResponse.model_validate(job)

    async def get_job(self, job_id: uuid.UUID) -> JobResponse:
        job = await self.db.get(Job, job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
            )
        return JobResponse.model_validate(job)

    async def list_jobs(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        location: str | None = None,
        employment_type: str | None = None,
        remote_type: str | None = None,
        company_name: str | None = None,
        status: str = "OPEN",
    ) -> JobListResponse:
        # ── build WHERE clauses and params dict ──────────────────────────────
        filters: list[str] = ["j.status = :status"]
        params: dict = {"status": status}

        if search:
            filters.append(
                "(j.title ILIKE :search OR j.description ILIKE :search)"
            )
            params["search"] = f"%{search}%"

        if location:
            filters.append("j.location ILIKE :location")
            params["location"] = f"%{location}%"

        if employment_type:
            filters.append("j.employment_type ILIKE :employment_type")
            params["employment_type"] = employment_type

        if remote_type:
            filters.append("j.remote_type ILIKE :remote_type")
            params["remote_type"] = remote_type

        if company_name:
            filters.append("c.company_name ILIKE :company_name")
            params["company_name"] = f"%{company_name}%"

        where_clause = " AND ".join(filters)

        # ── count query ───────────────────────────────────────────────────────
        count_sql = text(f"""
            SELECT COUNT(*) AS total
            FROM   public.jobs j
            WHERE  {where_clause}
        """)
        count_result = await self.db.execute(count_sql, params)
        total: int = count_result.scalar_one()

        # ── main query — jobs + aggregated skills ─────────────────────────────
        offset = (page - 1) * page_size
        params["limit"]  = page_size
        params["offset"] = offset

        data_sql = text(f"""
            SELECT
                j.id,
                j.company_id,
                j.title,
                j.description,
                j.employment_type,
                j.experience_required,
                j.salary_min,
                j.salary_max,
                j.location,
                j.remote_type,
                j.status,
                j.posted_by,
                j.created_at,
                j.updated_at,
                c.company_name,
                -- aggregate skills as JSON array
                COALESCE(
                    JSON_AGG(
                        JSON_BUILD_OBJECT(
                            'id',          js.id,
                            'skill_name',  js.skill_name,
                            'mandatory',   js.mandatory
                        )
                    ) FILTER (WHERE js.id IS NOT NULL),
                    '[]'
                ) AS skills
            FROM   public.jobs          j
            JOIN   public.companies     c  ON c.id = j.company_id
            LEFT JOIN public.job_skills js ON js.job_id = j.id
            WHERE  {where_clause}
            GROUP  BY j.id, c.company_name
            ORDER  BY j.created_at DESC
            LIMIT  :limit
            OFFSET :offset
        """)

        rows = (await self.db.execute(data_sql, params)).mappings().all()

        items: list[JobResponse] = []
        for row in rows:
            skills = [SkillOut(**s) for s in (row["skills"] or [])]
            items.append(
                JobResponse(
                    id=row["id"],
                    company_id=row["company_id"],
                    title=row["title"],
                    description=row["description"],
                    employment_type=row["employment_type"],
                    experience_required=row["experience_required"],
                    salary_min=row["salary_min"],
                    salary_max=row["salary_max"],
                    location=row["location"],
                    remote_type=row["remote_type"],
                    status=row["status"],
                    posted_by=row["posted_by"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    skills=skills,
                    company_name=row["company_name"],
                )
            )

        return JobListResponse(total=total, page=page, page_size=page_size, items=items)

    async def update_job(
        self, job_id: uuid.UUID, payload: JobUpdateRequest, current_user: User
    ) -> JobResponse:
        _require_employer(current_user)

        job = await self.db.get(Job, job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
            )
        if job.posted_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only edit your own job postings",
            )

        update_data = payload.model_dump(exclude_none=True, exclude={"skills"})
        for field, value in update_data.items():
            setattr(job, field, value)

        # replace skills if provided
        if payload.skills is not None:
            # delete existing
            existing = await self.db.execute(
                select(JobSkill).where(JobSkill.job_id == job_id)
            )
            for skill in existing.scalars().all():
                await self.db.delete(skill)
            await self.db.flush()

            for skill_in in payload.skills:
                self.db.add(
                    JobSkill(
                        job_id=job.id,
                        skill_name=skill_in.skill_name,
                        mandatory=skill_in.mandatory,
                    )
                )

        await self.db.flush()
        await self.db.refresh(job)
        return JobResponse.model_validate(job)

    async def delete_job(self, job_id: uuid.UUID, current_user: User) -> dict:
        _require_employer(current_user)

        job = await self.db.get(Job, job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
            )
        if job.posted_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own job postings",
            )

        await self.db.delete(job)
        await self.db.flush()
        return {"message": "Job deleted successfully"}

    async def get_my_jobs(
        self, current_user: User, page: int = 1, page_size: int = 20
    ) -> JobListResponse:
        _require_employer(current_user)

        query = select(Job).where(Job.posted_by == current_user.id)

        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        query = (
            query.order_by(Job.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        items = [JobResponse.model_validate(j) for j in result.scalars().all()]

        return JobListResponse(total=total, page=page, page_size=page_size, items=items)

    # ─── Featured Jobs ────────────────────────────────────────────────────────

    async def get_featured_jobs(self, limit: int = 10) -> FeaturedJobListResponse:
        """
        Return top featured jobs ranked by popularity score:
        score = (view_count * 1) + (application_count * 3) + recency_bonus

        Recency bonus gives newer posts a slight edge so the list stays fresh.
        Only OPEN jobs are included.
        """

        data_sql = text("""
            SELECT
                j.id,
                j.company_id,
                j.title,
                j.description,
                j.employment_type,
                j.experience_required,
                j.salary_min,
                j.salary_max,
                j.location,
                j.remote_type,
                j.status,
                j.posted_by,
                j.created_at,
                j.updated_at,
                c.company_name,
                c.logo_url AS company_logo,
                COALESCE(v.view_count, 0)::int          AS view_count,
                COALESCE(a.application_count, 0)::int   AS application_count,
                -- popularity score: views + 3x applications + recency bonus (max 30 days)
                (
                    COALESCE(v.view_count, 0) * 1
                    + COALESCE(a.application_count, 0) * 3
                    + GREATEST(0, 30 - EXTRACT(DAY FROM NOW() - j.created_at))
                ) AS popularity_score,
                COALESCE(
                    JSON_AGG(
                        JSON_BUILD_OBJECT(
                            'id',          js.id,
                            'skill_name',  js.skill_name,
                            'mandatory',   js.mandatory
                        )
                    ) FILTER (WHERE js.id IS NOT NULL),
                    '[]'
                ) AS skills
            FROM public.jobs j
            JOIN public.companies c ON c.id = j.company_id
            LEFT JOIN (
                SELECT job_id, COUNT(*) AS view_count
                FROM public.job_views
                GROUP BY job_id
            ) v ON v.job_id = j.id
            LEFT JOIN (
                SELECT job_id, COUNT(*) AS application_count
                FROM public.job_applications
                GROUP BY job_id
            ) a ON a.job_id = j.id
            LEFT JOIN public.job_skills js ON js.job_id = j.id
            WHERE j.status = 'OPEN'
            GROUP BY j.id, c.company_name, c.logo_url, v.view_count, a.application_count
            ORDER BY popularity_score DESC, j.created_at DESC
            LIMIT :limit
        """)

        rows = (await self.db.execute(data_sql, {"limit": limit})).mappings().all()

        items: list[FeaturedJobResponse] = []
        for row in rows:
            skills = [SkillOut(**s) for s in (row["skills"] or [])]
            items.append(
                FeaturedJobResponse(
                    id=row["id"],
                    company_id=row["company_id"],
                    title=row["title"],
                    description=row["description"],
                    employment_type=row["employment_type"],
                    experience_required=row["experience_required"],
                    salary_min=row["salary_min"],
                    salary_max=row["salary_max"],
                    location=row["location"],
                    remote_type=row["remote_type"],
                    status=row["status"],
                    posted_by=row["posted_by"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    skills=skills,
                    company_name=row["company_name"],
                    company_logo=row["company_logo"],
                    view_count=row["view_count"],
                    application_count=row["application_count"],
                )
            )

        return FeaturedJobListResponse(total=len(items), items=items)

    # ─── Job Applications ─────────────────────────────────────────────────────

    async def apply_to_job(
        self,
        job_id: uuid.UUID,
        current_user: User,
        resume_url: str,
    ) -> JobApplicationResponse:
        """
        Apply to a job with a resume upload.
        Creates a resume record and a job application record.
        """
        # verify job exists and is open
        job = await self.db.get(Job, job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
            )
        if job.status != "OPEN":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This job is no longer accepting applications",
            )

        # check if already applied
        existing = await self.db.execute(
            select(JobApplication).where(
                JobApplication.job_id == job_id,
                JobApplication.applicant_id == current_user.id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already applied to this job",
            )

        # create resume record
        resume = Resume(
            user_id=current_user.id,
            resume_url=resume_url,
        )
        self.db.add(resume)
        await self.db.flush()
        await self.db.refresh(resume)

        # create application
        application = JobApplication(
            job_id=job_id,
            applicant_id=current_user.id,
            resume_id=resume.id,
        )
        self.db.add(application)
        await self.db.flush()
        await self.db.refresh(application)

        # get company name for response
        company = await self.db.get(Company, job.company_id)

        return JobApplicationResponse(
            id=application.id,
            job_id=application.job_id,
            applicant_id=application.applicant_id,
            resume_id=application.resume_id,
            resume_url=resume_url,
            application_status=application.application_status,
            ai_match_score=application.ai_match_score,
            applied_at=application.applied_at,
            job_title=job.title,
            company_name=company.company_name if company else None,
        )

    async def get_my_applications(
        self, current_user: User, page: int = 1, page_size: int = 20
    ) -> JobApplicationListResponse:
        """Get all job applications by the current user."""

        count_sql = text("""
            SELECT COUNT(*) FROM public.job_applications WHERE applicant_id = :uid
        """)
        total = (await self.db.execute(count_sql, {"uid": str(current_user.id)})).scalar_one()

        offset = (page - 1) * page_size
        data_sql = text("""
            SELECT
                ja.id,
                ja.job_id,
                ja.applicant_id,
                ja.resume_id,
                r.resume_url,
                ja.application_status,
                ja.ai_match_score,
                ja.applied_at,
                j.title AS job_title,
                c.company_name
            FROM public.job_applications ja
            JOIN public.jobs j ON j.id = ja.job_id
            JOIN public.companies c ON c.id = j.company_id
            LEFT JOIN public.resumes r ON r.id = ja.resume_id
            WHERE ja.applicant_id = :uid
            ORDER BY ja.applied_at DESC
            LIMIT :limit OFFSET :offset
        """)

        rows = (await self.db.execute(
            data_sql,
            {"uid": str(current_user.id), "limit": page_size, "offset": offset},
        )).mappings().all()

        items = [JobApplicationResponse(**r) for r in rows]
        return JobApplicationListResponse(total=total, page=page, page_size=page_size, items=items)

    async def get_job_applicants(
        self, job_id: uuid.UUID, current_user: User, page: int = 1, page_size: int = 20
    ) -> JobApplicationListResponse:
        """Get all applicants for a job (employer only, own jobs)."""
        _require_employer(current_user)

        job = await self.db.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        if job.posted_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view applicants for your own jobs",
            )

        count_sql = text("SELECT COUNT(*) FROM public.job_applications WHERE job_id = :jid")
        total = (await self.db.execute(count_sql, {"jid": str(job_id)})).scalar_one()

        offset = (page - 1) * page_size
        data_sql = text("""
            SELECT
                ja.id,
                ja.job_id,
                ja.applicant_id,
                ja.resume_id,
                r.resume_url,
                ja.application_status,
                ja.ai_match_score,
                ja.applied_at,
                j.title AS job_title,
                c.company_name
            FROM public.job_applications ja
            JOIN public.jobs j ON j.id = ja.job_id
            JOIN public.companies c ON c.id = j.company_id
            LEFT JOIN public.resumes r ON r.id = ja.resume_id
            WHERE ja.job_id = :jid
            ORDER BY ja.applied_at DESC
            LIMIT :limit OFFSET :offset
        """)

        rows = (await self.db.execute(
            data_sql,
            {"jid": str(job_id), "limit": page_size, "offset": offset},
        )).mappings().all()

        items = [JobApplicationResponse(**r) for r in rows]
        return JobApplicationListResponse(total=total, page=page, page_size=page_size, items=items)
