"""SQLAlchemy 2 models for every table in the spec (section 5).

Every row has id, account_id, created_at, updated_at unless noted
(Account itself does not have account_id — it IS the account).
"""
from __future__ import annotations

import datetime as dt
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


# ── Mixins ──────────────────────────────────────────────────────
class TimestampMixin:
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow, nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime,
        default=dt.datetime.utcnow,
        onupdate=dt.datetime.utcnow,
        nullable=False,
    )


class AccountScopedMixin(TimestampMixin):
    """Mixin for every table that belongs to an account."""
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )


# ── Account (no account_id — it IS the account) ─────────────────
class Account(Base, TimestampMixin):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    two_factor_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # relationships
    profile: Mapped[Optional["Profile"]] = relationship(
        back_populates="account", uselist=False, cascade="all, delete-orphan"
    )
    brand_files: Mapped[List["BrandFile"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )
    runs: Mapped[List["Run"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )
    usage_records: Mapped[List["Usage"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )
    one_time_codes: Mapped[List["OneTimeCode"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )


# ── Profile ─────────────────────────────────────────────────────
class Profile(AccountScopedMixin, Base):
    __tablename__ = "profiles"

    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    business_type: Mapped[str] = mapped_column(String(255), nullable=False)
    products: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    audience: Mapped[str] = mapped_column(Text, nullable=False)
    tone: Mapped[str] = mapped_column(String(255), nullable=False)
    platforms: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    videos_per_week: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    brand_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)

    account: Mapped["Account"] = relationship(back_populates="profile")


# ── Brand File ──────────────────────────────────────────────────
class BrandFile(AccountScopedMixin, Base):
    __tablename__ = "brand_files"

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    extracted_text: Mapped[str] = mapped_column(Text, default="", nullable=False)

    account: Mapped["Account"] = relationship(back_populates="brand_files")


# ── Run ──────────────────────────────────────────────────────────
class Run(AccountScopedMixin, Base):
    __tablename__ = "runs"

    mode: Mapped[str] = mapped_column(String(50), nullable=False)  # weekly|campaign|both
    user_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    goal: Mapped[str] = mapped_column(Text, default="", nullable=False)
    constraints: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    task_plan: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="queued", nullable=False
    )  # queued|running|succeeded|failed|cancelled
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)
    credits_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    account: Mapped["Account"] = relationship(back_populates="runs")
    events: Mapped[List["RunEvent"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    content_plans: Mapped[List["ContentPlan"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    campaigns: Mapped[List["Campaign"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    validation_reports: Mapped[List["ValidationReport"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


# ── Run Event ────────────────────────────────────────────────────
class RunEvent(AccountScopedMixin, Base):
    __tablename__ = "run_events"

    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent: Mapped[str] = mapped_column(String(100), nullable=False)
    task: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # started|succeeded|failed
    started_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)
    detail: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    run: Mapped["Run"] = relationship(back_populates="events")


# ── Content Plan ─────────────────────────────────────────────────
class ContentPlan(AccountScopedMixin, Base):
    __tablename__ = "content_plans"

    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    week_start: Mapped[dt.date] = mapped_column(Date, nullable=False)
    strategy: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)

    run: Mapped["Run"] = relationship(back_populates="content_plans")
    posts: Mapped[List["Post"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )
    reply_drafts: Mapped[List["ReplyDraft"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )


# ── Post ─────────────────────────────────────────────────────────
class Post(AccountScopedMixin, Base):
    __tablename__ = "posts"

    plan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("content_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[Optional[dt.date]] = mapped_column(Date, nullable=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    format: Mapped[str] = mapped_column(String(50), nullable=False)
    pillar: Mapped[str] = mapped_column(String(100), nullable=False)
    caption: Mapped[str] = mapped_column(Text, default="", nullable=False)
    hook: Mapped[str] = mapped_column(Text, default="", nullable=False)
    script: Mapped[str] = mapped_column(Text, default="", nullable=False)
    shot_list: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    hashtags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    design_brief: Mapped[str] = mapped_column(Text, default="", nullable=False)
    on_screen_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="draft", nullable=False
    )  # draft|ready|posted

    plan: Mapped["ContentPlan"] = relationship(back_populates="posts")


# ── Reply Draft ─────────────────────────────────────────────────
class ReplyDraft(AccountScopedMixin, Base):
    __tablename__ = "reply_drafts"

    plan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("content_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # question|comment|dm|complaint
    question: Mapped[str] = mapped_column(Text, nullable=False)
    reply: Mapped[str] = mapped_column(Text, nullable=False)

    plan: Mapped["ContentPlan"] = relationship(back_populates="reply_drafts")


# ── Campaign ─────────────────────────────────────────────────────
class Campaign(AccountScopedMixin, Base):
    __tablename__ = "campaigns"

    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    template_inputs: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    phases: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    budget_plan: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    calendar: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)

    run: Mapped["Run"] = relationship(back_populates="campaigns")
    assets: Mapped[List["CampaignAsset"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )


# ── Campaign Asset ───────────────────────────────────────────────
class CampaignAsset(AccountScopedMixin, Base):
    __tablename__ = "campaign_assets"

    campaign_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # carousel|video|research_post|text_post|poll|outreach|comment_plan
    content: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)

    campaign: Mapped["Campaign"] = relationship(back_populates="assets")


# ── Asset Version ────────────────────────────────────────────────
class AssetVersion(AccountScopedMixin, Base):
    __tablename__ = "asset_versions"

    asset_kind: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # post|reply|campaign_asset
    asset_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    source: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # edit|regenerate|agent

    __table_args__ = (
        UniqueConstraint("asset_kind", "asset_id", "version_no", name="uq_asset_version"),
    )


# ── Validation Report ────────────────────────────────────────────
class ValidationReport(AccountScopedMixin, Base):
    __tablename__ = "validation_reports"

    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    checks: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)

    run: Mapped["Run"] = relationship(back_populates="validation_reports")


# ── Weekly Report ────────────────────────────────────────────────
class WeeklyReport(AccountScopedMixin, Base):
    __tablename__ = "weekly_reports"

    week_start: Mapped[dt.date] = mapped_column(Date, nullable=False)
    post_metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    orders: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    revenue_rm: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    costs: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    computed_metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    analysis: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    adapted_plan_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("content_plans.id", ondelete="SET NULL"), nullable=True
    )


# ── Period Report ────────────────────────────────────────────────
class PeriodReport(AccountScopedMixin, Base):
    __tablename__ = "period_reports"

    type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # monthly|quarterly|annual
    range_start: Mapped[dt.date] = mapped_column(Date, nullable=False)
    range_end: Mapped[dt.date] = mapped_column(Date, nullable=False)
    content: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


# ── Usage (daily run counter per account) ────────────────────────
class Usage(AccountScopedMixin, Base):
    __tablename__ = "usage"

    date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    runs_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    account: Mapped["Account"] = relationship(back_populates="usage_records")

    __table_args__ = (
        UniqueConstraint("account_id", "date", name="uq_account_date"),
    )


# ── One-Time Code (verify_email | two_factor | reset_password) ───
class OneTimeCode(AccountScopedMixin, Base):
    __tablename__ = "one_time_codes"

    code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    # verify_email | two_factor | reset_password
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    account: Mapped["Account"] = relationship(back_populates="one_time_codes")
