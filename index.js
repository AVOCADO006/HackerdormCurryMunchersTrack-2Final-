import Database from 'better-sqlite3';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const dbPath = path.resolve(__dirname, '../../data/social_media_manager.db');
const dataDir = path.dirname(dbPath);

if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir, { recursive: true });
}

const db = new Database(dbPath);

db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

// ============================================================
// SCHEMA — all tables enforce per-account data isolation
// via the account_id foreign key on every business-data table.
// ============================================================

db.exec(`
  -- Accounts / Businesses
  CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_demo INTEGER DEFAULT 0,
    email_verified INTEGER DEFAULT 0,
    two_factor_enabled INTEGER DEFAULT 0,
    two_factor_secret TEXT,
    runs_today INTEGER DEFAULT 0,
    runs_date TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
  );

  -- Password reset tokens
  CREATE TABLE IF NOT EXISTS password_reset_tokens (
    token TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL,
    used INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
  );

  -- Email verification tokens
  CREATE TABLE IF NOT EXISTS email_verification_tokens (
    token TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL,
    used INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
  );

  -- Business Profiles
  CREATE TABLE IF NOT EXISTS profiles (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    business_name TEXT NOT NULL,
    business_type TEXT,
    niche TEXT,
    description TEXT,
    brand_voice TEXT,
    target_audience TEXT,
    platforms TEXT DEFAULT '[]',
    capacity_hours_per_week INTEGER DEFAULT 10,
    has_designer INTEGER DEFAULT 0,
    can_film INTEGER DEFAULT 1,
    brand_colors TEXT,
    brand_fonts TEXT,
    logo_url TEXT,
    location TEXT,
    currency TEXT DEFAULT 'RM',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
  );

  -- Workflow Runs
  CREATE TABLE IF NOT EXISTS workflow_runs (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    goal TEXT NOT NULL,
    constraints TEXT DEFAULT '{}',
    status TEXT DEFAULT 'pending',
    workflow_type TEXT DEFAULT 'weekly',
    agent_steps TEXT DEFAULT '[]',
    result_summary TEXT,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
  );

  -- Agent Step Log (detailed per-step trace)
  CREATE TABLE IF NOT EXISTS agent_steps (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
    agent_role TEXT NOT NULL,
    task TEXT,
    status TEXT DEFAULT 'pending',
    input TEXT,
    output TEXT,
    attempts INTEGER DEFAULT 0,
    error TEXT,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
  );

  -- Content Plans (weekly calendars)
  CREATE TABLE IF NOT EXISTS content_plans (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    week_start TEXT,
    week_end TEXT,
    platforms TEXT DEFAULT '[]',
    created_at TEXT DEFAULT (datetime('now'))
  );

  -- Posts (individual post kits within a content plan)
  CREATE TABLE IF NOT EXISTS posts (
    id TEXT PRIMARY KEY,
    content_plan_id TEXT NOT NULL REFERENCES content_plans(id) ON DELETE CASCADE,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    day_of_week TEXT,
    date TEXT,
    platform TEXT NOT NULL,
    post_type TEXT NOT NULL,
    caption TEXT,
    hook TEXT,
    video_script TEXT,
    shot_list TEXT DEFAULT '[]',
    hashtags TEXT DEFAULT '[]',
    design_brief TEXT,
    carousel_slides TEXT DEFAULT '[]',
    on_screen_text TEXT,
    call_to_action TEXT,
    status TEXT DEFAULT 'draft',
    versions TEXT DEFAULT '[]',
    current_version INTEGER DEFAULT 0,
    source_link TEXT,
    is_placeholder INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
  );

  -- Reply Drafts (for common comments and DMs)
  CREATE TABLE IF NOT EXISTS reply_drafts (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    question_type TEXT NOT NULL,
    question_text TEXT,
    reply_text TEXT,
    platform TEXT,
    status TEXT DEFAULT 'draft',
    versions TEXT DEFAULT '[]',
    created_at TEXT DEFAULT (datetime('now'))
  );

  -- Review Logs (issues found and fixes made per run)
  CREATE TABLE IF NOT EXISTS review_logs (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
    reviewer_agent TEXT DEFAULT 'Reviewer',
    asset_type TEXT,
    asset_id TEXT,
    issue TEXT,
    fix TEXT,
    status TEXT DEFAULT 'fixed',
    created_at TEXT DEFAULT (datetime('now'))
  );

  -- Campaigns (LinkedIn B2B campaigns)
  CREATE TABLE IF NOT EXISTS campaigns (
    id TEXT PRIMARY KEY,
    run_id TEXT REFERENCES workflow_runs(id) ON DELETE SET NULL,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    business_goal TEXT NOT NULL,
    duration_weeks INTEGER DEFAULT 4,
    budget REAL DEFAULT 0,
    budget_currency TEXT DEFAULT 'RM',
    resources TEXT DEFAULT '{}',
    target_audience TEXT,
    offer TEXT,
    tone TEXT,
    proof_points TEXT,
    phases TEXT DEFAULT '[]',
    plan_type TEXT,
    status TEXT DEFAULT 'draft',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
  );

  -- Campaign Assets
  CREATE TABLE IF NOT EXISTS campaign_assets (
    id TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    asset_type TEXT NOT NULL,
    title TEXT,
    content TEXT,
    slides TEXT DEFAULT '[]',
    script TEXT,
    shot_list TEXT DEFAULT '[]',
    on_screen_text TEXT,
    caption TEXT,
    call_to_action TEXT,
    design_brief TEXT,
    source_link TEXT,
    is_placeholder INTEGER DEFAULT 0,
    phase TEXT,
    status TEXT DEFAULT 'draft',
    versions TEXT DEFAULT '[]',
    current_version INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
  );

  -- Weekly Reports
  CREATE TABLE IF NOT EXISTS weekly_reports (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    week_start TEXT,
    week_end TEXT,
    post_metrics TEXT DEFAULT '[]',
    finance_inputs TEXT DEFAULT '{}',
    analysis TEXT,
    next_week_plan TEXT,
    budget_suggestions TEXT,
    status TEXT DEFAULT 'draft',
    created_at TEXT DEFAULT (datetime('now'))
  );

  -- Periodic Reports (monthly, quarterly, annual)
  CREATE TABLE IF NOT EXISTS period_reports (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    report_type TEXT NOT NULL,
    period_start TEXT,
    period_end TEXT,
    source_report_ids TEXT DEFAULT '[]',
    content TEXT,
    status TEXT DEFAULT 'draft',
    created_at TEXT DEFAULT (datetime('now'))
  );

  -- Indexes for per-account queries
  CREATE INDEX IF NOT EXISTS idx_profiles_account ON profiles(account_id);
  CREATE INDEX IF NOT EXISTS idx_workflow_runs_account ON workflow_runs(account_id);
  CREATE INDEX IF NOT EXISTS idx_agent_steps_run ON agent_steps(run_id);
  CREATE INDEX IF NOT EXISTS idx_content_plans_run ON content_plans(run_id);
  CREATE INDEX IF NOT EXISTS idx_content_plans_account ON content_plans(account_id);
  CREATE INDEX IF NOT EXISTS idx_posts_plan ON posts(content_plan_id);
  CREATE INDEX IF NOT EXISTS idx_posts_account ON posts(account_id);
  CREATE INDEX IF NOT EXISTS idx_reply_drafts_run ON reply_drafts(run_id);
  CREATE INDEX IF NOT EXISTS idx_reply_drafts_account ON reply_drafts(account_id);
  CREATE INDEX IF NOT EXISTS idx_review_logs_run ON review_logs(run_id);
  CREATE INDEX IF NOT EXISTS idx_campaigns_account ON campaigns(account_id);
  CREATE INDEX IF NOT EXISTS idx_campaign_assets_campaign ON campaign_assets(campaign_id);
  CREATE INDEX IF NOT EXISTS idx_campaign_assets_account ON campaign_assets(account_id);
  CREATE INDEX IF NOT EXISTS idx_weekly_reports_account ON weekly_reports(account_id);
  CREATE INDEX IF NOT EXISTS idx_period_reports_account ON period_reports(account_id);
`);

export default db;
