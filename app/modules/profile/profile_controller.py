"""Profile routes — view, edit profile, social interactions (follow, endorse, share)."""

import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user
from app.modules.auth.model import User
from app.modules.profile.profile_service import ProfileService
from app.modules.profile.profile_schema import (
    ProfileUpdateRequest,
    ProfileOut,
    ProfileSearchResponse,
    SkillCreateRequest,
    SkillOut,
    EducationCreateRequest,
    EducationOut,
    ExperienceCreateRequest,
    ExperienceOut,
    FollowListResponse,
    ProfileViewOut,
    ShareProfileRequest,
    MessageResponse,
)

router = APIRouter(prefix="/profile", tags=["profile"])


def get_profile_service(db: AsyncSession = Depends(get_db)) -> ProfileService:
    return ProfileService(db)


# ─── Search Profiles ──────────────────────────────────────────────────────────

@router.get(
    "/search",
    response_model=ProfileSearchResponse,
    summary="Search user profiles by location, skill, job profile, bio keywords",
)
async def search_profiles(
    location: str | None = Query(None, description="Filter by location (partial match)"),
    skill: str | None = Query(None, description="Filter by skill name (partial match)"),
    job_profile: str | None = Query(None, description="Filter by current position / headline (partial match)"),
    keyword: str | None = Query(None, description="Search in bio, headline, full_name"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: ProfileService = Depends(get_profile_service),
):
    """
    Search and list user profiles with optional filters.
    All filters are optional and combined with AND logic.
    """
    return await service.search_profiles(
        location=location,
        skill=skill,
        job_profile=job_profile,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )


# ─── My Profile ───────────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=ProfileOut,
    summary="Get my full profile",
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    return await service.get_profile(current_user.id, current_user)


@router.patch(
    "/me",
    response_model=ProfileOut,
    summary="Update my profile",
)
async def update_my_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    return await service.update_profile(payload, current_user)


# ─── View another user's profile ─────────────────────────────────────────────

@router.get(
    "/{user_id}",
    response_model=ProfileOut,
    summary="View a user's profile (records a profile view)",
)
async def get_user_profile(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    return await service.get_profile(user_id, current_user)


# ─── Follow / Unfollow ────────────────────────────────────────────────────────

@router.post(
    "/{user_id}/follow",
    response_model=MessageResponse,
    summary="Follow or unfollow a user",
)
async def toggle_follow(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    return await service.toggle_follow(user_id, current_user)


@router.get(
    "/{user_id}/followers",
    response_model=FollowListResponse,
    summary="Get a user's followers",
)
async def get_followers(
    user_id: uuid.UUID,
    service: ProfileService = Depends(get_profile_service),
):
    return await service.get_followers(user_id)


@router.get(
    "/{user_id}/following",
    response_model=FollowListResponse,
    summary="Get who a user is following",
)
async def get_following(
    user_id: uuid.UUID,
    service: ProfileService = Depends(get_profile_service),
):
    return await service.get_following(user_id)


# ─── Skills ──────────────────────────────────────────────────────────────────

@router.post(
    "/skills",
    response_model=SkillOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a skill to my profile",
)
async def add_skill(
    payload: SkillCreateRequest,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    return await service.add_skill(payload, current_user)


@router.get(
    "/{user_id}/skills",
    response_model=list[SkillOut],
    summary="Get a user's skills with endorsement counts",
)
async def get_user_skills(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    return await service.get_user_skills(user_id, current_user)


@router.delete(
    "/skills/{skill_id}",
    response_model=MessageResponse,
    summary="Remove a skill from my profile",
)
async def delete_skill(
    skill_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    return await service.delete_skill(skill_id, current_user)


@router.post(
    "/skills/{skill_id}/endorse",
    response_model=MessageResponse,
    summary="Endorse or un-endorse a user's skill",
)
async def toggle_endorse_skill(
    skill_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    return await service.toggle_endorse_skill(skill_id, current_user)


# ─── Education ───────────────────────────────────────────────────────────────

@router.post(
    "/education",
    response_model=EducationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add education to my profile",
)
async def add_education(
    payload: EducationCreateRequest,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    return await service.add_education(payload, current_user)


@router.get(
    "/{user_id}/education",
    response_model=list[EducationOut],
    summary="Get a user's education history",
)
async def get_user_education(
    user_id: uuid.UUID,
    service: ProfileService = Depends(get_profile_service),
):
    return await service.get_user_education(user_id)


@router.delete(
    "/education/{edu_id}",
    response_model=MessageResponse,
    summary="Remove education entry",
)
async def delete_education(
    edu_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    return await service.delete_education(edu_id, current_user)


# ─── Experience ──────────────────────────────────────────────────────────────

@router.post(
    "/experience",
    response_model=ExperienceOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add experience to my profile",
)
async def add_experience(
    payload: ExperienceCreateRequest,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    return await service.add_experience(payload, current_user)


@router.get(
    "/{user_id}/experience",
    response_model=list[ExperienceOut],
    summary="Get a user's work experience",
)
async def get_user_experience(
    user_id: uuid.UUID,
    service: ProfileService = Depends(get_profile_service),
):
    return await service.get_user_experience(user_id)


@router.delete(
    "/experience/{exp_id}",
    response_model=MessageResponse,
    summary="Remove experience entry",
)
async def delete_experience(
    exp_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    return await service.delete_experience(exp_id, current_user)


# ─── Share Profile ───────────────────────────────────────────────────────────

@router.post(
    "/{user_id}/share",
    response_model=MessageResponse,
    summary="Share a user's profile",
)
async def share_profile(
    user_id: uuid.UUID,
    payload: ShareProfileRequest,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    return await service.share_profile(user_id, payload, current_user)


# ─── Who viewed my profile ───────────────────────────────────────────────────

@router.get(
    "/me/views",
    response_model=list[ProfileViewOut],
    summary="See who viewed my profile",
)
async def get_my_profile_views(
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    return await service.get_profile_views(current_user)
