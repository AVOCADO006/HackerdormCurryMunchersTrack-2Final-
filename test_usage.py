"""Usage limit tests — DAILY_RUN_LIMIT enforcement and demo account bypass."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.auth.dependencies import hash_password
from app.db.dal import AccountDAL
from app.db.models import Account
from app.db.session import SessionLocal
from app.services.usage import check_and_increment


class TestUsageLimit:
    def test_normal_account_blocked_after_limit(self, db):
        """The 4th run of a normal account should be blocked with 429."""
        acct_dal = AccountDAL(db)
        account = acct_dal.create(
            email="limit@test.com",
            password_hash=hash_password("password123"),
            email_verified=True,
            is_demo=False,
        )
        db.commit()

        # First 3 runs should succeed
        for i in range(3):
            check_and_increment(db, account)
            db.commit()

        # 4th run should raise 429
        with pytest.raises(HTTPException) as exc_info:
            check_and_increment(db, account)

        assert exc_info.value.status_code == 429
        detail = exc_info.value.detail
        assert "error" in detail
        assert "Daily run limit reached" in detail["error"]["message"]
        assert "try again tomorrow" in detail["error"]["message"]

    def test_demo_account_unlimited(self, db):
        """Demo accounts should never be blocked."""
        acct_dal = AccountDAL(db)
        account = acct_dal.create(
            email="demo@test.com",
            password_hash=hash_password("password123"),
            email_verified=True,
            is_demo=True,
        )
        db.commit()

        # Run 10 times — should never raise
        for i in range(10):
            check_and_increment(db, account)
            db.commit()

    def test_limit_message_exactly_as_specified(self, db):
        acct_dal = AccountDAL(db)
        account = acct_dal.create(
            email="msg@test.com",
            password_hash=hash_password("password123"),
            email_verified=True,
            is_demo=False,
        )
        db.commit()

        # Exhaust the limit
        for _ in range(3):
            check_and_increment(db, account)
            db.commit()

        with pytest.raises(HTTPException) as exc_info:
            check_and_increment(db, account)

        assert exc_info.value.status_code == 429
        assert (
            exc_info.value.detail["error"]["message"]
            == "Daily run limit reached, try again tomorrow"
        )
