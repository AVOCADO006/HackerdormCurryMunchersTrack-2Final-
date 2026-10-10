"""One-time code management — generate, store, verify with expiry + max attempts.

Code types: verify_email | two_factor | reset_password
"""
from __future__ import annotations

import datetime as dt
import logging
import random
import string
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.dal import DAL
from app.db.models import OneTimeCode

logger = logging.getLogger(__name__)
_settings = get_settings()


def generate_code() -> str:
    """6-digit numeric code."""
    return "".join(random.choices(string.digits, k=6))


def create_code(db: Session, account_id: int, code_type: str) -> str:
    """Invalidate previous codes of this type, then create a new one."""
    dal = DAL(db, account_id)
    dal.one_time_codes.invalidate_all(code_type)

    code = generate_code()
    now = dt.datetime.utcnow()
    dal.one_time_codes.create(
        code=code,
        type=code_type,
        expires_at=now + dt.timedelta(minutes=_settings.CODE_EXPIRY_MINUTES),
    )
    db.flush()
    return code


def verify_code(
    db: Session, account_id: int, code_type: str, submitted_code: str
) -> Tuple[bool, str]:
    """Verify a one-time code.

    Returns (success, message).
    - Increments attempts on mismatch.
    - Returns failure if expired, already used, or max attempts exceeded.
    """
    # Demo mode: FIXED_2FA_CODE for two_factor type
    if (
        code_type == "two_factor"
        and _settings.fixed_2fa_active
        and submitted_code == _settings.FIXED_2FA_CODE
    ):
        # Mark any existing codes as used so they can't be replayed
        dal = DAL(db, account_id)
        dal.one_time_codes.invalidate_all(code_type)
        db.flush()
        return True, "Verified (fixed code)."

    dal = DAL(db, account_id)
    record = dal.one_time_codes.latest_unused(code_type)

    if record is None:
        return False, "No valid code found. Please request a new one."

    # Check max attempts
    if record.attempts >= _settings.MAX_CODE_ATTEMPTS:
        record.used = True
        db.flush()
        return False, "Maximum attempts exceeded. Please request a new code."

    # Check the code
    if record.code == submitted_code:
        record.used = True
        db.flush()
        return True, "Verified."
    else:
        record.attempts += 1
        db.flush()
        remaining = _settings.MAX_CODE_ATTEMPTS - record.attempts
        if remaining > 0:
            return False, f"Invalid code. {remaining} attempt(s) remaining."
        else:
            record.used = True
            db.flush()
            return False, "Maximum attempts exceeded. Please request a new code."
