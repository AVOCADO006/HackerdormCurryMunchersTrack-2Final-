<<<<<<< HEAD
# AI Social Media Manager — Backend

Backend for a multi-agent social media manager web app. A business owner
logs in, completes a profile, and gives one prompt. A team of AI agents
decomposes the goal, runs tasks in parallel, validates its own work, and
delivers a weekly content plan, LinkedIn campaign, reply drafts, and
weekly performance/finance reports.

## Stack

- **Python 3.13**, **FastAPI**, **SQLAlchemy 2**, **Pydantic v2**, **asyncio**
- Database via `DATABASE_URL` (SQLite default, Postgres-compatible)
- `pytest` for isolation + validator tests (217 tests)
- `openpyxl`, `python-docx` for exports
- Docker support with multi-stage build

## Project structure

```
app/
  main.py              # App factory + startup (v0.8.0)
  config.py            # Env loading, fail-fast validation
  db/
    models.py           # 16 SQLAlchemy models
    session.py          # Engine, Base, session
    dal.py              # Data-access layer (every query takes account_id)
  auth/
    dependencies.py     # JWT decode + current-account injection
    schemas.py          # Pydantic models for auth endpoints
    codes.py            # One-time code generation + verification
    rate_limit.py       # Login rate limiter
    email.py            # SMTP or log-based email sender
  api/
    health.py           # GET /api/health
    auth.py             # 10 auth endpoints (signup, login, 2FA, reset, etc.)
    profile.py          # GET/PUT /api/profile, brand files CRUD
    runs.py             # POST /api/agent/run, list, detail, cancel
    plans.py            # Weekly workflow, plans CRUD, 7-day calendar
    campaigns.py        # LinkedIn campaign workflow + CRUD
    editing.py          # PATCH posts/replies/assets + version history
    regenerate.py       # Regenerate posts, plans, campaign assets
    export.py           # Export plans/campaigns as xlsx/docx/md, copy
    validation.py       # Code checks + Reviewer agent validation
    reports.py          # Weekly + period reports, history
    dashboard.py        # Aggregated metrics + recent activity
    errors.py           # Unified {error: {code, message}} format
  agents/
    registry.py         # 7 agent configs with system prompts
    schemas.py          # AgentResult dataclass + 7 output schemas
    providers/
      base.py           # BaseProvider ABC
      dev_stub.py       # Deterministic mock responses (dev only)
      platform_cloud.py # LLM chat completions via platform API
      platform_managed.py # Platform managed agent API
  engine/
    orchestrator.py     # Weekly + campaign workflows with retry
  services/
    usage.py            # Daily run limit check (429 on exceeded)
    context.py          # build_context: profile + playbook + festive dates
    versioning.py       # Save/restore asset versions
    export.py           # xlsx/docx/md generation for plans/campaigns
    reports.py          # Weekly + period report computation
    validation.py       # 8 deterministic code checks + Reviewer agent
  data/
    playbook/           # 8 marketing playbook markdown files
    festive_calendar.json  # Malaysian festive calendar 2025-2026
scripts/
  seed.py               # Re-runnable seed (Kak Min's Kuih Corner + ClinicFlow)
tests/
  conftest.py           # File-based test.db, env setup, fixtures
  test_isolation.py     # 14 cross-account isolation tests
  test_auth.py          # 17 auth tests
  test_usage.py         # 3 usage limit tests
  test_phase3.py        # 31 profile/playbook/context tests
  test_phase4.py        # 20 agent registry/provider tests
  test_phase5.py        # 15 orchestrator/run tests
  test_phase6.py        # 11 weekly workflow/plans tests
  test_phase7.py        # 9 campaign tests
  test_phase8.py        # 10 validation tests
  test_phase9.py        # 34 editing/versions/regen/export tests
  test_phase10.py       # 26 reports/finance/history tests
  test_phase11.py       # 21 dashboard/hardening tests
requirements.txt
.env.example
pytest.ini
Dockerfile
.dockerignore
```

## Environment variables

