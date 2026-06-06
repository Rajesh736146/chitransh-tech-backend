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



# ─── Forum Posts (Hiring / Seeking) ───────────────────────────────────────────

from pydantic import BaseModel as _BM, Field as _F

class ForumPostCreate(_BM):
    post_type: str = _F(..., description="HIRING or SEEKING")
    title: str = _F(..., min_length=5)
    content: str = _F(..., min_length=10)
    location: str | None = None
    skills_required: str | None = None
    experience_required: str | None = None
    salary_range: str | None = None

class ForumPostOut(_BM):
    id: str
    author_id: str
    author_name: str | None = None
    post_type: str
    title: str
    content: str
    location: str | None = None
    skills_required: str | None = None
    experience_required: str | None = None
    salary_range: str | None = None
    status: str
    created_at: str
    comment_count: int = 0

class ForumCommentCreate(_BM):
    content: str = _F(..., min_length=1)

class ForumCommentOut(_BM):
    id: str
    user_id: str
    author_name: str | None = None
    content: str
    created_at: str


@router.post(
    "/posts",
    response_model=ForumPostOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a forum post (HIRING or SEEKING)",
)
async def create_forum_post(
    payload: ForumPostCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import text
    sql = text("""
        INSERT INTO public.forum_posts (author_id, post_type, title, content, location, skills_required, experience_required, salary_range)
        VALUES (:author_id, :post_type, :title, :content, :location, :skills_required, :experience_required, :salary_range)
        RETURNING id, author_id, post_type, title, content, location, skills_required, experience_required, salary_range, status, created_at
    """)
    row = (await db.execute(sql, {
        "author_id": str(current_user.id), "post_type": payload.post_type,
        "title": payload.title, "content": payload.content,
        "location": payload.location, "skills_required": payload.skills_required,
        "experience_required": payload.experience_required, "salary_range": payload.salary_range,
    })).mappings().first()
    await db.flush()
    return ForumPostOut(**{k: str(v) if k in ("id", "author_id", "created_at") else v for k, v in row.items()}, author_name=current_user.full_name, comment_count=0)


@router.get(
    "/posts",
    summary="List forum posts (filterable by type)",
)
async def list_forum_posts(
    post_type: str | None = Query(None, description="HIRING or SEEKING"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import text
    type_filter = "AND fp.post_type = :post_type" if post_type else ""
    params: dict = {"limit": page_size, "offset": (page - 1) * page_size}
    if post_type:
        params["post_type"] = post_type

    count_sql = text(f"SELECT COUNT(*) FROM public.forum_posts fp WHERE 1=1 {type_filter}")
    total = (await db.execute(count_sql, params)).scalar() or 0

    sql = text(f"""
        SELECT fp.*, u.full_name AS author_name,
            (SELECT COUNT(*) FROM public.forum_comments fc WHERE fc.post_id = fp.id) AS comment_count
        FROM public.forum_posts fp
        JOIN public.users u ON u.id = fp.author_id
        WHERE 1=1 {type_filter}
        ORDER BY fp.created_at DESC
        LIMIT :limit OFFSET :offset
    """)
    rows = (await db.execute(sql, params)).mappings().all()
    items = [ForumPostOut(**{k: str(v) if k in ("id", "author_id", "created_at") else v for k, v in r.items()}) for r in rows]
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get(
    "/posts/{post_id}/comments",
    summary="Get comments on a forum post",
)
async def get_forum_comments(
    post_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import text
    sql = text("""
        SELECT fc.id, fc.user_id, fc.content, fc.created_at, u.full_name AS author_name
        FROM public.forum_comments fc
        JOIN public.users u ON u.id = fc.user_id
        WHERE fc.post_id = :post_id
        ORDER BY fc.created_at ASC
    """)
    rows = (await db.execute(sql, {"post_id": str(post_id)})).mappings().all()
    return [ForumCommentOut(**{k: str(v) if k in ("id", "user_id", "created_at") else v for k, v in r.items()}) for r in rows]


@router.post(
    "/posts/{post_id}/comments",
    status_code=status.HTTP_201_CREATED,
    summary="Comment on a forum post",
)
async def add_forum_comment(
    post_id: uuid.UUID,
    payload: ForumCommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import text
    sql = text("""
        INSERT INTO public.forum_comments (post_id, user_id, content)
        VALUES (:post_id, :user_id, :content)
        RETURNING id, user_id, content, created_at
    """)
    row = (await db.execute(sql, {"post_id": str(post_id), "user_id": str(current_user.id), "content": payload.content})).mappings().first()
    await db.flush()
    return ForumCommentOut(**{k: str(v) if k in ("id", "user_id", "created_at") else v for k, v in row.items()}, author_name=current_user.full_name)
