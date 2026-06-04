"""Feed routes."""

import uuid
from fastapi import APIRouter, Depends, Query, Form, File, UploadFile, HTTPException, status
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
from app.services.r2_storage_service import R2StorageService

router = APIRouter(prefix="/feed", tags=["feed"])

ALLOWED_MEDIA_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/gif",
    "video/mp4", "video/webm", "video/quicktime",
    "application/pdf",
}
MAX_MEDIA_SIZE = 20 * 1024 * 1024  # 20 MB


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


@router.post(
    "/with-media",
    response_model=FeedPostOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a post with file/image upload",
)
async def create_post_with_media(
    content: str = Form(..., min_length=1),
    title: str | None = Form(None),
    external_link: str | None = Form(None),
    visibility: str = Form("PUBLIC"),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    service: FeedService = Depends(get_feed_service),
):
    """
    Create a post with an attached file (image, video, or PDF).
    The file is uploaded to Cloudflare R2 and the URL is stored as media_url.
    """
    if file.content_type not in ALLOWED_MEDIA_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{file.content_type}'. Allowed: {', '.join(sorted(ALLOWED_MEDIA_TYPES))}",
        )

    # Check file size
    file_content = await file.read()
    if len(file_content) > MAX_MEDIA_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size must be under 20 MB",
        )
    await file.seek(0)

    # Upload to R2
    r2 = R2StorageService()
    key = r2.upload_file(
        file=file.file,
        filename=file.filename or "media",
        folder="feed-media",
        content_type=file.content_type,
    )
    media_url = r2.generate_presigned_url(key, expires_in=30 * 24 * 3600)  # 30-day URL

    # Create the post with media_url
    payload = CreatePostRequest(
        content=content,
        title=title,
        media_url=media_url,
        external_link=external_link,
        visibility=visibility,
    )
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
