"""Resume controller."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.modules.resume.resume_service import ResumeService
from app.modules.resume.resume_schema import BuildResumeRequest

router = APIRouter(prefix="/resume", tags=["resume"])


def get_resume_service(db: AsyncSession = Depends(get_db)) -> ResumeService:
    return ResumeService(db)


@router.post("/build", response_model=dict, status_code=status.HTTP_200_OK)
async def build_resume(
    payload: BuildResumeRequest,
    service: ResumeService = Depends(get_resume_service),
):
    return await service.build_resume(None, payload)
