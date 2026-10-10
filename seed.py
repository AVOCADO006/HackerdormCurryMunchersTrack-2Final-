"""Re-runnable seed script — creates 2 demo accounts with profiles,
past posts (with engagement metrics), and customer comments (reply drafts).

Idempotent: if accounts already exist by email, they are updated in place
and child rows are skipped (no duplicates).

Run:  python scripts/seed.py
"""
from __future__ import annotations

import datetime as dt
import os
import sys

# Ensure env vars exist before importing app
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("SECRET_KEY", "dev-secret-change-me")
os.environ.setdefault("DATABASE_URL", "sqlite:///./socialmedia.db")
os.environ.setdefault("LLM_PROVIDER", "dev_stub")
os.environ.setdefault("AUTO_VERIFY_EMAIL", "true")
os.environ.setdefault("ALLOW_DEMO_MODE", "true")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.auth.dependencies import hash_password
from app.db.dal import AccountDAL, DAL
from app.db.models import Account, Profile, ContentPlan, Post, ReplyDraft, Run, WeeklyReport
from app.db.session import Base, SessionLocal, engine, init_db


# ──────────────────────────────────────────────────────────────────
#  Demo Account A: Kak Min's Kuih Corner
# ──────────────────────────────────────────────────────────────────
KAK_MIN = {
    "email": "kakmin@socialmedia.ai",
    "password": "demo123456",
    "profile": {
        "business_name": "Kak Min's Kuih Corner",
        "business_type": "Home-based food business",
        "products": [
            {"name": "Kuih Assortment Box (10pcs)", "price": "RM 25"},
            {"name": "Party Box (30pcs, mixed)", "price": "RM 65"},
            {"name": "Corporate Catering Tray (50pcs)", "price": "RM 120"},
            {"name": "Custom Kuih Tower (Wedding/Event)", "price": "RM 350"},
            {"name": "Mini Kuih Set (6pcs, sampler)", "price": "RM 18"},
        ],
        "audience": "Corporate offices in KL needing catering, party hosts, "
        "wedding planners, families ordering for gatherings",
        "tone": "Warm, cheeky, a little Manglish — friendly auntie energy "
        "with professional polish when talking to corporate clients",
        "platforms": ["instagram", "linkedin", "x", "threads"],
        "location": "Petaling Jaya, Selangor, Malaysia",
        "videos_per_week": 3,
        "brand_notes": (
            "Past corporate catering orders from Petronas, MDEC, and a few "
            "KL startups. Best-selling items: Onde-onde, Kuih Lapis, "
            "Kuih Talam. Known for fresh daily preparation. Packaging is "
            "eco-friendly. WhatsApp is the main ordering channel; Instagram "
            "is the main marketing channel. Wants to win more corporate "
            "catering contracts through LinkedIn."
        ),
    },
}

