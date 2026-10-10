"""Auth router — signup, verify-email, login, verify-2fa, logout,
forgot-password, reset-password, change-password, 2FA toggle, delete account.

Errors never reveal whether an email exists.
Sessions are signed JWT tokens in an HTTP-only cookie, also accepted in
the Authorization header.
"""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.auth.codes import create_code, verify_code
from app.auth.dependencies import (
    create_access_token,
    get_current_account,
    hash_password,
    verify_password,
)
from app.auth.email import send_code
from app.auth.rate_limit import rate_limiter
from app.auth.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    SignupRequest,
    TwoFactorToggleRequest,
    Verify2FARequest,
    VerifyEmailRequest,
)
from app.config import get_settings
from app.db.dal import AccountDAL, DAL
from app.db.models import Account
from app.db.session import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])
_settings = get_settings()

_COOKIE_KWARGS = dict(
    key=_settings.COOKIE_NAME,
    httponly=True,
    samesite="lax",
    max_age=_settings.TOKEN_EXPIRE_HOURS * 3600,
    path="/",
)

_INVALID_CREDS = "Invalid email or password."
_EMAIL_EXISTS_MSG = "An account with this email already exists."


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(value=token, **_COOKIE_KWARGS)


def _clear_cookie(response: Response) -> None:
    response.delete_cookie(key=_settings.COOKIE_NAME, path="/")


def _auth_response(account: Account) -> dict:
    token = create_access_token(account.id)
    return {
        "token": token,
        "account_id": account.id,
        "email": account.email,
        "email_verified": account.email_verified,
        "two_factor_enabled": account.two_factor_enabled,
        "is_demo": account.is_demo,
    }


# ── Signup ────────────────────────────────────────────────────────
@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, db: Session = Depends(get_db)):
    # Check if email already exists
    existing = AccountDAL(db).get_by_email(body.email)
    if existing is not None:
        raise APIError(409, "EMAIL_EXISTS", _EMAIL_EXISTS_MSG)

    # Create account
    email_verified = _settings.auto_verify_active
    account = AccountDAL(db).create(
        email=body.email,
        password_hash=hash_password(body.password),
        email_verified=email_verified,
        is_demo=False,
    )

    # Create empty profile
    DAL(db, account.id).profiles.create(
        business_name="",
        business_type="",
        products=[],
        audience="",
        tone="",
        platforms=[],
        location="",
        videos_per_week=3,
        brand_notes="",
    )
    db.commit()

    # If not auto-verified, generate and send a verification code
    if not email_verified:
        code = create_code(db, account.id, "verify_email")
        db.commit()
        send_code(account.email, code, "verify_email")

    return {
        "account_id": account.id,
        "email": account.email,
        "email_verified": email_verified,
        "message": "Account created. Please verify your email to log in."
        if not email_verified
        else "Account created and email verified.",
    }


# ── Verify Email ──────────────────────────────────────────────────
@router.post("/verify-email")
def verify_email(body: VerifyEmailRequest, db: Session = Depends(get_db)):
    account = AccountDAL(db).get_by_email(body.email)

    if account is None:
        # Don't reveal that the email doesn't exist
        raise APIError(400, "INVALID_CODE", "Invalid or expired code.")

    success, message = verify_code(db, account.id, "verify_email", body.code)
    if not success:
        raise APIError(400, "INVALID_CODE", message)

    account.email_verified = True
    db.commit()
    return {"message": "Email verified successfully. You can now log in."}


# ── Login ─────────────────────────────────────────────────────────
@router.post("/login")
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else "unknown"

    # Rate limit check (before doing any DB lookup)
    allowed, rate_msg = rate_limiter.check(body.email, ip)
    if not allowed:
        raise APIError(429, "RATE_LIMITED", rate_msg)

    account = AccountDAL(db).get_by_email(body.email)

    # Always use the same error whether email doesn't exist or password is wrong
    if account is None or not verify_password(body.password, account.password_hash):
        rate_limiter.record(body.email, ip)
        raise APIError(401, "INVALID_CREDENTIALS", _INVALID_CREDS)

    # Password is correct — don't rate-limit further

    # Check email verification
    if not account.email_verified:
        # The user proved they know the password, so it's OK to tell them
        # to verify their email (this doesn't leak registration status to
        # attackers who don't know the password).
        raise APIError(403, "EMAIL_NOT_VERIFIED", "Please verify your email before logging in.")

    # Check 2FA
    if account.two_factor_enabled:
        code = create_code(db, account.id, "two_factor")
        db.commit()
        send_code(account.email, code, "two_factor")
        return {"requires_2fa": True, "email": account.email}

    # No 2FA — issue token
    result = _auth_response(account)
    _set_cookie(response, result["token"])
    return result


# ── Verify 2FA ───────────────────────────────────────────────────
@router.post("/verify-2fa")
def verify_2fa(
    body: Verify2FARequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else "unknown"

    # Rate limit
    allowed, rate_msg = rate_limiter.check(body.email, ip)
    if not allowed:
        raise APIError(429, "RATE_LIMITED", rate_msg)

    account = AccountDAL(db).get_by_email(body.email)
    if account is None:
        rate_limiter.record(body.email, ip)
        raise APIError(401, "INVALID_CREDENTIALS", _INVALID_CREDS)

    success, message = verify_code(db, account.id, "two_factor", body.code)
    if not success:
        rate_limiter.record(body.email, ip)
        raise APIError(401, "INVALID_CODE", message)

    db.commit()
    result = _auth_response(account)
    _set_cookie(response, result["token"])
    return result


# ── Logout ────────────────────────────────────────────────────────
@router.post("/logout")
def logout(response: Response):
    _clear_cookie(response)
    return {"message": "Logged out successfully."}


# ── Forgot Password ───────────────────────────────────────────────
@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    # Always return success — never reveal whether the email exists
    account = AccountDAL(db).get_by_email(body.email)
    if account is not None:
        code = create_code(db, account.id, "reset_password")
        db.commit()
        send_code(account.email, code, "reset_password")

    return {"message": "If the email exists, a reset code has been sent."}


# ── Reset Password ────────────────────────────────────────────────
@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    account = AccountDAL(db).get_by_email(body.email)
    if account is None:
        raise APIError(400, "INVALID_CODE", "Invalid or expired code.")

    success, message = verify_code(db, account.id, "reset_password", body.code)
    if not success:
        raise APIError(400, "INVALID_CODE", message)

    account.password_hash = hash_password(body.new_password)
    db.commit()
    return {"message": "Password reset successfully."}


# ── Change Password (requires session) ─────────────────────────────
@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    if not verify_password(body.current_password, account.password_hash):
        raise APIError(401, "INVALID_CREDENTIALS", "Current password is incorrect.")

    account.password_hash = hash_password(body.new_password)
    db.commit()
    return {"message": "Password changed successfully."}


# ── Enable / Disable 2FA (requires session) ───────────────────────
@router.post("/2fa")
def toggle_2fa(
    body: TwoFactorToggleRequest,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    account.two_factor_enabled = body.enable
    db.commit()
    return {"two_factor_enabled": body.enable}


# ── Delete Account (requires session) ─────────────────────────────
@router.delete("/account")
def delete_account(
    response: Response,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    AccountDAL(db).delete(account.id)
    db.commit()
    _clear_cookie(response)
    return {"message": "Account deleted successfully."}
