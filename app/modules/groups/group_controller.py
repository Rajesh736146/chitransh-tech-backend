"""Group routes — create, join, post, comment, like."""

import uuid
from fastapi import APIRouter, Depends, Query, Form, File, UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user
from app.modules.auth.model import User
from app.modules.groups.group_service import GroupService
from app.modules.groups.group_schema import (
    GroupCreateRequest,
    GroupUpdateRequest,
    GroupOut,
    GroupListResponse,
    GroupMemberOut,
    GroupPostCreateRequest,
    GroupPostOut,
    GroupPostListResponse,
    GroupCommentRequest,
    GroupCommentOut,
    MessageResponse,
)
from app.services.r2_storage_service import R2StorageService

router = APIRouter(prefix="/groups", tags=["groups"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB


def get_group_service(db: AsyncSession = Depends(get_db)) -> GroupService:
    return GroupService(db)


# ─── Group CRUD ───────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=GroupOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a group",
)
async def create_group(
    name: str = Form(..., min_length=2, max_length=255),
    description: str | None = Form(None),
    category: str | None = Form(None, description="blue_collar or white_collar"),
    cover_image: UploadFile | None = File(None, description="Cover image (JPEG, PNG, WebP, GIF)"),
    current_user: User = Depends(get_current_user),
    service: GroupService = Depends(get_group_service),
):
    cover_image_url = None

    if cover_image and cover_image.filename:
        if cover_image.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid image type. Allowed: JPEG, PNG, WebP, GIF",
            )
        content = await cover_image.read()
        if len(content) > MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image must be under 5 MB",
            )
        await cover_image.seek(0)

        r2 = R2StorageService()
        key = r2.upload_file(
            file=cover_image.file,
            filename=cover_image.filename or "cover.png",
            folder="group-covers",
            content_type=cover_image.content_type,
        )
        cover_image_url = r2.generate_presigned_url(key, expires_in=90 * 24 * 3600)

    payload = GroupCreateRequest(
        name=name,
        description=description,
        cover_image=cover_image_url,
        category=category,
    )
    return await service.create_group(payload, current_user)


@router.get(
    "/",
    response_model=GroupListResponse,
    summary="List / search groups",
)
async def list_groups(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = Query(None, description="Filter by category: blue_collar or white_collar"),
    search: str | None = Query(None, description="Search in group name/description"),
    service: GroupService = Depends(get_group_service),
):
    return await service.list_groups(page=page, page_size=page_size, category=category, search=search)


@router.get(
    "/my",
    response_model=GroupListResponse,
    summary="Get groups I'm a member of",
)
async def get_my_groups(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: GroupService = Depends(get_group_service),
):
    """Returns groups the current user has joined."""
    # Custom implementation using list with membership filter
    from sqlalchemy import text
    offset = (page - 1) * page_size
    user_id = str(current_user.id)

    count_sql = text("""
        SELECT COUNT(*) FROM public.group_members WHERE user_id = :uid
    """)
    total = (await service.db.execute(count_sql, {"uid": user_id})).scalar() or 0

    data_sql = text("""
        SELECT
            g.id, g.name, g.description, g.cover_image, g.category,
            g.created_by, g.created_at,
            COALESCE(mc.cnt, 0)::int AS member_count,
            TRUE AS is_member
        FROM public.groups g
        JOIN public.group_members gm ON gm.group_id = g.id AND gm.user_id = :uid
        LEFT JOIN (
            SELECT group_id, COUNT(*) AS cnt FROM public.group_members GROUP BY group_id
        ) mc ON mc.group_id = g.id
        ORDER BY gm.joined_at DESC
        LIMIT :limit OFFSET :offset
    """)
    rows = (await service.db.execute(
        data_sql, {"uid": user_id, "limit": page_size, "offset": offset}
    )).mappings().all()

    from app.modules.groups.group_schema import GroupOut as _GO
    items = [_GO(**r) for r in rows]
    return GroupListResponse(total=total, page=page, page_size=page_size, items=items)


@router.get(
    "/{group_id}",
    response_model=GroupOut,
    summary="Get a group by ID",
)
async def get_group(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: GroupService = Depends(get_group_service),
):
    return await service.get_group(group_id, current_user)


@router.patch(
    "/{group_id}",
    response_model=GroupOut,
    summary="Update a group (creator only)",
)
async def update_group(
    group_id: uuid.UUID,
    payload: GroupUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: GroupService = Depends(get_group_service),
):
    return await service.update_group(group_id, payload, current_user)


@router.delete(
    "/{group_id}",
    response_model=MessageResponse,
    summary="Delete a group (creator only)",
)
async def delete_group(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: GroupService = Depends(get_group_service),
):
    return await service.delete_group(group_id, current_user)


# ─── Membership ───────────────────────────────────────────────────────────────

@router.post(
    "/{group_id}/join",
    response_model=MessageResponse,
    summary="Join a group",
)
async def join_group(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: GroupService = Depends(get_group_service),
):
    return await service.join_group(group_id, current_user)


@router.post(
    "/{group_id}/leave",
    response_model=MessageResponse,
    summary="Leave a group",
)
async def leave_group(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: GroupService = Depends(get_group_service),
):
    return await service.leave_group(group_id, current_user)


@router.get(
    "/{group_id}/members",
    response_model=list[GroupMemberOut],
    summary="Get group members",
)
async def get_members(
    group_id: uuid.UUID,
    service: GroupService = Depends(get_group_service),
):
    return await service.get_members(group_id)


# ─── Group Posts ──────────────────────────────────────────────────────────────

@router.post(
    "/{group_id}/posts",
    response_model=GroupPostOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a post in a group (members only)",
)
async def create_group_post(
    group_id: uuid.UUID,
    payload: GroupPostCreateRequest,
    current_user: User = Depends(get_current_user),
    service: GroupService = Depends(get_group_service),
):
    return await service.create_post(group_id, payload, current_user)


@router.get(
    "/{group_id}/posts",
    response_model=GroupPostListResponse,
    summary="Get posts in a group",
)
async def list_group_posts(
    group_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    service: GroupService = Depends(get_group_service),
):
    return await service.list_group_posts(group_id, page=page, page_size=page_size, current_user=current_user)


@router.post(
    "/posts/{post_id}/like",
    response_model=MessageResponse,
    summary="Like / unlike a group post",
)
async def toggle_like(
    post_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: GroupService = Depends(get_group_service),
):
    return await service.toggle_like(post_id, current_user)


@router.get(
    "/posts/{post_id}/comments",
    response_model=list[GroupCommentOut],
    summary="Get comments on a group post",
)
async def get_comments(
    post_id: uuid.UUID,
    service: GroupService = Depends(get_group_service),
):
    return await service.get_comments(post_id)


@router.post(
    "/posts/{post_id}/comments",
    response_model=GroupCommentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Comment on a group post",
)
async def add_comment(
    post_id: uuid.UUID,
    payload: GroupCommentRequest,
    current_user: User = Depends(get_current_user),
    service: GroupService = Depends(get_group_service),
):
    return await service.add_comment(post_id, payload, current_user)


@router.delete(
    "/posts/{post_id}",
    response_model=MessageResponse,
    summary="Delete a group post (author or group admin)",
)
async def delete_post(
    post_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: GroupService = Depends(get_group_service),
):
    return await service.delete_post(post_id, current_user)
