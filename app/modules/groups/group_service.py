"""Business logic for the groups module."""

import uuid
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.modules.auth.model import User
from app.modules.groups.model import Group, GroupMember, GroupPost, GroupPostReaction, GroupPostComment
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


class GroupService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── Group CRUD ───────────────────────────────────────────────────────────

    async def create_group(self, payload: GroupCreateRequest, current_user: User) -> GroupOut:
        group = Group(
            name=payload.name,
            description=payload.description,
            cover_image=payload.cover_image,
            category=payload.category,
            created_by=current_user.id,
        )
        self.db.add(group)
        await self.db.flush()

        # Creator auto-joins as admin
        member = GroupMember(group_id=group.id, user_id=current_user.id, role="admin")
        self.db.add(member)
        await self.db.flush()
        await self.db.refresh(group)

        return GroupOut(
            id=group.id,
            name=group.name,
            description=group.description,
            cover_image=group.cover_image,
            category=group.category,
            created_by=group.created_by,
            member_count=1,
            is_member=True,
            created_at=group.created_at,
        )

    async def list_groups(
        self,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
        search: str | None = None,
        current_user: User | None = None,
    ) -> GroupListResponse:
        conditions = ["1=1"]
        params: dict = {}

        if category:
            conditions.append("g.category = :category")
            params["category"] = category

        if search:
            conditions.append("(g.name ILIKE :search OR g.description ILIKE :search)")
            params["search"] = f"%{search}%"

        where_clause = " AND ".join(conditions)
        user_id_str = str(current_user.id) if current_user else str(uuid.UUID(int=0))
        params["viewer_id"] = user_id_str

        count_sql = text(f"SELECT COUNT(*) FROM public.groups g WHERE {where_clause}")
        total = (await self.db.execute(count_sql, params)).scalar() or 0

        offset = (page - 1) * page_size
        params["limit"] = page_size
        params["offset"] = offset

        data_sql = text(f"""
            SELECT
                g.id, g.name, g.description, g.cover_image, g.category,
                g.created_by, g.created_at,
                COALESCE(mc.cnt, 0)::int AS member_count,
                EXISTS(
                    SELECT 1 FROM public.group_members gm2
                    WHERE gm2.group_id = g.id AND gm2.user_id = :viewer_id
                ) AS is_member
            FROM public.groups g
            LEFT JOIN (
                SELECT group_id, COUNT(*) AS cnt FROM public.group_members GROUP BY group_id
            ) mc ON mc.group_id = g.id
            WHERE {where_clause}
            ORDER BY g.created_at DESC
            LIMIT :limit OFFSET :offset
        """)

        rows = (await self.db.execute(data_sql, params)).mappings().all()
        items = [GroupOut(**r) for r in rows]

        return GroupListResponse(total=total, page=page, page_size=page_size, items=items)

    async def get_group(self, group_id: uuid.UUID, current_user: User | None = None) -> GroupOut:
        user_id_str = str(current_user.id) if current_user else str(uuid.UUID(int=0))

        sql = text("""
            SELECT
                g.id, g.name, g.description, g.cover_image, g.category,
                g.created_by, g.created_at,
                COALESCE(mc.cnt, 0)::int AS member_count,
                EXISTS(
                    SELECT 1 FROM public.group_members gm2
                    WHERE gm2.group_id = g.id AND gm2.user_id = :viewer_id
                ) AS is_member
            FROM public.groups g
            LEFT JOIN (
                SELECT group_id, COUNT(*) AS cnt FROM public.group_members GROUP BY group_id
            ) mc ON mc.group_id = g.id
            WHERE g.id = :group_id
        """)
        row = (await self.db.execute(sql, {"group_id": str(group_id), "viewer_id": user_id_str})).mappings().first()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
        return GroupOut(**row)

    async def update_group(
        self, group_id: uuid.UUID, payload: GroupUpdateRequest, current_user: User
    ) -> GroupOut:
        group = await self.db.get(Group, group_id)
        if not group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
        if group.created_by != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the group creator can update")

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(group, field, value)
        await self.db.flush()

        return await self.get_group(group_id, current_user)

    async def delete_group(self, group_id: uuid.UUID, current_user: User) -> MessageResponse:
        group = await self.db.get(Group, group_id)
        if not group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
        if group.created_by != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the group creator can delete")
        await self.db.delete(group)
        await self.db.flush()
        return MessageResponse(message="Group deleted")

    # ─── Membership ───────────────────────────────────────────────────────────

    async def join_group(self, group_id: uuid.UUID, current_user: User) -> MessageResponse:
        group = await self.db.get(Group, group_id)
        if not group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

        existing = await self.db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id, GroupMember.user_id == current_user.id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already a member")

        self.db.add(GroupMember(group_id=group_id, user_id=current_user.id, role="member"))
        await self.db.flush()
        return MessageResponse(message="Joined group")

    async def leave_group(self, group_id: uuid.UUID, current_user: User) -> MessageResponse:
        existing = await self.db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id, GroupMember.user_id == current_user.id
            )
        )
        member = existing.scalar_one_or_none()
        if not member:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not a member")

        group = await self.db.get(Group, group_id)
        if group and group.created_by == current_user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Creator cannot leave. Delete the group instead.")

        await self.db.delete(member)
        await self.db.flush()
        return MessageResponse(message="Left group")

    async def get_members(self, group_id: uuid.UUID) -> list[GroupMemberOut]:
        sql = text("""
            SELECT gm.user_id, u.full_name, u.profile_image, gm.role, gm.joined_at
            FROM public.group_members gm
            JOIN public.users u ON u.id = gm.user_id
            WHERE gm.group_id = :group_id
            ORDER BY gm.joined_at
        """)
        rows = (await self.db.execute(sql, {"group_id": str(group_id)})).mappings().all()
        return [GroupMemberOut(**r) for r in rows]

    # ─── Group Posts ──────────────────────────────────────────────────────────

    async def create_post(
        self, group_id: uuid.UUID, payload: GroupPostCreateRequest, current_user: User
    ) -> GroupPostOut:
        # Must be a member
        existing = await self.db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id, GroupMember.user_id == current_user.id
            )
        )
        if not existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Must be a group member to post")

        post = GroupPost(
            group_id=group_id,
            author_id=current_user.id,
            title=payload.title,
            content=payload.content,
            media_url=payload.media_url,
        )
        self.db.add(post)
        await self.db.flush()
        await self.db.refresh(post)

        group = await self.db.get(Group, group_id)

        return GroupPostOut(
            id=post.id,
            group_id=post.group_id,
            author_id=post.author_id,
            title=post.title,
            content=post.content,
            media_url=post.media_url,
            created_at=post.created_at,
            author_name=current_user.full_name,
            group_name=group.name if group else None,
            like_count=0,
            comment_count=0,
            is_liked=False,
        )

    async def list_group_posts(
        self,
        group_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        current_user: User | None = None,
    ) -> GroupPostListResponse:
        user_id_str = str(current_user.id) if current_user else str(uuid.UUID(int=0))
        offset = (page - 1) * page_size

        count_sql = text("SELECT COUNT(*) FROM public.group_posts WHERE group_id = :gid")
        total = (await self.db.execute(count_sql, {"gid": str(group_id)})).scalar() or 0

        data_sql = text("""
            SELECT
                gp.id, gp.group_id, gp.author_id, gp.title, gp.content,
                gp.media_url, gp.created_at,
                u.full_name AS author_name,
                g.name AS group_name,
                COUNT(DISTINCT gr.id) AS like_count,
                COUNT(DISTINCT gc.id) AS comment_count,
                BOOL_OR(gr.user_id = :viewer_id) AS is_liked
            FROM public.group_posts gp
            JOIN public.users u ON u.id = gp.author_id
            JOIN public.groups g ON g.id = gp.group_id
            LEFT JOIN public.group_post_reactions gr ON gr.post_id = gp.id
            LEFT JOIN public.group_post_comments gc ON gc.post_id = gp.id
            WHERE gp.group_id = :gid
            GROUP BY gp.id, u.full_name, g.name
            ORDER BY gp.created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        rows = (await self.db.execute(
            data_sql, {"gid": str(group_id), "viewer_id": user_id_str, "limit": page_size, "offset": offset}
        )).mappings().all()

        items = [GroupPostOut(**{**r, "is_liked": bool(r["is_liked"])}) for r in rows]
        return GroupPostListResponse(total=total, page=page, page_size=page_size, items=items)

    # ─── Like / Unlike group post ─────────────────────────────────────────────

    async def toggle_like(self, post_id: uuid.UUID, current_user: User) -> MessageResponse:
        post = await self.db.get(GroupPost, post_id)
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

        existing = await self.db.execute(
            select(GroupPostReaction).where(
                GroupPostReaction.post_id == post_id, GroupPostReaction.user_id == current_user.id
            )
        )
        reaction = existing.scalar_one_or_none()
        if reaction:
            await self.db.delete(reaction)
            await self.db.flush()
            return MessageResponse(message="Unliked")

        self.db.add(GroupPostReaction(post_id=post_id, user_id=current_user.id))
        await self.db.flush()
        return MessageResponse(message="Liked")

    # ─── Comments ─────────────────────────────────────────────────────────────

    async def add_comment(
        self, post_id: uuid.UUID, payload: GroupCommentRequest, current_user: User
    ) -> GroupCommentOut:
        post = await self.db.get(GroupPost, post_id)
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

        comment = GroupPostComment(
            post_id=post_id, user_id=current_user.id, comment_text=payload.comment_text
        )
        self.db.add(comment)
        await self.db.flush()
        await self.db.refresh(comment)
        return GroupCommentOut(
            id=comment.id,
            user_id=comment.user_id,
            comment_text=comment.comment_text,
            created_at=comment.created_at,
            author_name=current_user.full_name,
        )

    async def get_comments(self, post_id: uuid.UUID) -> list[GroupCommentOut]:
        sql = text("""
            SELECT gc.id, gc.user_id, gc.comment_text, gc.created_at, u.full_name AS author_name
            FROM public.group_post_comments gc
            JOIN public.users u ON u.id = gc.user_id
            WHERE gc.post_id = :post_id
            ORDER BY gc.created_at ASC
        """)
        rows = (await self.db.execute(sql, {"post_id": str(post_id)})).mappings().all()
        return [GroupCommentOut(**r) for r in rows]

    async def delete_post(self, post_id: uuid.UUID, current_user: User) -> MessageResponse:
        post = await self.db.get(GroupPost, post_id)
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
        if post.author_id != current_user.id:
            # Check if user is group admin
            member = await self.db.execute(
                select(GroupMember).where(
                    GroupMember.group_id == post.group_id,
                    GroupMember.user_id == current_user.id,
                    GroupMember.role == "admin",
                )
            )
            if not member.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        await self.db.delete(post)
        await self.db.flush()
        return MessageResponse(message="Post deleted")