# 8 past posts with engagement metrics
KAK_MIN_POSTS = [
    {
        "date": "2025-09-01",
        "platform": "instagram",
        "format": "reel",
        "pillar": "Behind the Scenes",
        "caption": "Morning kuih prep! Every piece handmade with love. This is what 5am looks like for us.",
        "hook": "POV: you wake up at 5am to make kuih for 3 offices",
        "script": "Open with dark kitchen, lights flick on. Close-up of hands mixing batter. Steam rising from bamboo trays. Time-lapse of colours appearing. End with finished trays lined up.",
        "shot_list": [
            "Wide shot of dark kitchen, lights turn on",
            "Close-up: hands mixing green pandan batter",
            "Steam rising from bamboo steamer trays",
            "Time-lapse: trays filling with different coloured kuih",
            "Final wide: 6 trays lined up, labelled by office",
        ],
        "hashtags": ["#kuih", "#malaysianfood", "#homebakery", "#pjfood", "#corporatecatering"],
        "design_brief": "Warm, natural light. Earthy tones. Handheld feel.",
        "on_screen_text": "Fresh Daily | Petaling Jaya",
        "status": "posted",
        "metrics": {"views": 4200, "likes": 312, "comments": 28, "shares": 15, "saves": 42},
    },
    {
        "date": "2025-09-03",
        "platform": "instagram",
        "format": "carousel",
        "pillar": "Product Showcase",
        "caption": "Our bestsellers in one tray! Swipe to see what each one is. Which is your favourite?",
        "hook": "Name that kuih! How many can you identify?",
        "script": "",
        "shot_list": [],
        "hashtags": ["#kuih", "#malaysianfood", "#kuihlapis", "#ondeonde"],
        "design_brief": "Top-down flat lay. Each slide features one kuih type with name label.",
        "on_screen_text": "",
        "status": "posted",
        "metrics": {"views": 2100, "likes": 198, "comments": 41, "shares": 8, "saves": 67},
    },
    {
        "date": "2025-09-05",
        "platform": "linkedin",
        "format": "text_post",
        "pillar": "Social Proof",
        "caption": (
            "Last week we delivered 120 pieces of kuih to Petronas for their "
            "team gathering. The HR manager said it reminded her of her "
            "grandmother's kitchen. That's the highest compliment we can get. "
            "If your office needs a treat that feels like home, we deliver "
            "across KL and PJ. DM us or WhatsApp 012-345-6789."
        ),
        "hook": "When the office canteen food just won't do...",
        "script": "",
        "shot_list": [],
        "hashtags": [],
        "design_brief": "",
        "on_screen_text": "",
        "status": "posted",
        "metrics": {"views": 850, "likes": 47, "comments": 6, "shares": 3, "saves": 12},
    },
    {
        "date": "2025-09-08",
        "platform": "instagram",
        "format": "reel",
        "pillar": "Education",
        "caption": "Did you know Onde-onde means 'boiling' in Malay? Because they float when ready! Here's how we know they're done.",
        "hook": "The secret to perfect onde-onde is in the float",
        "script": "Show pot of boiling water. Drop in green balls. They sink, then slowly float up. 'When they float, they're done.' Pull one out, cut open, show gula melaka oozing.",
        "shot_list": [
            "Close-up: pot of water at rolling boil",
            "Hands dropping green onde-onde balls in",
            "Balls sink, then slowly rise to surface",
            "Scoop one out, cut in half",
            "Gula melaka oozing out — slow mo",
        ],
        "hashtags": ["#ondeonde", "#kuih", "#foodeducation", "#malaysianfood"],
        "design_brief": "Bright, clean lighting. Macro lens for the cut shot.",
        "on_screen_text": "When it floats = it's ready",
        "status": "posted",
        "metrics": {"views": 6800, "likes": 489, "comments": 52, "shares": 34, "saves": 120},
    },
    {
        "date": "2025-09-10",
        "platform": "x",
        "format": "short_post",
        "pillar": "Community",
        "caption": "Thank you KL for keeping us busy! 3 corporate orders today and we're out of kuih talam already. Restocking tomorrow at 6am. Set your alarms!",
        "hook": "",
        "script": "",
        "shot_list": [],
        "hashtags": ["#kuih", "#klfood"],
        "design_brief": "",
        "on_screen_text": "",
        "status": "posted",
        "metrics": {"views": 340, "likes": 23, "comments": 4, "shares": 2, "saves": 0},
    },
    {
        "date": "2025-09-12",
        "platform": "instagram",
        "format": "carousel",
        "pillar": "Social Proof",
        "caption": "Corporate catering tray for MDEC's culture day! 50 pieces of assorted kuih, all gone in 20 minutes apparently. Swipe to see the setup!",
        "hook": "50 pieces. Gone in 20 minutes.",
        "script": "",
        "shot_list": [],
        "hashtags": ["#corporatecatering", "#kuih", "#mdec", "#klcatering"],
        "design_brief": "Clean office setting. Trays arranged neatly on conference table.",
        "on_screen_text": "MDEC Culture Day",
        "status": "posted",
        "metrics": {"views": 1800, "likes": 156, "comments": 19, "shares": 7, "saves": 28},
    },
    {
        "date": "2025-09-15",
        "platform": "instagram",
        "format": "story",
        "pillar": "Behind the Scenes",
        "caption": "Restocking day! Here's what our fridge looks like at 6am. Yes, we make everything fresh, no overnight storage.",
        "hook": "This is what fresh looks like at 6am",
        "script": "",
        "shot_list": [],
        "hashtags": ["#freshdaily"],
        "design_brief": "Quick story format. Bright fridge shot.",
        "on_screen_text": "Fresh daily, no overnight",
        "status": "posted",
        "metrics": {"views": 950, "likes": 67, "comments": 5, "shares": 2, "saves": 8},
    },
    {
        "date": "2025-09-17",
        "platform": "threads",
        "format": "conversational_post",
        "pillar": "Community",
        "caption": "Honest moment: almost gave up on the business last year. Orders were slow, competition everywhere. Then one corporate client tried our kuih at a friend's office party and ordered for their entire floor the next week. Never underestimate the power of one person sharing your food.",
        "hook": "Almost quit last year. One order changed everything.",
        "script": "",
        "shot_list": [],
        "hashtags": ["#smallbusiness", "#malaysia"],
        "design_brief": "",
        "on_screen_text": "",
        "status": "posted",
        "metrics": {"views": 1200, "likes": 89, "comments": 15, "shares": 6, "saves": 14},
    },
]

