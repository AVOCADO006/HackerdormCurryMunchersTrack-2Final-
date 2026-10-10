"""Auth endpoint tests — signup, verify-email, login, 2FA, logout,
forgot/reset password, change password, 2FA toggle, delete account."""
from __future__ import annotations

import json
from datetime import datetime, timedelta

from app.db.session import SessionLocal
from app.db.dal import AccountDAL, DAL


# ── Signup ────────────────────────────────────────────────────────
class TestSignup:
    def test_signup_creates_account_and_empty_profile(self, client):
        resp = client.post("/api/auth/signup", json={
            "email": "newuser@test.com",
            "password": "password123",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "newuser@test.com"
        assert data["email_verified"] is True  # AUTO_VERIFY_EMAIL=true in test env

        # Profile should exist with empty values
        db = SessionLocal()
        try:
            account = AccountDAL(db).get_by_email("newuser@test.com")
            assert account is not None
            profile = DAL(db, account.id).profiles.get_for_account()
            assert profile is not None
            assert profile.business_name == ""
            assert profile.platforms == []
        finally:
            db.close()

    def test_signup_duplicate_email(self, client):
        client.post("/api/auth/signup", json={
            "email": "dup@test.com",
            "password": "password123",
        })
        resp = client.post("/api/auth/signup", json={
            "email": "dup@test.com",
            "password": "password123",
        })
        assert resp.status_code == 409
        body = resp.json()
        assert "already exists" in body["error"]["message"]

    def test_signup_short_password(self, client):
        resp = client.post("/api/auth/signup", json={
            "email": "short@test.com",
            "password": "short",
        })
        assert resp.status_code == 422  # Pydantic validation


# ── Login ─────────────────────────────────────────────────────────
class TestLogin:
    def test_login_success(self, client):
        client.post("/api/auth/signup", json={
            "email": "login@test.com",
            "password": "password123",
        })
        resp = client.post("/api/auth/login", json={
            "email": "login@test.com",
            "password": "password123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["email"] == "login@test.com"
        assert data["email_verified"] is True
        assert data["two_factor_enabled"] is False

    def test_login_wrong_password(self, client):
        client.post("/api/auth/signup", json={
            "email": "wrong@test.com",
            "password": "password123",
        })
        resp = client.post("/api/auth/login", json={
            "email": "wrong@test.com",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401
        body = resp.json()
        assert "Invalid" in body["error"]["message"]

    def test_login_nonexistent_email(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "nobody@test.com",
            "password": "password123",
        })
        assert resp.status_code == 401
        # Must not reveal whether email exists — same message as wrong password
        body = resp.json()
        assert "Invalid" in body["error"]["message"]

    def test_login_sets_cookie(self, client):
        client.post("/api/auth/signup", json={
            "email": "cookie@test.com",
            "password": "password123",
        })
        resp = client.post("/api/auth/login", json={
            "email": "cookie@test.com",
            "password": "password123",
        })
        # Cookie should be set (TestClient stores it)
        assert "session" in resp.cookies


# ── Logout ────────────────────────────────────────────────────────
class TestLogout:
    def test_logout_clears_cookie(self, client):
        client.post("/api/auth/signup", json={
            "email": "logout@test.com",
            "password": "password123",
        })
        client.post("/api/auth/login", json={
            "email": "logout@test.com",
            "password": "password123",
        })
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 200


# ── 2FA ───────────────────────────────────────────────────────────
class Test2FA:
    def test_enable_2fa_then_login_requires_code(self, client):
        # Signup + login
        client.post("/api/auth/signup", json={
            "email": "2fa@test.com",
            "password": "password123",
        })
        login_resp = client.post("/api/auth/login", json={
            "email": "2fa@test.com",
            "password": "password123",
        })
        token = login_resp.json()["token"]

        # Enable 2FA
        resp = client.post("/api/auth/2fa", json={"enable": True},
                           headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["two_factor_enabled"] is True

        # Login again — should require 2FA
        login2 = client.post("/api/auth/login", json={
            "email": "2fa@test.com",
            "password": "password123",
        })
        assert login2.status_code == 200
        assert login2.json().get("requires_2fa") is True

    def test_verify_2fa_with_fixed_code(self, client):
        client.post("/api/auth/signup", json={
            "email": "2fa2@test.com",
            "password": "password123",
        })
        login_resp = client.post("/api/auth/login", json={
            "email": "2fa2@test.com",
            "password": "password123",
        })
        token = login_resp.json()["token"]
        client.post("/api/auth/2fa", json={"enable": True},
                     headers={"Authorization": f"Bearer {token}"})

        # Login → requires 2FA
        client.post("/api/auth/login", json={
            "email": "2fa2@test.com",
            "password": "password123",
        })

        # Verify with fixed code (FIXED_2FA_CODE=123456 in test env)
        resp = client.post("/api/auth/verify-2fa", json={
            "email": "2fa2@test.com",
            "code": "123456",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data

    def test_verify_2fa_wrong_code(self, client):
        client.post("/api/auth/signup", json={
            "email": "2fa3@test.com",
            "password": "password123",
        })
        login_resp = client.post("/api/auth/login", json={
            "email": "2fa3@test.com",
            "password": "password123",
        })
        token = login_resp.json()["token"]
        client.post("/api/auth/2fa", json={"enable": True},
                     headers={"Authorization": f"Bearer {token}"})
        client.post("/api/auth/login", json={
            "email": "2fa3@test.com",
            "password": "password123",
        })

        resp = client.post("/api/auth/verify-2fa", json={
            "email": "2fa3@test.com",
            "code": "000000",
        })
        assert resp.status_code == 401

    def test_disable_2fa(self, client):
        client.post("/api/auth/signup", json={
            "email": "2fa4@test.com",
            "password": "password123",
        })
        login_resp = client.post("/api/auth/login", json={
            "email": "2fa4@test.com",
            "password": "password123",
        })
        token = login_resp.json()["token"]
        client.post("/api/auth/2fa", json={"enable": True},
                     headers={"Authorization": f"Bearer {token}"})
        resp = client.post("/api/auth/2fa", json={"enable": False},
                           headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["two_factor_enabled"] is False


# ── Forgot + Reset Password ───────────────────────────────────────
class TestPasswordReset:
    def test_forgot_password_always_success(self, client):
        # Nonexistent email should still return success
        resp = client.post("/api/auth/forgot-password", json={
            "email": "nonexistent@test.com",
        })
        assert resp.status_code == 200
        assert "reset code has been sent" in resp.json()["message"]

    def test_reset_password_with_db_code(self, client):
        # Signup
        client.post("/api/auth/signup", json={
            "email": "reset@test.com",
            "password": "password123",
        })

        # Request reset
        client.post("/api/auth/forgot-password", json={
            "email": "reset@test.com",
        })

        # Get the code from the DB
        db = SessionLocal()
        try:
            from app.db.dal import DAL
            account = AccountDAL(db).get_by_email("reset@test.com")
            otc = DAL(db, account.id).one_time_codes.latest_unused("reset_password")
            assert otc is not None
            code = otc.code
        finally:
            db.close()

        # Reset password
        resp = client.post("/api/auth/reset-password", json={
            "email": "reset@test.com",
            "code": code,
            "new_password": "newpassword456",
        })
        assert resp.status_code == 200

        # Login with new password
        login = client.post("/api/auth/login", json={
            "email": "reset@test.com",
            "password": "newpassword456",
        })
        assert login.status_code == 200

    def test_reset_password_wrong_code(self, client):
        client.post("/api/auth/signup", json={
            "email": "reset2@test.com",
            "password": "password123",
        })
        client.post("/api/auth/forgot-password", json={
            "email": "reset2@test.com",
        })
        resp = client.post("/api/auth/reset-password", json={
            "email": "reset2@test.com",
            "code": "000000",
            "new_password": "newpassword456",
        })
        assert resp.status_code == 400


# ── Change Password ───────────────────────────────────────────────
class TestChangePassword:
    def test_change_password(self, client):
        client.post("/api/auth/signup", json={
            "email": "change@test.com",
            "password": "password123",
        })
        login = client.post("/api/auth/login", json={
            "email": "change@test.com",
            "password": "password123",
        })
        token = login.json()["token"]

        resp = client.post("/api/auth/change-password", json={
            "current_password": "password123",
            "new_password": "newpassword456",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

        # Old password should fail
        old_login = client.post("/api/auth/login", json={
            "email": "change@test.com",
            "password": "password123",
        })
        assert old_login.status_code == 401

        # New password should work
        new_login = client.post("/api/auth/login", json={
            "email": "change@test.com",
            "password": "newpassword456",
        })
        assert new_login.status_code == 200

    def test_change_password_wrong_current(self, client):
        client.post("/api/auth/signup", json={
            "email": "change2@test.com",
            "password": "password123",
        })
        login = client.post("/api/auth/login", json={
            "email": "change2@test.com",
            "password": "password123",
        })
        token = login.json()["token"]

        resp = client.post("/api/auth/change-password", json={
            "current_password": "wrongpassword",
            "new_password": "newpassword456",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401


# ── Email Verification (non-auto-verify path) ───────────────────
class TestEmailVerification:
    def test_verify_email_with_db_code(self, client, monkeypatch):
        # Temporarily disable auto-verify so we can test the verification flow
        from app.config import get_settings, Settings
        settings = get_settings()
        monkeypatch.setattr(settings, "AUTO_VERIFY_EMAIL", False)

        # Signup — email NOT auto-verified
        resp = client.post("/api/auth/signup", json={
            "email": "verify@test.com",
            "password": "password123",
        })
        assert resp.status_code == 201
        assert resp.json()["email_verified"] is False

        # Login should fail — email not verified
        login = client.post("/api/auth/login", json={
            "email": "verify@test.com",
            "password": "password123",
        })
        assert login.status_code == 403

        # Get the code from DB
        db = SessionLocal()
        try:
            account = AccountDAL(db).get_by_email("verify@test.com")
            otc = DAL(db, account.id).one_time_codes.latest_unused("verify_email")
            assert otc is not None
            code = otc.code
        finally:
            db.close()

        # Verify email
        resp = client.post("/api/auth/verify-email", json={
            "email": "verify@test.com",
            "code": code,
        })
        assert resp.status_code == 200

        # Login should now work
        login = client.post("/api/auth/login", json={
            "email": "verify@test.com",
            "password": "password123",
        })
        assert login.status_code == 200

    def test_verify_email_wrong_code(self, client, monkeypatch):
        from app.config import get_settings
        settings = get_settings()
        monkeypatch.setattr(settings, "AUTO_VERIFY_EMAIL", False)

        client.post("/api/auth/signup", json={
            "email": "verify2@test.com",
            "password": "password123",
        })
        resp = client.post("/api/auth/verify-email", json={
            "email": "verify2@test.com",
            "code": "000000",
        })
        assert resp.status_code == 400


# ── Delete Account ─────────────────────────────────────────────────
class TestDeleteAccount:
    def test_delete_account(self, client):
        client.post("/api/auth/signup", json={
            "email": "delete@test.com",
            "password": "password123",
        })
        login = client.post("/api/auth/login", json={
            "email": "delete@test.com",
            "password": "password123",
        })
        token = login.json()["token"]

        resp = client.delete("/api/auth/account",
                              headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

        # Account should be gone
        db = SessionLocal()
        try:
            account = AccountDAL(db).get_by_email("delete@test.com")
            assert account is None
        finally:
            db.close()

        # Token should no longer work
        resp = client.delete("/api/auth/account",
                              headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401


# ── Token via cookie vs header ────────────────────────────────────
class TestTokenSources:
    def test_protected_endpoint_with_header(self, client):
        client.post("/api/auth/signup", json={
            "email": "hdr@test.com",
            "password": "password123",
        })
        login = client.post("/api/auth/login", json={
            "email": "hdr@test.com",
            "password": "password123",
        })
        token = login.json()["token"]

        # Use header
        resp = client.post("/api/auth/2fa", json={"enable": True},
                           headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_protected_endpoint_with_cookie(self, client):
        client.post("/api/auth/signup", json={
            "email": "cook@test.com",
            "password": "password123",
        })
        client.post("/api/auth/login", json={
            "email": "cook@test.com",
            "password": "password123",
        })

        # Cookie is set automatically by TestClient; no Authorization header
        resp = client.post("/api/auth/2fa", json={"enable": True})
        assert resp.status_code == 200

    def test_protected_endpoint_no_token(self, client):
        resp = client.post("/api/auth/2fa", json={"enable": True})
        assert resp.status_code == 401
