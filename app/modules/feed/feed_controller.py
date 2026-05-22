"""Feed routes."""

import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user
from app.modules.auth.model import User
from app.modules.feed.feed_service import FeedService
from app.modules.feed.feed_schema import (
    CreatePostRequest,
    UpdatePostRequest,
    CommentRequest,
    UpdateCommentRequest,
    FeedPostOut,
    FeedListResponse,
    CommentOut,
    MessageResponse,
)

router = APIRouter(prefix="/feed", tags=["feed"])


def get_feed_service(db: AsyncSession = Depends(get_db)) -> FeedService:
    return FeedService(db)


@router.get(
    "/",
    response_model=FeedListResponse,
    summary="Get public feed (paginated)",
)
async def list_feed(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint — no auth required. Pass token to get is_liked state."""
    service = FeedService(db)
    return await service.list_feed(page=page, page_size=page_size)


@router.post(
    "/",
    response_model=FeedPostOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a post",
)
async def create_post(
    payload: CreatePostRequest,
    current_user: User = Depends(get_current_user),
    service: FeedService = Depends(get_feed_service),
):
    return await service.create_post(payload, current_user)


@router.get(
    "/my",
    response_model=FeedListResponse,
    summary="Get current user's posts",
)
async def get_my_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    service: FeedService = Depends(get_feed_service),
):
    return await service.get_my_posts(page=page, page_size=page_size, current_user=current_user)


@router.get(
    "/{post_id}",
    response_model=FeedPostOut,
    summary="Get a single post",
)
async def get_post(
    post_id: uuid.UUID,
    service: FeedService = Depends(get_feed_service),
):
    return await service.get_post(post_id)


@router.patch(
    "/{post_id}",
    response_model=FeedPostOut,
    summary="Update own post",
)
async def update_post(
    post_id: uuid.UUID,
    payload: UpdatePostRequest,
    current_user: User = Depends(get_current_user),
    service: FeedService = Depends(get_feed_service),
):
    return await service.update_post(post_id, payload, current_user)


@router.post(
    "/{post_id}/like",
    response_model=MessageResponse,
    summary="Like / unlike a post",
)
async def toggle_like(
    post_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: FeedService = Depends(get_feed_service),
):
    return await service.toggle_like(post_id, current_user)


@router.get(
    "/{post_id}/comments",
    response_model=list[CommentOut],
    summary="Get comments for a post",
)
async def get_comments(
    post_id: uuid.UUID,
    service: FeedService = Depends(get_feed_service),
):
    return await service.get_comments(post_id)


@router.post(
    "/{post_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment",
)

async def add_comment(
    post_id: uuid.UUID,
    payload: CommentRequest,
    current_user: User = Depends(get_current_user),
    service: FeedService = Depends(get_feed_service),
):
    return await service.add_comment(post_id, payload, current_user)


@router.delete(
    "/{post_id}/comments/{comment_id}",
    response_model=MessageResponse,
    summary="Delete own comment",
)
async def delete_comment(
    post_id: uuid.UUID,
    comment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: FeedService = Depends(get_feed_service),
):
    return await service.delete_comment(post_id, comment_id, current_user)


@router.patch(
    "/{post_id}/comments/{comment_id}",
    response_model=CommentOut,
    summary="Update own comment",
)
async def update_comment(
    post_id: uuid.UUID,
    comment_id: uuid.UUID,
    payload: UpdateCommentRequest,
    current_user: User = Depends(get_current_user),
    service: FeedService = Depends(get_feed_service),
):
    return await service.update_comment(post_id, comment_id, payload, current_user)


@router.delete(
    "/{post_id}",
    response_model=MessageResponse,
    summary="Delete own post",
)
async def delete_post(
    post_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: FeedService = Depends(get_feed_service),
):
    return await service.delete_post(post_id, current_user)