# 6 fake customer comments / reply drafts
KAK_MIN_COMMENTS = [
    {
        "type": "question",
        "question": "Do you deliver to Cyberjaya?",
        "reply": "Yes we do! Delivery to Cyberjaya is RM15, or free for orders above RM100. You can WhatsApp us at 012-345-6789 to place your order.",
    },
    {
        "type": "comment",
        "question": "Your kuih looks amazing! Is it halal?",
        "reply": "Thank you! Yes, all our kuih is 100% halal. We use only halal-certified ingredients and our kitchen is home-based with no non-halal items at all.",
    },
    {
        "type": "dm",
        "question": "Can I order for 100 people next Friday? Need it by 10am.",
        "reply": "Hi! Yes, we can do 100 pieces (assorted) for next Friday 10am. That would be RM240 for the Corporate Catering Tray x2. Please confirm via WhatsApp 012-345-6789 and we'll lock it in!",
    },
    {
        "type": "complaint",
        "question": "The kuih arrived a bit squished today. Not happy.",
        "reply": "Oh no, we're so sorry about that! The packaging should have held up. Please send us a photo on WhatsApp and we'll either refund or send a replacement tomorrow morning. We take quality seriously.",
    },
    {
        "type": "question",
        "question": "Do you do custom designs for weddings? Like themed colours?",
        "reply": "Yes we do! We've done pink/white themed kuih towers for weddings. Custom orders need 2 weeks notice. WhatsApp us with your theme and we'll share a mood board!",
    },
    {
        "type": "comment",
        "question": "Tried your onde-onde at the office today. Best I've had in years.ordering again next week!",
        "reply": "Aww thank you so much! That really makes our day. We'll have fresh batches ready for you next week. See you then!",
    },
]


# ──────────────────────────────────────────────────────────────────
#  Demo Account B: B2B Startup (clinic scheduling software)
# ──────────────────────────────────────────────────────────────────
B2B_STARTUP = {
    "email": "b2b@clinicflow.ai",
    "password": "demo123456",
    "profile": {
        "business_name": "ClinicFlow",
        "business_type": "B2B SaaS — scheduling software for clinics",
        "products": [
            {"name": "ClinicFlow Starter", "price": "RM 199/month"},
            {"name": "ClinicFlow Pro (multi-branch)", "price": "RM 499/month"},
            {"name": "ClinicFlow Enterprise (custom)", "price": "RM 1,200/month"},
            {"name": "Onboarding & Training Package", "price": "RM 800 one-time"},
        ],
        "audience": "Clinic owners, practice managers, healthcare administrators "
        "in Malaysia and Southeast Asia",
        "tone": "Professional, knowledgeable, empathetic to clinic pain points. "
        "Not too corporate — approachable but credible.",
        "platforms": ["linkedin", "x", "instagram"],
        "location": "Kuala Lumpur, Malaysia (serving SEA)",
        "videos_per_week": 2,
        "brand_notes": (
            "Targeting small to medium clinics (2-10 doctors). Key selling "
            "points: reduces no-shows by 40%, integrates with existing "
            "clinic management systems, Malay/English bilingual interface. "
            "Current customers: 15 clinics across Klang Valley. "
            "Want to expand to Penang and Johor."
        ),
    },
}

