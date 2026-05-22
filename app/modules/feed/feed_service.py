"""Business logic for the feed module."""

import uuid
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.modules.feed.model import FeedPost, FeedReaction, FeedComment
from app.modules.auth.model import User
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


class FeedService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── helpers ───────────────────────────────────────────────────────────────

    async def _get_post_or_404(self, post_id: uuid.UUID) -> FeedPost:
        post = await self.db.get(FeedPost, post_id)
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
        return post

    # ── create a regular user post ────────────────────────────────────────────

    async def create_post(self, payload: CreatePostRequest, current_user: User) -> FeedPostOut:
        post = FeedPost(
            author_id=current_user.id,
            post_type="POST",
            title=payload.title,
            content=payload.content,
            media_url=payload.media_url,
            external_link=payload.external_link,
            visibility=payload.visibility,
        )
        self.db.add(post)
        await self.db.flush()
        await self.db.refresh(post)
        return FeedPostOut(
            **post.__dict__,
            author_name=current_user.full_name,
            author_email=current_user.email,
        )

    # ── auto-create a feed post when a job is posted ──────────────────────────

    async def create_job_feed_post(
        self,
        job_id: uuid.UUID,
        job_title: str,
        company_name: str,
        location: str | None,
        employment_type: str | None,
        salary_min: float | None,
        salary_max: float | None,
        posted_by: uuid.UUID,
    ) -> None:
        salary_str = ""
        if salary_min and salary_max:
            salary_str = f" · ₹{int(salary_min):,} – ₹{int(salary_max):,}"
        elif salary_min:
            salary_str = f" · ₹{int(salary_min):,}+"

        content_parts = [f"📢 New job opening at {company_name}!"]
        if location:
            content_parts.append(f"📍 {location}")
        if employment_type:
            content_parts.append(f"🕐 {employment_type}")
        if salary_str:
            content_parts.append(f"💰{salary_str}")
        content_parts.append(f"\n🔗 Apply now — job ID: {job_id}")

        post = FeedPost(
            author_id=posted_by,
            post_type="JOB_POST",
            title=job_title,
            content="\n".join(content_parts),
            external_link=f"/jobs/{job_id}",
            visibility="PUBLIC",
        )
        self.db.add(post)
        await self.db.flush()

    # ── list feed (raw SQL with enrichment) ───────────────────────────────────

    async def list_feed(
        self,
        page: int = 1,
        page_size: int = 20,
        current_user: User | None = None,
    ) -> FeedListResponse:
        offset = (page - 1) * page_size
        user_id_str = str(current_user.id) if current_user else None

        count_result = await self.db.execute(
            text("SELECT COUNT(*) FROM public.feed_posts WHERE visibility = 'PUBLIC'")
        )
        total: int = count_result.scalar_one()

        data_sql = text("""
            SELECT
                fp.id,
                fp.author_id,
                fp.post_type,
                fp.title,
                fp.content,
                fp.media_url,
                fp.external_link,
                fp.visibility,
                fp.created_at,
                u.full_name                                    AS author_name,
                u.email                                        AS author_email,
                COUNT(DISTINCT fr.id)                          AS like_count,
                COUNT(DISTINCT fc.id)                          AS comment_count,
                BOOL_OR(fr.user_id = :user_id)                 AS is_liked
            FROM   public.feed_posts    fp
            LEFT JOIN public.users          u  ON u.id  = fp.author_id
            LEFT JOIN public.feed_reactions fr ON fr.post_id = fp.id
            LEFT JOIN public.feed_comments  fc ON fc.post_id = fp.id
            WHERE  fp.visibility = 'PUBLIC'
            GROUP  BY fp.id, u.full_name, u.email
            ORDER  BY fp.created_at DESC
            LIMIT  :limit
            OFFSET :offset
        """)

        rows = (
            await self.db.execute(
                data_sql,
                {"user_id": user_id_str, "limit": page_size, "offset": offset},
            )
        ).mappings().all()

        items = [
            FeedPostOut(
                id=r["id"],
                author_id=r["author_id"],
                post_type=r["post_type"],
                title=r["title"],
                content=r["content"],
                media_url=r["media_url"],
                external_link=r["external_link"],
                visibility=r["visibility"],
                created_at=r["created_at"],
                author_name=r["author_name"],
                author_email=r["author_email"],
                like_count=r["like_count"] or 0,
                comment_count=r["comment_count"] or 0,
                is_liked=bool(r["is_liked"]),
            )
            for r in rows
        ]

        return FeedListResponse(total=total, page=page, page_size=page_size, items=items)

    # ── like / unlike ─────────────────────────────────────────────────────────

    async def toggle_like(self, post_id: uuid.UUID, current_user: User) -> MessageResponse:
        await self._get_post_or_404(post_id)

        existing = await self.db.execute(
            select(FeedReaction).where(
                FeedReaction.post_id == post_id,
                FeedReaction.user_id == current_user.id,
            )
        )
        reaction = existing.scalar_one_or_none()

        if reaction:
            await self.db.delete(reaction)
            await self.db.flush()
            return MessageResponse(message="Unliked")

        self.db.add(FeedReaction(post_id=post_id, user_id=current_user.id))
        await self.db.flush()
        return MessageResponse(message="Liked")

    # ── comments ──────────────────────────────────────────────────────────────

    async def add_comment(
        self, post_id: uuid.UUID, payload: CommentRequest, current_user: User
    ) -> CommentOut:
        await self._get_post_or_404(post_id)

        comment = FeedComment(
            post_id=post_id,
            user_id=current_user.id,
            comment_text=payload.comment_text,
        )
        self.db.add(comment)
        await self.db.flush()
        await self.db.refresh(comment)
        return CommentOut(
            id=comment.id,
            user_id=comment.user_id,
            comment_text=comment.comment_text,
            created_at=comment.created_at,
            author_name=current_user.full_name,
        )

    async def get_comments(self, post_id: uuid.UUID) -> list[CommentOut]:
        await self._get_post_or_404(post_id)

        sql = text("""
            SELECT fc.id, fc.user_id, fc.comment_text, fc.created_at, u.full_name AS author_name
            FROM   public.feed_comments fc
            JOIN   public.users         u  ON u.id = fc.user_id
            WHERE  fc.post_id = :post_id
            ORDER  BY fc.created_at ASC
        """)
        rows = (await self.db.execute(sql, {"post_id": str(post_id)})).mappings().all()
        return [CommentOut(**r) for r in rows]

    # ── delete own post ───────────────────────────────────────────────────────

    async def delete_post(self, post_id: uuid.UUID, current_user: User) -> MessageResponse:
        post = await self._get_post_or_404(post_id)
        if post.author_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your post")
        await self.db.delete(post)
        await self.db.flush()
        return MessageResponse(message="Post deleted")

    # ── update own post ────────────────────────────────────────────────────

    async def update_post(
        self, post_id: uuid.UUID, payload: UpdatePostRequest, current_user: User
    ) -> FeedPostOut:
        post = await self._get_post_or_404(post_id)
        if post.author_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your post")

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(post, field, value)

        await self.db.flush()
        await self.db.refresh(post)

        return FeedPostOut(
            **post.__dict__,
            author_name=current_user.full_name,
            author_email=current_user.email,
        )

    # ── get single post ────────────────────────────────────────────────────

    async def get_post(self, post_id: uuid.UUID) -> FeedPostOut:
        sql = text("""
            SELECT
                fp.id,
                fp.author_id,
                fp.post_type,
                fp.title,
                fp.content,
                fp.media_url,
                fp.external_link,
                fp.visibility,
                fp.created_at,
                u.full_name   AS author_name,
                u.email       AS author_email,
                COUNT(DISTINCT fr.id) AS like_count,
                COUNT(DISTINCT fc.id) AS comment_count
            FROM   public.feed_posts    fp
            LEFT JOIN public.users          u  ON u.id  = fp.author_id
            LEFT JOIN public.feed_reactions fr ON fr.post_id = fp.id
            LEFT JOIN public.feed_comments  fc ON fc.post_id = fp.id
            WHERE  fp.id = :post_id
            GROUP  BY fp.id, u.full_name, u.email
        """)
        row = (await self.db.execute(sql, {"post_id": str(post_id)})).mappings().first()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
        return FeedPostOut(**row, is_liked=False)

    # ── get current user's posts ───────────────────────────────────────────

    async def get_my_posts(
        self, page: int, page_size: int, current_user: User
    ) -> FeedListResponse:
        offset = (page - 1) * page_size

        count_result = await self.db.execute(
            text("SELECT COUNT(*) FROM public.feed_posts WHERE author_id = :uid"),
            {"uid": str(current_user.id)},
        )
        total: int = count_result.scalar_one()

        sql = text("""
            SELECT
                fp.id,
                fp.author_id,
                fp.post_type,
                fp.title,
                fp.content,
                fp.media_url,
                fp.external_link,
                fp.visibility,
                fp.created_at,
                u.full_name   AS author_name,
                u.email       AS author_email,
                COUNT(DISTINCT fr.id) AS like_count,
                COUNT(DISTINCT fc.id) AS comment_count,
                BOOL_OR(fr.user_id = :uid2) AS is_liked
            FROM   public.feed_posts    fp
            LEFT JOIN public.users          u  ON u.id  = fp.author_id
            LEFT JOIN public.feed_reactions fr ON fr.post_id = fp.id
            LEFT JOIN public.feed_comments  fc ON fc.post_id = fp.id
            WHERE  fp.author_id = :uid3
            GROUP  BY fp.id, u.full_name, u.email
            ORDER  BY fp.created_at DESC
            LIMIT  :limit
            OFFSET :offset
        """)
        rows = (
            await self.db.execute(
                sql,
                {
                    "uid": str(current_user.id),
                    "uid2": str(current_user.id),
                    "uid3": str(current_user.id),
                    "limit": page_size,
                    "offset": offset,
                },
            )
        ).mappings().all()

        items = [
            FeedPostOut(
                id=r["id"],
                author_id=r["author_id"],
                post_type=r["post_type"],
                title=r["title"],
                content=r["content"],
                media_url=r["media_url"],
                external_link=r["external_link"],
                visibility=r["visibility"],
                created_at=r["created_at"],
                author_name=r["author_name"],
                author_email=r["author_email"],
                like_count=r["like_count"] or 0,
                comment_count=r["comment_count"] or 0,
                is_liked=bool(r["is_liked"]),
            )
            for r in rows
        ]
        return FeedListResponse(total=total, page=page, page_size=page_size, items=items)

    # ── delete own comment ─────────────────────────────────────────────────

    async def delete_comment(
        self, post_id: uuid.UUID, comment_id: uuid.UUID, current_user: User
    ) -> MessageResponse:
        await self._get_post_or_404(post_id)

        comment = await self.db.get(FeedComment, comment_id)
        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
        if comment.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your comment")

        await self.db.delete(comment)
        await self.db.flush()
        return MessageResponse(message="Comment deleted")

    # ── update own comment ─────────────────────────────────────────────────

    async def update_comment(
        self,
        post_id: uuid.UUID,
        comment_id: uuid.UUID,
        payload: UpdateCommentRequest,
        current_user: User,
    ) -> CommentOut:
        await self._get_post_or_404(post_id)

        comment = await self.db.get(FeedComment, comment_id)
        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
        if comment.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your comment")

        comment.comment_text = payload.comment_text
        await self.db.flush()
        await self.db.refresh(comment)

        return CommentOut(
            id=comment.id,
            user_id=comment.user_id,
            comment_text=comment.comment_text,
            created_at=comment.created_at,
            author_name=current_user.full_name,
        )
