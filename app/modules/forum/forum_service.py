"""Business logic for the forum module — candidate search, invitations, chat."""

import uuid
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.modules.auth.model import User
from app.modules.forum.model import HiringInvitation, ChatMessage
from app.modules.forum.forum_schema import (
    CandidateOut,
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


class ForumService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── Candidate Search ─────────────────────────────────────────────────────

    async def search_candidates(
        self,
        city: str | None = None,
        job_role: str | None = None,
        experience_min: float | None = None,
        experience_max: float | None = None,
        skill: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> CandidateSearchResponse:
        """Search jobseekers by city, role, experience, skills."""

        conditions = ["u.role_id = 1"]  # Only jobseekers
        params: dict = {}

        if city:
            conditions.append("LOWER(p.location) LIKE :city")
            params["city"] = f"%{city.lower()}%"

        if job_role:
            conditions.append("(LOWER(p.current_position) LIKE :job_role OR LOWER(p.headline) LIKE :job_role)")
            params["job_role"] = f"%{job_role.lower()}%"

        if experience_min is not None:
            conditions.append("p.experience_years >= :exp_min")
            params["exp_min"] = experience_min

        if experience_max is not None:
            conditions.append("p.experience_years <= :exp_max")
            params["exp_max"] = experience_max

        if skill:
            conditions.append("""
                EXISTS (
                    SELECT 1 FROM public.user_skills us
                    WHERE us.user_id = u.id AND LOWER(us.skill_name) LIKE :skill
                )
            """)
            params["skill"] = f"%{skill.lower()}%"

        if keyword:
            conditions.append("""
                (LOWER(u.full_name) LIKE :keyword
                 OR LOWER(p.headline) LIKE :keyword
                 OR LOWER(p.bio) LIKE :keyword
                 OR LOWER(p.current_position) LIKE :keyword)
            """)
            params["keyword"] = f"%{keyword.lower()}%"

        where_clause = " AND ".join(conditions)
        offset = (page - 1) * page_size

        # Count
        count_sql = text(f"""
            SELECT COUNT(DISTINCT u.id)
            FROM public.users u
            LEFT JOIN public.user_profiles p ON p.user_id = u.id
            WHERE {where_clause}
        """)
        total = (await self.db.execute(count_sql, params)).scalar() or 0

        # Data
        params["limit"] = page_size
        params["offset"] = offset
        data_sql = text(f"""
            SELECT
                u.id AS user_id,
                u.full_name,
                u.email,
                u.profile_image,
                p.headline,
                p.current_position,
                p.current_company,
                p.experience_years,
                p.location,
                p.notice_period,
                COALESCE(
                    (SELECT array_agg(us.skill_name) FROM public.user_skills us WHERE us.user_id = u.id),
                    ARRAY[]::text[]
                ) AS skills
            FROM public.users u
            LEFT JOIN public.user_profiles p ON p.user_id = u.id
            WHERE {where_clause}
            ORDER BY p.experience_years DESC NULLS LAST, u.full_name
            LIMIT :limit OFFSET :offset
        """)

        rows = (await self.db.execute(data_sql, params)).mappings().all()
        items = [
            CandidateOut(
                user_id=r["user_id"],
                full_name=r["full_name"],
                email=r["email"],
                profile_image=r["profile_image"],
                headline=r["headline"],
                current_position=r["current_position"],
                current_company=r["current_company"],
                experience_years=r["experience_years"],
                location=r["location"],
                skills=list(r["skills"]) if r["skills"] else [],
                notice_period=r["notice_period"],
            )
            for r in rows
        ]

        return CandidateSearchResponse(total=total, page=page, page_size=page_size, items=items)

    # ─── Hiring Invitations ───────────────────────────────────────────────────

    async def send_invitation(
        self, payload: SendInvitationRequest, current_user: User
    ) -> InvitationOut:
        """Send a hiring invitation to a candidate."""
        # Verify receiver exists and is a jobseeker
        receiver = await self.db.get(User, payload.receiver_id)
        if not receiver:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        invitation = HiringInvitation(
            sender_id=current_user.id,
            receiver_id=payload.receiver_id,
            job_title=payload.job_title,
            message=payload.message,
        )
        self.db.add(invitation)
        await self.db.flush()
        await self.db.refresh(invitation)

        return InvitationOut(
            id=invitation.id,
            sender_id=invitation.sender_id,
            receiver_id=invitation.receiver_id,
            sender_name=current_user.full_name,
            receiver_name=receiver.full_name,
            job_title=invitation.job_title,
            message=invitation.message,
            status=invitation.status,
            created_at=invitation.created_at,
        )

    async def get_my_invitations(self, current_user: User, direction: str = "received") -> InvitationListResponse:
        """Get sent or received invitations."""
        if direction == "received":
            sql = text("""
                SELECT hi.*, s.full_name AS sender_name, r.full_name AS receiver_name
                FROM public.hiring_invitations hi
                JOIN public.users s ON s.id = hi.sender_id
                JOIN public.users r ON r.id = hi.receiver_id
                WHERE hi.receiver_id = :uid
                ORDER BY hi.created_at DESC
            """)
        else:
            sql = text("""
                SELECT hi.*, s.full_name AS sender_name, r.full_name AS receiver_name
                FROM public.hiring_invitations hi
                JOIN public.users s ON s.id = hi.sender_id
                JOIN public.users r ON r.id = hi.receiver_id
                WHERE hi.sender_id = :uid
                ORDER BY hi.created_at DESC
            """)

        rows = (await self.db.execute(sql, {"uid": str(current_user.id)})).mappings().all()
        items = [InvitationOut(**r) for r in rows]
        return InvitationListResponse(total=len(items), items=items)

    async def update_invitation(
        self, invitation_id: uuid.UUID, payload: UpdateInvitationRequest, current_user: User
    ) -> MessageResponse:
        """Accept or decline an invitation."""
        invitation = await self.db.get(HiringInvitation, invitation_id)
        if not invitation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
        if invitation.receiver_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your invitation")
        if payload.status not in ("ACCEPTED", "DECLINED"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status must be ACCEPTED or DECLINED")

        invitation.status = payload.status
        await self.db.flush()
        return MessageResponse(message=f"Invitation {payload.status.lower()}")

    # ─── Chat / Messages ─────────────────────────────────────────────────────

    async def send_message(self, payload: SendMessageRequest, current_user: User) -> MessageOut:
        """Send a direct message."""
        receiver = await self.db.get(User, payload.receiver_id)
        if not receiver:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        msg = ChatMessage(
            sender_id=current_user.id,
            receiver_id=payload.receiver_id,
            content=payload.content,
        )
        self.db.add(msg)
        await self.db.flush()
        await self.db.refresh(msg)

        return MessageOut(
            id=msg.id,
            sender_id=msg.sender_id,
            receiver_id=msg.receiver_id,
            content=msg.content,
            is_read=msg.is_read,
            created_at=msg.created_at,
            sender_name=current_user.full_name,
        )

    async def get_conversation(
        self, other_user_id: uuid.UUID, current_user: User, page: int = 1, page_size: int = 50
    ) -> list[MessageOut]:
        """Get messages between current user and another user."""
        offset = (page - 1) * page_size
        sql = text("""
            SELECT cm.*, u.full_name AS sender_name
            FROM public.chat_messages cm
            JOIN public.users u ON u.id = cm.sender_id
            WHERE (cm.sender_id = :uid AND cm.receiver_id = :other)
               OR (cm.sender_id = :other AND cm.receiver_id = :uid)
            ORDER BY cm.created_at ASC
            LIMIT :limit OFFSET :offset
        """)
        rows = (await self.db.execute(sql, {
            "uid": str(current_user.id),
            "other": str(other_user_id),
            "limit": page_size,
            "offset": offset,
        })).mappings().all()

        # Mark received messages as read
        await self.db.execute(
            text("UPDATE public.chat_messages SET is_read = true WHERE receiver_id = :uid AND sender_id = :other AND is_read = false"),
            {"uid": str(current_user.id), "other": str(other_user_id)},
        )
        await self.db.flush()

        return [MessageOut(**r) for r in rows]

    async def get_conversations(self, current_user: User) -> list[ConversationOut]:
        """Get list of conversations (unique users you've chatted with)."""
        sql = text("""
            SELECT DISTINCT ON (other_id)
                other_id AS user_id,
                u.full_name,
                u.profile_image,
                last_msg AS last_message,
                last_at AS last_message_at,
                COALESCE(unread.cnt, 0)::int AS unread_count
            FROM (
                SELECT
                    CASE WHEN sender_id = :uid THEN receiver_id ELSE sender_id END AS other_id,
                    content AS last_msg,
                    created_at AS last_at
                FROM public.chat_messages
                WHERE sender_id = :uid OR receiver_id = :uid
                ORDER BY other_id, created_at DESC
            ) sub
            JOIN public.users u ON u.id = sub.other_id
            LEFT JOIN (
                SELECT sender_id, COUNT(*) AS cnt
                FROM public.chat_messages
                WHERE receiver_id = :uid AND is_read = false
                GROUP BY sender_id
            ) unread ON unread.sender_id = sub.other_id
            ORDER BY other_id, last_at DESC
        """)
        rows = (await self.db.execute(sql, {"uid": str(current_user.id)})).mappings().all()
        return [ConversationOut(**r) for r in rows]
