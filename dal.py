"""Data Access Layer — every query takes account_id and filters by it.

No endpoint or service may query a table without passing account_id.
This is the ONLY place that should create/read/update/delete rows.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Generic, Optional, Type, TypeVar

from sqlalchemy import select, func, delete
from sqlalchemy.orm import Session

from app.db import models

T = TypeVar("T", bound=models.AccountScopedMixin)


class BaseDAL(Generic[T]):
    """Generic CRUD that always filters by account_id."""

    model: Type[T]

    def __init__(self, db: Session, account_id: int):
        self.db = db
        self.account_id = account_id

    def get(self, row_id: int) -> Optional[T]:
        stmt = select(self.model).where(
            self.model.id == row_id,
            self.model.account_id == self.account_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list(self, **filters: Any) -> list[T]:
        stmt = select(self.model).where(self.model.account_id == self.account_id)
        for key, value in filters.items():
            if hasattr(self.model, key):
                stmt = stmt.where(getattr(self.model, key) == value)
        return list(self.db.execute(stmt).scalars().all())

    def create(self, **fields: Any) -> T:
        obj = self.model(account_id=self.account_id, **fields)
        self.db.add(obj)
        self.db.flush()
        return obj

    def update(self, row_id: int, **fields: Any) -> Optional[T]:
        obj = self.get(row_id)
        if obj is None:
            return None
        for key, value in fields.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        self.db.flush()
        return obj

    def delete(self, row_id: int) -> bool:
        obj = self.get(row_id)
        if obj is None:
            return False
        self.db.delete(obj)
        self.db.flush()
        return True


# ── Account DAL (does NOT have account_id — it IS the account) ──
class AccountDAL:
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> Optional[models.Account]:
        return self.db.execute(
            select(models.Account).where(models.Account.email == email)
        ).scalar_one_or_none()

    def get_by_id(self, account_id: int) -> Optional[models.Account]:
        return self.db.get(models.Account, account_id)

    def create(
        self,
        *,
        email: str,
        password_hash: str,
        email_verified: bool = False,
        is_demo: bool = False,
        two_factor_enabled: bool = False,
    ) -> models.Account:
        obj = models.Account(
            email=email,
            password_hash=password_hash,
            email_verified=email_verified,
            is_demo=is_demo,
            two_factor_enabled=two_factor_enabled,
        )
        self.db.add(obj)
        self.db.flush()
        return obj

    def delete(self, account_id: int) -> bool:
        obj = self.get_by_id(account_id)
        if obj is None:
            return False
        self.db.delete(obj)
        self.db.flush()
        return True


# ── Typed DALs for each model ────────────────────────────────────
class ProfileDAL(BaseDAL[models.Profile]):
    model = models.Profile

    def get_for_account(self) -> Optional[models.Profile]:
        return self.db.execute(
            select(self.model).where(self.model.account_id == self.account_id)
        ).scalar_one_or_none()


class BrandFileDAL(BaseDAL[models.BrandFile]):
    model = models.BrandFile


class RunDAL(BaseDAL[models.Run]):
    model = models.Run


class RunEventDAL(BaseDAL[models.RunEvent]):
    model = models.RunEvent

    def list_for_run(self, run_id: int) -> list[models.RunEvent]:
        stmt = select(self.model).where(
            self.model.run_id == run_id,
            self.model.account_id == self.account_id,
        ).order_by(self.model.id)
        return list(self.db.execute(stmt).scalars().all())


class ContentPlanDAL(BaseDAL[models.ContentPlan]):
    model = models.ContentPlan


class PostDAL(BaseDAL[models.Post]):
    model = models.Post

    def list_for_plan(self, plan_id: int) -> list[models.Post]:
        stmt = select(self.model).where(
            self.model.plan_id == plan_id,
            self.model.account_id == self.account_id,
        ).order_by(self.model.id)
        return list(self.db.execute(stmt).scalars().all())


class ReplyDraftDAL(BaseDAL[models.ReplyDraft]):
    model = models.ReplyDraft

    def list_for_plan(self, plan_id: int) -> list[models.ReplyDraft]:
        stmt = select(self.model).where(
            self.model.plan_id == plan_id,
            self.model.account_id == self.account_id,
        ).order_by(self.model.id)
        return list(self.db.execute(stmt).scalars().all())


class CampaignDAL(BaseDAL[models.Campaign]):
    model = models.Campaign


class CampaignAssetDAL(BaseDAL[models.CampaignAsset]):
    model = models.CampaignAsset

    def list_for_campaign(self, campaign_id: int) -> list[models.CampaignAsset]:
        stmt = select(self.model).where(
            self.model.campaign_id == campaign_id,
            self.model.account_id == self.account_id,
        ).order_by(self.model.id)
        return list(self.db.execute(stmt).scalars().all())


class AssetVersionDAL(BaseDAL[models.AssetVersion]):
    model = models.AssetVersion

    def list_for_asset(self, asset_kind: str, asset_id: int) -> list[models.AssetVersion]:
        stmt = select(self.model).where(
            self.model.asset_kind == asset_kind,
            self.model.asset_id == asset_id,
            self.model.account_id == self.account_id,
        ).order_by(self.model.version_no)
        return list(self.db.execute(stmt).scalars().all())


class ValidationReportDAL(BaseDAL[models.ValidationReport]):
    model = models.ValidationReport


class WeeklyReportDAL(BaseDAL[models.WeeklyReport]):
    model = models.WeeklyReport


class PeriodReportDAL(BaseDAL[models.PeriodReport]):
    model = models.PeriodReport


class UsageDAL(BaseDAL[models.Usage]):
    model = models.Usage

    def get_or_create_today(self) -> models.Usage:
        today = dt.date.today()
        stmt = select(self.model).where(
            self.model.account_id == self.account_id,
            self.model.date == today,
        )
        row = self.db.execute(stmt).scalar_one_or_none()
        if row is None:
            row = self.model(account_id=self.account_id, date=today, runs_count=0)
            self.db.add(row)
            self.db.flush()
        return row

    def today_count(self) -> int:
        today = dt.date.today()
        stmt = select(func.coalesce(func.sum(self.model.runs_count), 0)).where(
            self.model.account_id == self.account_id,
            self.model.date == today,
        )
        return int(self.db.execute(stmt).scalar() or 0)

    def increment(self) -> int:
        row = self.get_or_create_today()
        row.runs_count += 1
        self.db.flush()
        return row.runs_count


class OneTimeCodeDAL(BaseDAL[models.OneTimeCode]):
    model = models.OneTimeCode

    def latest_unused(self, code_type: str) -> Optional[models.OneTimeCode]:
        """Most recent unused code of a given type for this account."""
        now = dt.datetime.utcnow()
        stmt = (
            select(self.model)
            .where(
                self.model.account_id == self.account_id,
                self.model.type == code_type,
                self.model.used == False,  # noqa: E712
                self.model.expires_at > now,
            )
            .order_by(self.model.id.desc())
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def invalidate_all(self, code_type: str) -> None:
        """Mark all existing codes of this type as used (so only the newest is valid)."""
        now = dt.datetime.utcnow()
        stmt = (
            select(self.model)
            .where(
                self.model.account_id == self.account_id,
                self.model.type == code_type,
                self.model.used == False,  # noqa: E712
            )
        )
        for row in self.db.execute(stmt).scalars().all():
            row.used = True
        self.db.flush()


# ── Factory ──────────────────────────────────────────────────────
class DAL:
    """One-stop access point. Always created with account_id."""

    def __init__(self, db: Session, account_id: int):
        self.db = db
        self.account_id = account_id
        self.profiles = ProfileDAL(db, account_id)
        self.brand_files = BrandFileDAL(db, account_id)
        self.runs = RunDAL(db, account_id)
        self.run_events = RunEventDAL(db, account_id)
        self.content_plans = ContentPlanDAL(db, account_id)
        self.posts = PostDAL(db, account_id)
        self.reply_drafts = ReplyDraftDAL(db, account_id)
        self.campaigns = CampaignDAL(db, account_id)
        self.campaign_assets = CampaignAssetDAL(db, account_id)
        self.asset_versions = AssetVersionDAL(db, account_id)
        self.validation_reports = ValidationReportDAL(db, account_id)
        self.weekly_reports = WeeklyReportDAL(db, account_id)
        self.period_reports = PeriodReportDAL(db, account_id)
        self.usage = UsageDAL(db, account_id)
        self.one_time_codes = OneTimeCodeDAL(db, account_id)


def get_dal(db: Session, account_id: int) -> DAL:
    return DAL(db, account_id)
