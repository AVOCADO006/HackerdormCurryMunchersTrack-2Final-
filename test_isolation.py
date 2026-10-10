"""Isolation tests — prove account A cannot touch account B's data.

These tests exercise the DAL directly, showing that every query
filters by account_id and cross-account access returns None / False.
"""
from __future__ import annotations

import datetime as dt

import pytest

from app.db.dal import DAL, AccountDAL
from app.auth.dependencies import hash_password


# ── Profile ──────────────────────────────────────────────────────
class TestProfileIsolation:
    def test_a_creates_b_cannot_read(self, db, account_a, account_b):
        dal_a = DAL(db, account_a)
        dal_a.profiles.create(
            business_name="Kak Min's Kuih Corner",
            business_type="home-based food",
            products=["Kuih", "Party Boxes"],
            audience="Corporate clients, party hosts",
            tone="Warm, cheeky, Manglish",
            platforms=["instagram", "linkedin", "x", "threads"],
            location="Kuala Lumpur, Malaysia",
            videos_per_week=3,
            brand_notes="Past corporate catering orders from KL companies",
        )
        db.commit()

        dal_b = DAL(db, account_b)
        assert dal_b.profiles.get_for_account() is None
        # B also cannot read A's profile by guessing the ID
        assert dal_b.profiles.get(1) is None

    def test_b_cannot_update_a_profile(self, db, account_a, account_b):
        dal_a = DAL(db, account_a)
        p = dal_a.profiles.create(
            business_name="Cafe A",
            business_type="cafe",
            products=["Coffee"],
            audience="Locals",
            tone="Friendly",
            platforms=["instagram"],
            location="KL",
            videos_per_week=2,
            brand_notes="",
        )
        db.commit()
        profile_id = p.id

        dal_b = DAL(db, account_b)
        result = dal_b.profiles.update(profile_id, business_name="Hacked!")
        assert result is None
        # A's profile is unchanged
        db.refresh(p)
        assert p.business_name == "Cafe A"

    def test_b_cannot_delete_a_profile(self, db, account_a, account_b):
        dal_a = DAL(db, account_a)
        p = dal_a.profiles.create(
            business_name="Cafe A",
            business_type="cafe",
            products=["Coffee"],
            audience="Locals",
            tone="Friendly",
            platforms=["instagram"],
            location="KL",
            videos_per_week=2,
            brand_notes="",
        )
        db.commit()
        profile_id = p.id

        dal_b = DAL(db, account_b)
        assert dal_b.profiles.delete(profile_id) is False
        # Profile still exists
        assert dal_a.profiles.get(profile_id) is not None


# ── Run + RunEvent ───────────────────────────────────────────────
class TestRunIsolation:
    def test_b_cannot_read_a_run(self, db, account_a, account_b):
        dal_a = DAL(db, account_a)
        r = dal_a.runs.create(
            mode="weekly",
            user_prompt="Plan this week's posts",
            goal="Engagement",
        )
        db.commit()

        dal_b = DAL(db, account_b)
        assert dal_b.runs.get(r.id) is None
        assert dal_b.runs.list() == []

    def test_b_cannot_cancel_a_run(self, db, account_a, account_b):
        dal_a = DAL(db, account_a)
        r = dal_a.runs.create(
            mode="both",
            user_prompt="Win corporate catering on LinkedIn",
            goal="Corporate orders",
        )
        db.commit()

        dal_b = DAL(db, account_b)
        assert dal_b.runs.update(r.id, status="cancelled") is None
        db.refresh(r)
        assert r.status == "queued"


# ── ContentPlan + Post + ReplyDraft ──────────────────────────────
class TestContentIsolation:
    def _setup_plan(self, db, account_id):
        dal = DAL(db, account_id)
        run = dal.runs.create(mode="weekly", user_prompt="test", goal="test")
        plan = dal.content_plans.create(
            run_id=run.id,
            week_start=dt.date(2025, 1, 1),
            strategy={"focus": "awareness"},
            status="draft",
        )
        post = dal.posts.create(
            plan_id=plan.id,
            date=dt.date(2025, 1, 6),
            platform="instagram",
            format="reel",
            pillar="Behind the Scenes",
            caption="Morning kuih prep!",
            hook="Ever wondered how kuih is made?",
            script="Start with rice flour...",
            shot_list=["Wide shot of kitchen", "Close-up of steaming"],
            hashtags=["#kuih", "#malaysianfood"],
            design_brief="Warm tones, natural light",
            on_screen_text="Fresh Daily",
        )
        reply = dal.reply_drafts.create(
            plan_id=plan.id,
            type="question",
            question="Do you deliver?",
            reply="Yes! We deliver across KL. DM us!",
        )
        db.commit()
        return run.id, plan.id, post.id, reply.id

    def test_b_cannot_see_a_posts(self, db, account_a, account_b):
        run_id, plan_id, post_id, reply_id = self._setup_plan(db, account_a)

        dal_b = DAL(db, account_b)
        assert dal_b.posts.get(post_id) is None
        assert dal_b.posts.list_for_plan(plan_id) == []
        assert dal_b.reply_drafts.get(reply_id) is None
        assert dal_b.reply_drafts.list_for_plan(plan_id) == []
        assert dal_b.content_plans.get(plan_id) is None

    def test_b_cannot_edit_a_post(self, db, account_a, account_b):
        _, plan_id, post_id, _ = self._setup_plan(db, account_a)

        dal_b = DAL(db, account_b)
        assert dal_b.posts.update(post_id, caption="Hacked caption") is None

        dal_a = DAL(db, account_a)
        p = dal_a.posts.get(post_id)
        assert p.caption == "Morning kuih prep!"

    def test_b_cannot_delete_a_reply(self, db, account_a, account_b):
        _, plan_id, _, reply_id = self._setup_plan(db, account_a)

        dal_b = DAL(db, account_b)
        assert dal_b.reply_drafts.delete(reply_id) is False

        dal_a = DAL(db, account_a)
        assert dal_a.reply_drafts.get(reply_id) is not None


