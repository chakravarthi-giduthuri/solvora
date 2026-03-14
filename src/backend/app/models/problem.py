import uuid
from datetime import datetime, timezone, date
from typing import Optional, List
from sqlalchemy import String, Text, Boolean, Float, Integer, DateTime, Date, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)

class Problem(Base):
    __tablename__ = "problems"
    __table_args__ = (
        UniqueConstraint("source_id", "platform", name="uq_source_platform"),
        CheckConstraint("platform IN ('reddit','hackernews','twitter','user')", name="ck_platform"),
        CheckConstraint("sentiment IN ('urgent','frustrated','curious','neutral') OR sentiment IS NULL", name="ck_sentiment"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(1024), unique=True, nullable=False)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
    author_handle: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    upvotes: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    subreddit: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    sentiment: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_problem: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    potd_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    share_count: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(16), default="scraped")
    tags_auto: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submitted_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    solutions: Mapped[List["Solution"]] = relationship("Solution", back_populates="problem", cascade="all, delete-orphan")
    bookmarks: Mapped[List["Bookmark"]] = relationship("Bookmark", back_populates="problem", cascade="all, delete-orphan")
    tags: Mapped[List["ProblemTag"]] = relationship("ProblemTag", cascade="all, delete-orphan")
    reports: Mapped[List["ProblemReport"]] = relationship("ProblemReport", cascade="all, delete-orphan", foreign_keys="ProblemReport.problem_id")

class Solution(Base):
    __tablename__ = "solutions"
    __table_args__ = (
        CheckConstraint("provider IN ('gemini','openai','claude')", name="ck_provider"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    problem_id: Mapped[str] = mapped_column(String(36), ForeignKey("problems.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    solution_text: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, default=0)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    problem: Mapped["Problem"] = relationship("Problem", back_populates="solutions")
    votes: Mapped[List["Vote"]] = relationship("Vote", back_populates="solution", cascade="all, delete-orphan")
    comments: Mapped[List["Comment"]] = relationship("Comment", back_populates=None, cascade="all, delete-orphan", foreign_keys="Comment.solution_id")

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("auth_provider IN ('email','google')", name="ck_auth_provider"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    auth_provider: Mapped[str] = mapped_column(String(32), nullable=False, default="email")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    bookmarks: Mapped[List["Bookmark"]] = relationship("Bookmark", back_populates="user", cascade="all, delete-orphan")
    votes: Mapped[List["Vote"]] = relationship("Vote", back_populates="user", cascade="all, delete-orphan")

class Bookmark(Base):
    __tablename__ = "bookmarks"
    __table_args__ = (
        UniqueConstraint("user_id", "problem_id", name="uq_user_problem_bookmark"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    problem_id: Mapped[str] = mapped_column(String(36), ForeignKey("problems.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship("User", back_populates="bookmarks")
    problem: Mapped["Problem"] = relationship("Problem", back_populates="bookmarks")

class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("user_id", "solution_id", name="uq_user_solution_vote"),
        CheckConstraint("vote_type IN (1, -1)", name="ck_vote_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    solution_id: Mapped[str] = mapped_column(String(36), ForeignKey("solutions.id", ondelete="CASCADE"), nullable=False)
    vote_type: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship("User", back_populates="votes")
    solution: Mapped["Solution"] = relationship("Solution", back_populates="votes")

class ProblemClick(Base):
    __tablename__ = "problem_clicks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    problem_id: Mapped[str] = mapped_column(String(36), ForeignKey("problems.id", ondelete="CASCADE"), nullable=False, index=True)
    clicked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    use_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProblemTag(Base):
    __tablename__ = "problem_tags"
    __table_args__ = (UniqueConstraint("problem_id", "tag_id", name="uq_problem_tag"),)

    problem_id: Mapped[str] = mapped_column(String(36), ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[str] = mapped_column(String(36), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FilterPreset(Base):
    __tablename__ = "filter_presets"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_user_preset_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    filters: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    solution_id: Mapped[str] = mapped_column(String(36), ForeignKey("solutions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("comments.id", ondelete="CASCADE"), nullable=True, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship("User")
    replies: Mapped[List["Comment"]] = relationship(
        "Comment",
        back_populates="parent",
        foreign_keys="Comment.parent_id",
    )
    parent: Mapped[Optional["Comment"]] = relationship(
        "Comment",
        back_populates="replies",
        foreign_keys="Comment.parent_id",
        remote_side="Comment.id",
    )


class UserNotificationPrefs(Base):
    __tablename__ = "user_notification_prefs"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    digest_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    digest_day: Mapped[int] = mapped_column(Integer, default=1)
    digest_hour_utc: Mapped[int] = mapped_column(Integer, default=8)
    category_interests: Mapped[str] = mapped_column(Text, default="[]")
    notify_on_comment: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_vote: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class DigestSend(Base):
    __tablename__ = "digest_sends"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    problem_ids: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(16), default="sent")


class ProblemReport(Base):
    __tablename__ = "problem_reports"
    __table_args__ = (
        UniqueConstraint("problem_id", "reporter_id", name="uq_problem_reporter"),
        CheckConstraint("reason IN ('spam','inappropriate','duplicate','other')", name="ck_report_reason"),
        CheckConstraint("status IN ('pending','reviewed','dismissed')", name="ck_report_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    problem_id: Mapped[str] = mapped_column(String(36), ForeignKey("problems.id", ondelete="CASCADE"), nullable=False, index=True)
    reporter_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
