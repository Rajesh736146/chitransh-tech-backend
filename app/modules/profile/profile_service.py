"""Business logic for user profiles and social interactions."""

import uuid
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text

from app.modules.auth.model import User
from app.modules.profile.model import (
    UserProfile,
    UserSkill,
    UserEducation,
    UserExperience,
    UserConnection,
    ProfileView,
    SkillEndorsement,
    ProfileShare,
)
from app.modules.profile.profile_schema import (
    ProfileUpdateRequest,
    ProfileOut,
    SkillCreateRequest,
    SkillOut,
    EducationCreateRequest,
    EducationOut,
    ExperienceCreateRequest,
    ExperienceOut,
    FollowOut,
    FollowListResponse,
    ProfileViewOut,
    ShareProfileRequest,
    MessageResponse,
)


class ProfileService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── Profile CRUD ─────────────────────────────────────────────────────────

    async def get_profile(
        self, user_id: uuid.UUID, current_user: User | None = None
    ) -> ProfileOut:
        """Get a user's full profile with social stats."""

        sql = text("""
            SELECT
                u.id AS user_id,
                u.full_name,
                u.email,
                u.phone,
                u.profile_image,
                p.headline,
                p.bio,
                p.current_company,
                p.current_position,
                p.experience_years,
                p.location,
                p.notice_period,
                p.portfolio_url,
                p.linkedin_url,
                p.github_url,
                COALESCE(fc.follower_count, 0)::int AS follower_count,
                COALESCE(fg.following_count, 0)::int AS following_count,
                COALESCE(pv.view_count, 0)::int AS profile_view_count
            FROM public.users u
            LEFT JOIN public.user_profiles p ON p.user_id = u.id
            LEFT JOIN (
                SELECT following_id, COUNT(*) AS follower_count
                FROM public.user_connections
                GROUP BY following_id
            ) fc ON fc.following_id = u.id
            LEFT JOIN (
                SELECT follower_id, COUNT(*) AS following_count
                FROM public.user_connections
                GROUP BY follower_id
            ) fg ON fg.follower_id = u.id
            LEFT JOIN (
                SELECT viewed_id, COUNT(*) AS view_count
                FROM public.profile_views
                GROUP BY viewed_id
            ) pv ON pv.viewed_id = u.id
            WHERE u.id = :user_id
        """)

        row = (await self.db.execute(sql, {"user_id": str(user_id)})).mappings().first()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Check if current user follows this profile
        is_following = False
        if current_user and current_user.id != user_id:
            follow_check = await self.db.execute(
                select(UserConnection).where(
                    UserConnection.follower_id == current_user.id,
                    UserConnection.following_id == user_id,
                )
            )
            is_following = follow_check.scalar_one_or_none() is not None

            # Record profile view
            view = ProfileView(viewer_id=current_user.id, viewed_id=user_id)
            self.db.add(view)
            await self.db.flush()

        return ProfileOut(**row, is_following=is_following)

    async def update_profile(
        self, payload: ProfileUpdateRequest, current_user: User
    ) -> ProfileOut:
        """Update or create the current user's profile."""

        profile = (
            await self.db.execute(
                select(UserProfile).where(UserProfile.user_id == current_user.id)
            )
        ).scalar_one_or_none()

        if not profile:
            profile = UserProfile(user_id=current_user.id)
            self.db.add(profile)
            await self.db.flush()

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(profile, field, value)

        await self.db.flush()
        await self.db.refresh(profile)

        return await self.get_profile(current_user.id, current_user)

    # ─── Skills ───────────────────────────────────────────────────────────────

    async def add_skill(self, payload: SkillCreateRequest, current_user: User) -> SkillOut:
        skill = UserSkill(
            user_id=current_user.id,
            skill_name=payload.skill_name,
            experience_years=payload.experience_years,
            skill_level=payload.skill_level,
        )
        self.db.add(skill)
        await self.db.flush()
        await self.db.refresh(skill)
        return SkillOut(
            id=skill.id,
            skill_name=skill.skill_name,
            experience_years=skill.experience_years,
            skill_level=skill.skill_level,
            endorsement_count=0,
            is_endorsed_by_me=False,
        )

    async def get_user_skills(
        self, user_id: uuid.UUID, current_user: User | None = None
    ) -> list[SkillOut]:
        sql = text("""
            SELECT
                us.id,
                us.skill_name,
                us.experience_years,
                us.skill_level,
                COALESCE(e.cnt, 0)::int AS endorsement_count,
                BOOL_OR(e.endorser_id = :viewer_id) AS is_endorsed_by_me
            FROM public.user_skills us
            LEFT JOIN (
                SELECT skill_id, COUNT(*) AS cnt, endorser_id
                FROM public.skill_endorsements
                GROUP BY skill_id, endorser_id
            ) e ON e.skill_id = us.id
            WHERE us.user_id = :user_id
            GROUP BY us.id, us.skill_name, us.experience_years, us.skill_level
            ORDER BY endorsement_count DESC, us.skill_name
        """)
        viewer_id = str(current_user.id) if current_user else str(uuid.UUID(int=0))
        rows = (await self.db.execute(sql, {"user_id": str(user_id), "viewer_id": viewer_id})).mappings().all()

        return [
            SkillOut(
                id=r["id"],
                skill_name=r["skill_name"],
                experience_years=r["experience_years"],
                skill_level=r["skill_level"],
                endorsement_count=r["endorsement_count"],
                is_endorsed_by_me=bool(r["is_endorsed_by_me"]),
            )
            for r in rows
        ]

    async def delete_skill(self, skill_id: uuid.UUID, current_user: User) -> MessageResponse:
        skill = await self.db.get(UserSkill, skill_id)
        if not skill:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
        if skill.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your skill")
        await self.db.delete(skill)
        await self.db.flush()
        return MessageResponse(message="Skill removed")

    # ─── Education ────────────────────────────────────────────────────────────

    async def add_education(self, payload: EducationCreateRequest, current_user: User) -> EducationOut:
        edu = UserEducation(user_id=current_user.id, **payload.model_dump())
        self.db.add(edu)
        await self.db.flush()
        await self.db.refresh(edu)
        return EducationOut.model_validate(edu)

    async def get_user_education(self, user_id: uuid.UUID) -> list[EducationOut]:
        result = await self.db.execute(
            select(UserEducation)
            .where(UserEducation.user_id == user_id)
            .order_by(UserEducation.end_year.desc().nullslast())
        )
        return [EducationOut.model_validate(e) for e in result.scalars().all()]

    async def delete_education(self, edu_id: uuid.UUID, current_user: User) -> MessageResponse:
        edu = await self.db.get(UserEducation, edu_id)
        if not edu:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Education not found")
        if edu.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not yours")
        await self.db.delete(edu)
        await self.db.flush()
        return MessageResponse(message="Education removed")

    # ─── Experience ───────────────────────────────────────────────────────────

    async def add_experience(self, payload: ExperienceCreateRequest, current_user: User) -> ExperienceOut:
        exp = UserExperience(user_id=current_user.id, **payload.model_dump())
        self.db.add(exp)
        await self.db.flush()
        await self.db.refresh(exp)
        return ExperienceOut.model_validate(exp)

    async def get_user_experience(self, user_id: uuid.UUID) -> list[ExperienceOut]:
        result = await self.db.execute(
            select(UserExperience)
            .where(UserExperience.user_id == user_id)
            .order_by(UserExperience.start_date.desc().nullslast())
        )
        return [ExperienceOut.model_validate(e) for e in result.scalars().all()]

    async def delete_experience(self, exp_id: uuid.UUID, current_user: User) -> MessageResponse:
        exp = await self.db.get(UserExperience, exp_id)
        if not exp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experience not found")
        if exp.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not yours")
        await self.db.delete(exp)
        await self.db.flush()
        return MessageResponse(message="Experience removed")

    # ─── Follow / Unfollow ────────────────────────────────────────────────────

    async def toggle_follow(self, target_user_id: uuid.UUID, current_user: User) -> MessageResponse:
        if target_user_id == current_user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot follow yourself")

        # Check target exists
        target = await self.db.get(User, target_user_id)
        if not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        existing = await self.db.execute(
            select(UserConnection).where(
                UserConnection.follower_id == current_user.id,
                UserConnection.following_id == target_user_id,
            )
        )
        connection = existing.scalar_one_or_none()

        if connection:
            await self.db.delete(connection)
            await self.db.flush()
            return MessageResponse(message="Unfollowed")

        self.db.add(UserConnection(follower_id=current_user.id, following_id=target_user_id))
        await self.db.flush()
        return MessageResponse(message="Followed")

    async def get_followers(self, user_id: uuid.UUID) -> FollowListResponse:
        sql = text("""
            SELECT
                u.id AS user_id,
                u.full_name,
                u.profile_image,
                p.headline
            FROM public.user_connections uc
            JOIN public.users u ON u.id = uc.follower_id
            LEFT JOIN public.user_profiles p ON p.user_id = u.id
            WHERE uc.following_id = :user_id
            ORDER BY uc.created_at DESC
        """)
        rows = (await self.db.execute(sql, {"user_id": str(user_id)})).mappings().all()
        items = [FollowOut(**r) for r in rows]
        return FollowListResponse(total=len(items), items=items)

    async def get_following(self, user_id: uuid.UUID) -> FollowListResponse:
        sql = text("""
            SELECT
                u.id AS user_id,
                u.full_name,
                u.profile_image,
                p.headline
            FROM public.user_connections uc
            JOIN public.users u ON u.id = uc.following_id
            LEFT JOIN public.user_profiles p ON p.user_id = u.id
            WHERE uc.follower_id = :user_id
            ORDER BY uc.created_at DESC
        """)
        rows = (await self.db.execute(sql, {"user_id": str(user_id)})).mappings().all()
        items = [FollowOut(**r) for r in rows]
        return FollowListResponse(total=len(items), items=items)

    # ─── Endorse Skill ────────────────────────────────────────────────────────

    async def toggle_endorse_skill(self, skill_id: uuid.UUID, current_user: User) -> MessageResponse:
        skill = await self.db.get(UserSkill, skill_id)
        if not skill:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
        if skill.user_id == current_user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot endorse your own skill")

        existing = await self.db.execute(
            select(SkillEndorsement).where(
                SkillEndorsement.endorser_id == current_user.id,
                SkillEndorsement.skill_id == skill_id,
            )
        )
        endorsement = existing.scalar_one_or_none()

        if endorsement:
            await self.db.delete(endorsement)
            await self.db.flush()
            return MessageResponse(message="Endorsement removed")

        self.db.add(SkillEndorsement(endorser_id=current_user.id, skill_id=skill_id))
        await self.db.flush()
        return MessageResponse(message="Skill endorsed")

    # ─── Share Profile ────────────────────────────────────────────────────────

    async def share_profile(
        self, target_user_id: uuid.UUID, payload: ShareProfileRequest, current_user: User
    ) -> MessageResponse:
        target = await self.db.get(User, target_user_id)
        if not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        share = ProfileShare(
            sharer_id=current_user.id,
            shared_profile_id=target_user_id,
            platform=payload.platform,
        )
        self.db.add(share)
        await self.db.flush()
        return MessageResponse(message=f"Profile shared{' on ' + payload.platform if payload.platform else ''}")

    # ─── Profile Views (who viewed me) ────────────────────────────────────────

    async def get_profile_views(self, current_user: User) -> list[ProfileViewOut]:
        sql = text("""
            SELECT DISTINCT ON (pv.viewer_id)
                pv.viewer_id,
                u.full_name,
                u.profile_image,
                p.headline,
                pv.viewed_at
            FROM public.profile_views pv
            JOIN public.users u ON u.id = pv.viewer_id
            LEFT JOIN public.user_profiles p ON p.user_id = u.id
            WHERE pv.viewed_id = :user_id
            ORDER BY pv.viewer_id, pv.viewed_at DESC
        """)
        rows = (await self.db.execute(sql, {"user_id": str(current_user.id)})).mappings().all()
        return [ProfileViewOut(**r) for r in rows]
