"""Usage service — enforces DAILY_RUN_LIMIT per UTC day.

Demo accounts skip the check entirely.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.dal import DAL
from app.db.models import Account
from app.api.errors import APIError

_settings = get_settings()


def check_and_increment(db: Session, account: Account) -> None:
    """Check the daily run limit and increment the counter.

    Demo accounts skip the check entirely.
    Raises HTTP 429 if the limit is reached.
    """
    if account.is_demo:
        return

    dal = DAL(db, account.id)
    count = dal.usage.today_count()

    if count >= _settings.DAILY_RUN_LIMIT:
        raise APIError(
            status_code=429,
            code="RATE_LIMITED",
            message="Daily run limit reached, try again tomorrow",
        )

    dal.usage.increment()
    db.commit()
