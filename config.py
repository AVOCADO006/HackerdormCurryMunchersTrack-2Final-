"""Application configuration loaded from environment variables.

Fail-fast: required variables raise immediately if missing.
dev_stub refuses to start in production.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────
    APP_ENV: str = "development"
    SECRET_KEY: str
    DATABASE_URL: str = "sqlite:///./socialmedia.db"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # ── Agent Provider ───────────────────────────
    LLM_PROVIDER: str = "dev_stub"

    # ── Auth / Demo ──────────────────────────────
    AUTO_VERIFY_EMAIL: bool = True
    FIXED_2FA_CODE: str = ""
    ALLOW_DEMO_MODE: bool = True
    DAILY_RUN_LIMIT: int = 3

    # ── Auth / Security ──────────────────────────
    TOKEN_EXPIRE_HOURS: int = 168  # 7 days
    CODE_EXPIRY_MINUTES: int = 10
    MAX_CODE_ATTEMPTS: int = 5
    LOGIN_RATE_LIMIT: int = 5       # max attempts per window per email
    LOGIN_RATE_WINDOW_MINUTES: int = 15
    COOKIE_NAME: str = "session"

    # ── SMTP (optional — if empty, codes print to log) ──
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""

    # ── Platform credentials ─────────────────────
    PLATFORM_ACCESS_TOKEN: str = ""
    PLATFORM_AGENT_PREFIX: str = "smm"
    PLATFORM_LLM_ENDPOINT: str = ""

    @field_validator("LLM_PROVIDER")
    @classmethod
    def _validate_provider(cls, v: str) -> str:
        allowed = {"platform_managed_agents", "platform_cloud_llm", "dev_stub"}
        if v not in allowed:
            raise ValueError(
                f"LLM_PROVIDER must be one of {allowed}, got '{v}'"
            )
        return v

    @field_validator("APP_ENV")
    @classmethod
    def _validate_env(cls, v: str) -> str:
        if v not in ("development", "production"):
            raise ValueError("APP_ENV must be 'development' or 'production'")
        return v

    # ── Derived helpers ──────────────────────────
    @property
    def cors_list(self) -> List[str]:
        return [
            o.strip()
            for o in self.CORS_ORIGINS.split(",")
            if o.strip()
        ]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def demo_mode_active(self) -> bool:
        """Demo features only work in dev or when ALLOW_DEMO_MODE=true."""
        return self.APP_ENV == "development" or self.ALLOW_DEMO_MODE

    @property
    def auto_verify_active(self) -> bool:
        return self.AUTO_VERIFY_EMAIL and self.demo_mode_active

    @property
    def fixed_2fa_active(self) -> bool:
        return bool(self.FIXED_2FA_CODE) and self.demo_mode_active

    @property
    def smtp_configured(self) -> bool:
        return bool(self.SMTP_HOST and self.SMTP_FROM)

    def validate_startup(self) -> None:
        """Call once at startup to enforce cross-field rules."""
        # dev_stub is for local dev only — refuse to start in production
        if self.LLM_PROVIDER == "dev_stub" and self.is_production:
            raise RuntimeError(
                "LLM_PROVIDER=dev_stub is not allowed in production. "
                "Set LLM_PROVIDER to platform_managed_agents or "
                "platform_cloud_llm."
            )
        if self.is_production and self.SECRET_KEY == "change-me-to-a-random-string":
            raise RuntimeError(
                "SECRET_KEY must be changed from the default in production."
            )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.validate_startup()
    return s