B2B_POSTS = [
    {
        "date": "2025-09-02",
        "platform": "linkedin",
        "format": "text_post",
        "pillar": "Thought Leadership",
        "caption": (
            "The average clinic loses RM 2,400/month to no-shows. That's "
            "a dentist's salary, a new autoclave, or 6 months of rent "
            "increase. We built ClinicFlow because the solution isn't more "
            "staff — it's smarter scheduling. Our clinics report 40% fewer "
            "no-shows in the first month. What's your no-show rate?"
        ),
        "hook": "RM 2,400/month. That's what no-shows cost your clinic.",
        "script": "",
        "shot_list": [],
        "hashtags": ["#healthtech", "#clinicmanagement", "#malaysia"],
        "design_brief": "",
        "on_screen_text": "",
        "status": "posted",
        "metrics": {"views": 1200, "likes": 34, "comments": 8, "shares": 5, "saves": 11},
    },
    {
        "date": "2025-09-04",
        "platform": "linkedin",
        "format": "carousel",
        "pillar": "Product Showcase",
        "caption": "How ClinicFlow works in 5 slides. Swipe to see the journey from patient booking to automated reminder.",
        "hook": "From booking to reminder in 3 clicks. Here's how.",
        "script": "",
        "shot_list": [],
        "hashtags": ["#healthtech", "#scheduling", "#clinicmanagement"],
        "design_brief": "Clean, medical aesthetic. Blue and white. Each slide = one step.",
        "on_screen_text": "Step 1: Patient books online",
        "status": "posted",
        "metrics": {"views": 890, "likes": 28, "comments": 4, "shares": 3, "saves": 9},
    },
    {
        "date": "2025-09-06",
        "platform": "x",
        "format": "short_post",
        "pillar": "Education",
        "caption": "Hot take: SMS reminders still outperform app notifications for clinic patients. Our data: 87% read rate vs 23% for push. Meet your patients where they are.",
        "hook": "",
        "script": "",
        "shot_list": [],
        "hashtags": ["#healthtech", "#ux"],
        "design_brief": "",
        "on_screen_text": "",
        "status": "posted",
        "metrics": {"views": 210, "likes": 12, "comments": 3, "shares": 1, "saves": 0},
    },
    {
        "date": "2025-09-09",
        "platform": "linkedin",
        "format": "text_post",
        "pillar": "Social Proof",
        "caption": (
            "Klinik Sehat in Cheras went from 22% no-show rate to 9% in "
            "their first month with ClinicFlow. Dr. Tan said: 'My "
            "receptionist used to spend 3 hours a day calling patients. "
            "Now she spends that time helping patients instead.' That's "
            "what we mean by smarter scheduling."
        ),
        "hook": "From 22% no-shows to 9%. In one month.",
        "script": "",
        "shot_list": [],
        "hashtags": ["#healthtech", "#casestudy", "#clinicmanagement"],
        "design_brief": "",
        "on_screen_text": "",
        "status": "posted",
        "metrics": {"views": 2100, "likes": 67, "comments": 12, "shares": 9, "saves": 23},
    },
    {
        "date": "2025-09-11",
        "platform": "instagram",
        "format": "reel",
        "pillar": "Product Showcase",
        "caption": "POV: you're a clinic receptionist and the phone won't stop ringing. Meanwhile, ClinicFlow is quietly confirming 15 appointments via SMS. Work smarter!",
        "hook": "When the phone rings non-stop but your scheduler has it handled",
        "script": "Split screen: left = frantic receptionist on phone. Right = ClinicFlow dashboard showing automated confirmations. End with calm receptionist smiling.",
        "shot_list": [
            "Split screen setup: left phone chaos, right clean dashboard",
            "Close-up of dashboard showing 'SMS Sent' notifications",
            "Receptionist breathing easy, smiling at a patient",
            "Caption overlay: 'Smart scheduling = calm clinics'",
        ],
        "hashtags": ["#clinicmanagement", "#healthtech", "#scheduling", "#malaysia"],
        "design_brief": "Clean, modern. Split screen format. Blue accent colours.",
        "on_screen_text": "Smart scheduling = calm clinics",
        "status": "posted",
        "metrics": {"views": 1500, "likes": 45, "comments": 6, "shares": 4, "saves": 7},
    },
    {
        "date": "2025-09-13",
        "platform": "linkedin",
        "format": "text_post",
        "pillar": "Education",
        "caption": (
            "We analysed 50,000 appointments across our 15 partner clinics. "
            "Finding: patients who book online are 3x more likely to show up "
            "than those who book by phone. The reason? Commitment consistency "
            "— they chose the slot, they own the slot. If your clinic still "
            "only takes phone bookings, you're leaving money on the table."
        ),
        "hook": "Online bookers are 3x more likely to show up. Here's why.",
        "script": "",
        "shot_list": [],
        "hashtags": ["#healthtech", "#data", "#clinicmanagement"],
        "design_brief": "",
        "on_screen_text": "",
        "status": "posted",
        "metrics": {"views": 1800, "likes": 52, "comments": 9, "shares": 7, "saves": 18},
    },
    {
        "date": "2025-09-16",
        "platform": "x",
        "format": "thread",
        "pillar": "Thought Leadership",
        "caption": "Thread: 5 things Malaysian clinics get wrong about digital scheduling. 1/5: Treating it as an 'IT project' instead of an operations upgrade. Your receptionist is the real user, not your IT guy.",
        "hook": "5 things clinics get wrong about scheduling (thread)",
        "script": "",
        "shot_list": [],
        "hashtags": ["#healthtech", "#clinicmanagement"],
        "design_brief": "",
        "on_screen_text": "",
        "status": "posted",
        "metrics": {"views": 450, "likes": 18, "comments": 5, "shares": 2, "saves": 4},
    },
    {
        "date": "2025-09-18",
        "platform": "linkedin",
        "format": "text_post",
        "pillar": "Community",
        "caption": (
            "We just signed our 15th clinic partner. Klinik Sehat, Klinik "
            "Murni, Klinik Maju — each one with a different workflow, "
            "different patient demographics, different challenges. That's "
            "why we don't believe in one-size-fits-all. Every clinic gets "
            "a customised onboarding. To the next 15!"
        ),
        "hook": "15 clinics. 15 different workflows. One platform.",
        "script": "",
        "shot_list": [],
        "hashtags": ["#healthtech", "#malaysia", "#milestone"],
        "design_brief": "",
        "on_screen_text": "",
        "status": "posted",
        "metrics": {"views": 950, "likes": 41, "comments": 7, "shares": 4, "saves": 6},
    },
]