| Variable | Default | Required | Notes |
|---|---|---|---|
| `APP_ENV` | `development` | | `production` blocks `dev_stub` |
| `SECRET_KEY` | (random) | Yes | Random string; fail-fast if default in production |
| `DATABASE_URL` | `sqlite:///./socialmedia.db` | | Postgres-compatible |
| `LLM_PROVIDER` | `dev_stub` | | `platform_managed_agents` \| `platform_cloud_llm` \| `dev_stub` |
| `CORS_ORIGINS` | `localhost:3000,5173` | | Comma-separated |
| `AUTO_VERIFY_EMAIL` | `true` | | Skip email verification in dev |
| `FIXED_2FA_CODE` | (empty) | | If set, 2FA always uses this code |
| `ALLOW_DEMO_MODE` | `true` | | Enables auto-verify + fixed 2FA |
| `DAILY_RUN_LIMIT` | `3` | | Per-account daily run limit |
| `TOKEN_EXPIRE_HOURS` | `24` | | JWT expiry |
| `CODE_EXPIRY_MINUTES` | `10` | | One-time code expiry |
| `MAX_CODE_ATTEMPTS` | `5` | | Max code attempts before lockout |
| `SMTP_*` | (empty) | | SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM |
| `PLATFORM_LLM_ENDPOINT` | (empty) | | For platform_cloud_llm provider |
| `PLATFORM_ACCESS_TOKEN` | (empty) | | For platform_cloud_llm provider |

Copy `.env.example` to `.env` and edit:
```bash
cp .env.example .env
```

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Seed demo data (re-runnable)
python scripts/seed.py

# 3. Run tests
pytest

# 4. Start the server
uvicorn app.main:app --reload --port 8000
```

## Docker

```bash
docker build -t social-media-manager .
docker run -p 8000:8000 -e SECRET_KEY=your-secret social-media-manager
```

## Demo accounts

| Email | Password | Business |
|---|---|---|
| `demo@socialmedia.ai` | `demo123456` | Kak Min's Kuih Corner |
| `b2b@test.com` | `test123456` | TechFlow Solutions |

Both are `is_demo=true`, email-verified, and unlimited runs.

## API Endpoints

### Auth
| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/signup` | Create account |
| POST | `/api/auth/verify-email` | Verify email with code |
| POST | `/api/auth/login` | Login (returns token or requires_2fa) |
| POST | `/api/auth/verify-2fa` | Verify 2FA code |
| POST | `/api/auth/logout` | Clear cookie |
| POST | `/api/auth/forgot-password` | Request reset code |
| POST | `/api/auth/reset-password` | Reset with code |
| POST | `/api/auth/change-password` | Change password |
| PATCH | `/api/auth/2fa` | Toggle 2FA |
| DELETE | `/api/auth/account` | Delete account |

### Profile
| Method | Path | Description |
|---|---|---|
| GET | `/api/profile` | Get profile |
| PUT | `/api/profile` | Create/update profile |
| POST | `/api/profile/files` | Upload brand file (txt/csv/docx) |
| GET | `/api/profile/files` | List brand files |
| DELETE | `/api/profile/files/{id}` | Delete brand file |

### Runs
| Method | Path | Description |
|---|---|---|
| POST | `/api/agent/run` | Create and execute a run |
| GET | `/api/runs` | List runs |
| GET | `/api/runs/{id}` | Run detail with events |
| GET | `/api/runs/{id}/events` | List run events |
| POST | `/api/runs/{id}/cancel` | Cancel a running run |

### Weekly Workflow
| Method | Path | Description |
|---|---|---|
| POST | `/api/workflows/weekly` | Trigger weekly workflow |
| GET | `/api/plans` | List content plans |
| GET | `/api/plans/{id}` | Plan with 7-day calendar |
| GET | `/api/plans/{id}/posts` | List posts |
| GET | `/api/plans/{id}/replies` | List reply drafts |
| PATCH | `/api/plans/{id}` | Update plan status |

### Campaigns
| Method | Path | Description |
|---|---|---|
| POST | `/api/campaigns` | Trigger LinkedIn campaign |
| GET | `/api/campaigns` | List campaigns |
| GET | `/api/campaigns/{id}` | Campaign detail with assets |
| GET | `/api/campaigns/{id}/assets` | List campaign assets |
| PATCH | `/api/campaigns/{id}` | Update campaign status |

