"""ORM models for feed_posts, feed_reactions, feed_comments."""

import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class FeedPost(Base):
    __tablename__ = "feed_posts"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("uuid_generate_v4()"),
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("public.users.id", ondelete="SET NULL"), nullable=True
    )
    post_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    visibility: Mapped[str] = mapped_column(String(50), server_default="PUBLIC")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    reactions: Mapped[list["FeedReaction"]] = relationship(
        "FeedReaction", back_populates="post", cascade="all, delete-orphan", lazy="selectin"
    )
    comments: Mapped[list["FeedComment"]] = relationship(
        "FeedComment", back_populates="post", cascade="all, delete-orphan", lazy="selectin"
    )


class FeedReaction(Base):
    __tablename__ = "feed_reactions"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("uuid_generate_v4()")
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("public.feed_posts.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False
    )
    reaction_type: Mapped[str] = mapped_column(String(50), server_default="LIKE")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    post: Mapped["FeedPost"] = relationship("FeedPost", back_populates="reactions")


class FeedComment(Base):
    __tablename__ = "feed_comments"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("uuid_generate_v4()")
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("public.feed_posts.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False
    )
    comment_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    post: Mapped["FeedPost"] = relationship("FeedPost", back_populates="comments")