def _ensure_account(db, spec: dict) -> Account:
    """Create or fetch an account by email. Returns the Account ORM object."""
    acct_dal = AccountDAL(db)
    account = acct_dal.get_by_email(spec["email"])
    if account is None:
        account = acct_dal.create(
            email=spec["email"],
            password_hash=hash_password(spec["password"]),
            email_verified=True,
            is_demo=True,
        )
        print(f"  Created account: {spec['email']}")
    else:
        # Update password hash in case it changed
        account.password_hash = hash_password(spec["password"])
        account.email_verified = True
        account.is_demo = True
        print(f"  Account exists, updated: {spec['email']}")
    db.flush()
    return account


def _ensure_profile(db, account_id: int, profile_data: dict) -> Profile:
    """Create or update the profile for an account."""
    dal = DAL(db, account_id)
    existing = dal.profiles.get_for_account()
    if existing is None:
        dal.profiles.create(**profile_data)
        print(f"  Created profile for account {account_id}")
    else:
        for key, value in profile_data.items():
            setattr(existing, key, value)
        print(f"  Updated profile for account {account_id}")
    db.flush()


def _seed_posts(db, account_id: int, posts_data: list, label: str) -> None:
    """Create a run + content plan + posts + reply drafts (if provided)."""
    dal = DAL(db, account_id)

    # Check if a "seed" run already exists for this account
    existing_runs = dal.runs.list()
    seed_run = None
    for r in existing_runs:
        if r.user_prompt == "[SEED] Past posts":
            seed_run = r
            break

    if seed_run is None:
        seed_run = dal.runs.create(
            mode="weekly",
            user_prompt="[SEED] Past posts",
            goal="Historical data for demo",
            status="succeeded",
            started_at=dt.datetime(2025, 9, 1, 8, 0, 0),
            finished_at=dt.datetime(2025, 9, 1, 8, 5, 0),
        )
        print(f"  Created seed run for {label}")

    # Check if plan already exists for this run
    plans = dal.content_plans.list(run_id=seed_run.id)
    if plans:
        print(f"  Posts already seeded for {label}, skipping")
        return

    plan = dal.content_plans.create(
        run_id=seed_run.id,
        week_start=dt.date(2025, 9, 1),
        strategy={"type": "historical_seed", "note": "Past posts for demo"},
        status="posted",
    )

    # Create posts
    post_metrics = {}
    for pd in posts_data:
        metrics = pd.pop("metrics", {})
        # Convert date string to Python date object
        if isinstance(pd.get("date"), str):
            pd["date"] = dt.date.fromisoformat(pd["date"])
        post = dal.posts.create(
            plan_id=plan.id,
            **pd,
        )
        post_metrics[str(post.id)] = metrics

    # For Kak Min, also seed the 6 reply drafts
    if label == "Kak Min":
        for cd in KAK_MIN_COMMENTS:
            dal.reply_drafts.create(plan_id=plan.id, **cd)

    # Create a weekly report with the post metrics
    dal.weekly_reports.create(
        week_start=dt.date(2025, 9, 1),
        post_metrics=post_metrics,
        orders=[
            {"item": "Corporate Catering Tray", "qty": 3, "rm": 360},
            {"item": "Party Box", "qty": 2, "rm": 130},
            {"item": "Kuih Assortment Box", "qty": 5, "rm": 125},
        ] if label == "Kak Min" else [],
        revenue_rm=615.0 if label == "Kak Min" else 0.0,
        costs={"ingredients": 180, "packaging": 45, "delivery": 30, "boost": 0}
        if label == "Kak Min"
        else {},
        computed_metrics={
            "total_posts": len(posts_data),
            "total_views": sum(m.get("views", 0) for m in
                [p.get("metrics", {}) for p in
                 [{"metrics": v} for v in post_metrics.values()]]),
            "total_engagement": 0,
        } if False else {},  # We'll compute below
        analysis={
            "note": "Historical seed data for demo",
            "best_post_format": "reel",
            "best_platform": "instagram",
        },
    )

    # Fix computed_metrics with real sums
    total_views = sum(m.get("views", 0) for m in post_metrics.values())
    total_likes = sum(m.get("likes", 0) for m in post_metrics.values())
    total_comments = sum(m.get("comments", 0) for m in post_metrics.values())
    total_shares = sum(m.get("shares", 0) for m in post_metrics.values())
    total_saves = sum(m.get("saves", 0) for m in post_metrics.values())

    # Update the weekly report we just created
    wr = dal.weekly_reports.list()[-1]
    wr.computed_metrics = {
        "total_posts": len(posts_data),
        "total_views": total_views,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "total_shares": total_shares,
        "total_saves": total_saves,
        "engagement_rate": round(
            (total_likes + total_comments + total_shares + total_saves)
            / max(total_views, 1)
            * 100,
            2,
        ),
    }
    db.flush()
    print(f"  Seeded {len(posts_data)} posts for {label}")


def main():
    print("Initializing database...")
    init_db()

    db = SessionLocal()
    try:
        # ── Account A: Kak Min ──
        print("\n[1/2] Kak Min's Kuih Corner")
        account_a = _ensure_account(db, KAK_MIN)
        _ensure_profile(db, account_a.id, KAK_MIN["profile"])
        # Deep-copy posts so we don't mutate the module-level list
        import copy
        posts_a = copy.deepcopy(KAK_MIN_POSTS)
        _seed_posts(db, account_a.id, posts_a, "Kak Min")

        # ── Account B: B2B Startup ──
        print("\n[2/2] ClinicFlow (B2B)")
        account_b = _ensure_account(db, B2B_STARTUP)
        _ensure_profile(db, account_b.id, B2B_STARTUP["profile"])
        posts_b = copy.deepcopy(B2B_POSTS)
        _seed_posts(db, account_b.id, posts_b, "ClinicFlow")

        db.commit()
        print("\nSeed complete. Both demo accounts ready.")
        print("  Kak Min:  kakmin@socialmedia.ai / demo123456")
        print("  ClinicFlow: b2b@clinicflow.ai / demo123456")

    except Exception as e:
        db.rollback()
        print(f"\nSeed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
