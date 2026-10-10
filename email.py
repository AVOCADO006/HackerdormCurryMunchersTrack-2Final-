"""Email sender — uses SMTP if configured, otherwise prints to server log in dev."""
from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import get_settings

logger = logging.getLogger(__name__)
_settings = get_settings()

EMAIL_TEMPLATES = {
    "verify_email": {
        "subject": "Verify your email — AI Social Media Manager",
        "body": (
            "Welcome to AI Social Media Manager!\n\n"
            "Your verification code is: {code}\n\n"
            "This code expires in {expiry} minutes.\n"
        ),
    },
    "two_factor": {
        "subject": "Your 2FA code — AI Social Media Manager",
        "body": (
            "Your two-factor authentication code is: {code}\n\n"
            "This code expires in {expiry} minutes.\n"
        ),
    },
    "reset_password": {
        "subject": "Password reset — AI Social Media Manager",
        "body": (
            "We received a request to reset your password.\n\n"
            "Your reset code is: {code}\n\n"
            "This code expires in {expiry} minutes.\n"
            "If you did not request this, you can safely ignore this email.\n"
        ),
    },
}


def send_code(to_email: str, code: str, code_type: str) -> None:
    """Send a one-time code via email. Falls back to log output in dev."""
    template = EMAIL_TEMPLATES.get(code_type, EMAIL_TEMPLATES["verify_email"])
    body = template["body"].format(
        code=code,
        expiry=_settings.CODE_EXPIRY_MINUTES,
    )

    if _settings.smtp_configured:
        msg = MIMEMultipart()
        msg["From"] = _settings.SMTP_FROM
        msg["To"] = to_email
        msg["Subject"] = template["subject"]
        msg.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(_settings.SMTP_HOST, _settings.SMTP_PORT) as server:
                server.starttls()
                if _settings.SMTP_USER:
                    server.login(_settings.SMTP_USER, _settings.SMTP_PASSWORD)
                server.sendmail(_settings.SMTP_FROM, to_email, msg.as_string())
            logger.info("Email sent to %s (type=%s)", to_email, code_type)
        except Exception as e:
            logger.error("Failed to send email to %s: %s — code=%s", to_email, e, code)
    else:
        # Dev mode: print to server log
        logger.info(
            "\n"
            "──────────────────────────────────────────────\n"
            "EMAIL (dev mode — no SMTP configured)\n"
            "To: %s\n"
            "Subject: %s\n"
            "Code: %s (type=%s, expires in %d min)\n"
            "──────────────────────────────────────────────",
            to_email,
            template["subject"],
            code,
            code_type,
            _settings.CODE_EXPIRY_MINUTES,
        )