### Editing & Versions
| Method | Path | Description |
|---|---|---|
| PATCH | `/api/posts/{id}` | Edit a post |
| GET | `/api/posts/{id}/versions` | List post versions |
| POST | `/api/posts/{id}/restore/{vno}` | Restore post version |
| PATCH | `/api/replies/{id}` | Edit a reply draft |
| GET | `/api/replies/{id}/versions` | List reply versions |
| POST | `/api/replies/{id}/restore/{vno}` | Restore reply version |
| PATCH | `/api/campaign-assets/{id}` | Edit campaign asset |
| GET | `/api/campaign-assets/{id}/versions` | List asset versions |
| POST | `/api/campaign-assets/{id}/restore/{vno}` | Restore asset version |

### Regeneration
| Method | Path | Description |
|---|---|---|
| POST | `/api/posts/{id}/regenerate` | Regenerate a single post |
| POST | `/api/plans/{id}/regenerate` | Regenerate all posts in a plan |
| POST | `/api/campaign-assets/{id}/regenerate` | Regenerate a campaign asset |

### Export
| Method | Path | Description |
|---|---|---|
| GET | `/api/plans/{id}/export?format=` | Export plan (xlsx/docx/md) |
| GET | `/api/campaigns/{id}/export?format=` | Export campaign (xlsx/md) |
| GET | `/api/posts/{id}/copy` | Get post as plain text |

### Validation
| Method | Path | Description |
|---|---|---|
| GET | `/api/runs/{id}/validation` | Get validation report |
| POST | `/api/runs/{id}/validation` | Re-run validation |

### Reports
| Method | Path | Description |
|---|---|---|
| POST | `/api/reports/weekly` | Create weekly report |
| GET | `/api/reports/weekly` | List weekly reports |
| GET | `/api/reports/weekly/{id}` | Get weekly report |
| POST | `/api/reports/period` | Create period report |
| GET | `/api/reports/period` | List period reports |
| GET | `/api/reports/period/{id}` | Get period report |

### Dashboard & History
| Method | Path | Description |
|---|---|---|
| GET | `/api/dashboard` | Aggregated metrics + recent activity |
| GET | `/api/history` | Full account history timeline |

## Architecture

### Per-account isolation
Every table has `account_id`. The data-access layer (`app/db/dal.py`)
filters every query by `account_id`. The test suite proves account A
cannot read, update, or delete account B's rows across all 16 models.

### Agent system
7 AI agents with a pluggable provider interface:
1. **Strategist** — Decomposes goal into task plan
2. **Trend Research** — Finds relevant trends
3. **Content Creator** — Creates 7-day content plan
4. **Community Manager** — Drafts reply templates
5. **LinkedIn Campaign Planner** — Creates B2B campaign assets
6. **Finance Analyst** — Analyzes performance, suggests adaptations
7. **Reviewer** — Validates content quality

Three provider implementations:
- `dev_stub` — Deterministic mock responses for local dev (refuses to start in production)
- `platform_cloud_llm` — LLM chat completions via platform API
- `platform_managed_agents` — Platform managed agent API

### Validation
8 deterministic code checks (captions, hooks, hashtags, pillar balance,
tone, platform format, CTA presence, duplicates) + Reviewer agent for
holistic review. Verdict: pass / fix / fail.

### Error format
All errors return: `{ "error": { "code": "...", "message": "..." } }`

## Test results

217 tests covering:
- Cross-account isolation (14 tests)
- Authentication (17 tests)
- Usage limits (3 tests)
- Profile, brand files, playbook, context (31 tests)
- Agent registry and providers (20 tests)
- Orchestrator and run engine (15 tests)
- Weekly workflow and plans (11 tests)
- LinkedIn campaigns (9 tests)
- Validation and reviewer (10 tests)
- Editing, versions, regeneration, export (34 tests)
- Reports, finance, history (26 tests)
- Dashboard and hardening (21 tests)
=======

>>>>>>> 8ba39df05b9d05576decf283680b87c8dc07ff08
