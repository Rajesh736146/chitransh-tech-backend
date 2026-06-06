"""Forum routes — candidate search, hiring invitations, direct messaging."""

import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user
from app.modules.auth.model import User
from app.modules.forum.forum_service import ForumService
from app.modules.forum.forum_schema import (
    CandidateSearchResponse,
    SendInvitationRequest,
    InvitationOut,
    InvitationListResponse,
    UpdateInvitationRequest,
    SendMessageRequest,
    MessageOut,
    ConversationOut,
    MessageResponse,
)

router = APIRouter(prefix="/forum", tags=["forum"])


def get_forum_service(db: AsyncSession = Depends(get_db)) -> ForumService:
    return ForumService(db)


# ─── Candidate Search (public) ────────────────────────────────────────────────

@router.get(
    "/candidates",
    response_model=CandidateSearchResponse,
    summary="Search candidates by city, role, experience, skills",
)
async def search_candidates(
    city: str | None = Query(None, description="Filter by city/location"),
    job_role: str | None = Query(None, description="Filter by job role / position"),
    experience_min: float | None = Query(None, description="Min years of experience"),
    experience_max: float | None = Query(None, description="Max years of experience"),
    skill: str | None = Query(None, description="Filter by skill"),
    keyword: str | None = Query(None, description="Search in name, headline, bio"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: ForumService = Depends(get_forum_service),
):
    """
    Public endpoint — search for available candidates.
    No auth required. Employers can use this to find talent.
    """
    return await service.search_candidates(
        city=city, job_role=job_role,
        experience_min=experience_min, experience_max=experience_max,
        skill=skill, keyword=keyword,
        page=page, page_size=page_size,
    )


# ─── Hiring Invitations ──────────────────────────────────────────────────────

@router.post(
    "/invitations",
    response_model=InvitationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Send a hiring invitation to a candidate",
)
async def send_invitation(
    payload: SendInvitationRequest,
    current_user: User = Depends(get_current_user),
    service: ForumService = Depends(get_forum_service),
):
    return await service.send_invitation(payload, current_user)


@router.get(
    "/invitations/received",
    response_model=InvitationListResponse,
    summary="Get invitations received by me",
)
async def get_received_invitations(
    current_user: User = Depends(get_current_user),
    service: ForumService = Depends(get_forum_service),
):
    return await service.get_my_invitations(current_user, direction="received")


@router.get(
    "/invitations/sent",
    response_model=InvitationListResponse,
    summary="Get invitations sent by me",
)
async def get_sent_invitations(
    current_user: User = Depends(get_current_user),
    service: ForumService = Depends(get_forum_service),
):
    return await service.get_my_invitations(current_user, direction="sent")


@router.patch(
    "/invitations/{invitation_id}",
    response_model=MessageResponse,
    summary="Accept or decline a hiring invitation",
)
async def update_invitation(
    invitation_id: uuid.UUID,
    payload: UpdateInvitationRequest,
    current_user: User = Depends(get_current_user),
    service: ForumService = Depends(get_forum_service),
):
    return await service.update_invitation(invitation_id, payload, current_user)


# ─── Direct Messages ─────────────────────────────────────────────────────────

@router.post(
    "/messages",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
    summary="Send a direct message",
)
async def send_message(
    payload: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    service: ForumService = Depends(get_forum_service),
):
    return await service.send_message(payload, current_user)


@router.get(
    "/messages/conversations",
    response_model=list[ConversationOut],
    summary="Get all my conversations",
)
async def get_conversations(
    current_user: User = Depends(get_current_user),
    service: ForumService = Depends(get_forum_service),
):
    return await service.get_conversations(current_user)


@router.get(
    "/messages/{user_id}",
    response_model=list[MessageOut],
    summary="Get messages with a specific user",
)
async def get_conversation(
    user_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: ForumService = Depends(get_forum_service),
):
    return await service.get_conversation(user_id, current_user, page=page, page_size=page_size)
