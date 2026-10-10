<<<<<<< HEAD
# ── Build stage ──────────────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /app

# Install build deps for bcrypt, python-docx, openpyxl
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ── Runtime stage ────────────────────────────────────────────────
FROM python:3.13-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy application code
COPY . .

# Default config — override with -e flags
ENV APP_ENV=production
ENV SECRET_KEY=changeme-in-production
ENV DATABASE_URL=sqlite:///./social_media_manager.db
ENV LLM_PROVIDER=dev_stub
ENV AUTO_VERIFY_EMAIL=false
ENV FIXED_2FA_CODE=
ENV ALLOW_DEMO_MODE=false
ENV DAILY_RUN_LIMIT=3
ENV TOKEN_EXPIRE_HOURS=24
ENV CODE_EXPIRY_MINUTES=10
ENV MAX_CODE_ATTEMPTS=5
ENV COOKIE_NAME=social_mm_token
ENV CORS_ORIGINS=http://localhost:3000,http://localhost:5173

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
=======

>>>>>>> 8ba39df05b9d05576decf283680b87c8dc07ff08