# ── Campaign + CampaignAsset + AssetVersion ─────────────────────
class TestCampaignIsolation:
    def _setup_campaign(self, db, account_id):
        dal = DAL(db, account_id)
        run = dal.runs.create(mode="campaign", user_prompt="LinkedIn campaign", goal="leads")
        camp = dal.campaigns.create(
            run_id=run.id,
            template_inputs={"budget": 300, "weeks": 4},
            phases=[{"name": "Phase 1", "weeks": 1}],
            budget_plan={"type": "boost_test", "allocation_notes": "RM150 boost"},
            calendar=[{"week": 1, "day": "Mon", "asset_ref": "carousel"}],
            status="draft",
        )
        asset = dal.campaign_assets.create(
            campaign_id=camp.id,
            type="carousel",
            content={"slides": [{"title": "Who We Are", "body": "Kuih for offices"}]},
            status="draft",
        )
        ver = dal.asset_versions.create(
            asset_kind="campaign_asset",
            asset_id=asset.id,
            version_no=1,
            content={"slides": []},
            source="agent",
        )
        db.commit()
        return camp.id, asset.id, ver.id

    def test_b_cannot_see_a_campaign(self, db, account_a, account_b):
        camp_id, asset_id, ver_id = self._setup_campaign(db, account_a)

        dal_b = DAL(db, account_b)
        assert dal_b.campaigns.get(camp_id) is None
        assert dal_b.campaign_assets.get(asset_id) is None
        assert dal_b.asset_versions.get(ver_id) is None

    def test_b_cannot_delete_a_asset(self, db, account_a, account_b):
        camp_id, asset_id, _ = self._setup_campaign(db, account_a)

        dal_b = DAL(db, account_b)
        assert dal_b.campaign_assets.delete(asset_id) is False
        assert dal_b.campaigns.delete(camp_id) is False


# ── WeeklyReport + PeriodReport + ValidationReport ──────────────
class TestReportIsolation:
    def test_b_cannot_read_a_reports(self, db, account_a, account_b):
        dal_a = DAL(db, account_a)
        run = dal_a.runs.create(mode="weekly", user_prompt="test", goal="test")
        wr = dal_a.weekly_reports.create(
            week_start=dt.date(2025, 1, 6),
            post_metrics={"impressions": 1200},
            orders=[{"item": "Kuih Box", "qty": 5, "rm": 150}],
            revenue_rm=150.0,
            costs={"boost": 50},
            computed_metrics={"ctr": 0.03},
            analysis={"insight": "Reels outperformed"},
        )
        pr = dal_a.period_reports.create(
            type="monthly",
            range_start=dt.date(2025, 1, 1),
            range_end=dt.date(2025, 1, 31),
            content={"summary": "January was good"},
        )
        vr = dal_a.validation_reports.create(
            run_id=run.id,
            checks=[{"check": "caption_length", "passed": True}],
            summary="All checks passed",
        )
        db.commit()

        dal_b = DAL(db, account_b)
        assert dal_b.weekly_reports.get(wr.id) is None
        assert dal_b.period_reports.get(pr.id) is None
        assert dal_b.validation_reports.get(vr.id) is None

    def test_b_cannot_delete_a_report(self, db, account_a, account_b):
        dal_a = DAL(db, account_a)
        wr = dal_a.weekly_reports.create(
            week_start=dt.date(2025, 1, 6),
            post_metrics={},
            orders=[],
            revenue_rm=0.0,
            costs={},
            computed_metrics={},
            analysis={},
        )
        db.commit()

        dal_b = DAL(db, account_b)
        assert dal_b.weekly_reports.delete(wr.id) is False


# ── Usage counter ────────────────────────────────────────────────
class TestUsageIsolation:
    def test_usage_is_per_account(self, db, account_a, account_b):
        dal_a = DAL(db, account_a)
        dal_b = DAL(db, account_b)

        # A runs 3 times
        for _ in range(3):
            dal_a.usage.increment()
        db.commit()

        assert dal_a.usage.today_count() == 3
        assert dal_b.usage.today_count() == 0


# ── Account deletion cascades ────────────────────────────────────
class TestCascade:
    def test_deleting_account_cascades(self, db, account_a):
        dal_a = DAL(db, account_a)
        run = dal_a.runs.create(mode="weekly", user_prompt="x", goal="x")
        plan = dal_a.content_plans.create(
            run_id=run.id, week_start=dt.date(2025, 1, 1), strategy={}, status="draft"
        )
        dal_a.posts.create(
            plan_id=plan.id,
            platform="instagram",
            format="reel",
            pillar="test",
            caption="c",
            hook="h",
            script="s",
            shot_list=[],
            hashtags=[],
            design_brief="",
            on_screen_text="",
        )
        db.commit()
        assert dal_a.runs.list() != []

        # Delete the account
        AccountDAL(db).delete(account_a)
        db.commit()

        # All scoped rows are gone
        dal_check = DAL(db, account_a)
        assert dal_check.runs.list() == []
        assert dal_check.posts.list() == []
