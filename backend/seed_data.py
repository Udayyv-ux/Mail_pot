"""
Seed script — populates the database with default admin, plans, policies, and settings.
Run once: python -m backend.seed_data
"""
import asyncio
import uuid
import json
from backend.database import SessionLocal, init_db
from backend.models.user import User, UserRole
from backend.models.client import Client
from backend.models.plan import Plan
from backend.models.app_settings import Policy, AppSetting
from backend.config import settings
from sqlalchemy import select


async def seed():
    await init_db()

    async with SessionLocal() as db:
        # ── Check if already seeded ──────────────────────────────────────
        result = await db.execute(select(User).where(User.role == UserRole.ADMIN))
        if result.scalar_one_or_none():
            print("Database already seeded. Skipping.")
            return

        # ── Super Admin User ─────────────────────────────────────────────
        admin_email = settings.SUPER_ADMIN_EMAIL or "admin@mailpilot.com"
        admin_user = User(
            id=str(uuid.uuid4()),
            email=admin_email,
            name="Super Admin",
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(admin_user)
        print(f"Created Super Admin: {admin_email}")

        # ── Pricing Plans ────────────────────────────────────────────────
        plans = [
            Plan(
                id=str(uuid.uuid4()), name="Free Trial", description="Get started with basic features",
                price_monthly=0, price_yearly=0, email_limit_daily=20, template_limit=2,
                campaign_limit=1, features_json=json.dumps(["20 emails/day", "2 templates", "1 campaign", "Basic AI routing", "Email support"]),
                is_active=True, is_featured=False, sort_order=0,
            ),
            Plan(
                id=str(uuid.uuid4()), name="Starter", description="Perfect for small teams and growing businesses",
                price_monthly=999, price_yearly=9990, email_limit_daily=100, template_limit=10,
                campaign_limit=5, features_json=json.dumps(["100 emails/day", "10 templates", "5 campaigns", "AI lead routing", "Priority support", "Analytics dashboard"]),
                is_active=True, is_featured=False, sort_order=1,
            ),
            Plan(
                id=str(uuid.uuid4()), name="Professional", description="For established businesses with high volume needs",
                price_monthly=2999, price_yearly=29990, email_limit_daily=500, template_limit=50,
                campaign_limit=20, features_json=json.dumps(["500 emails/day", "50 templates", "20 campaigns", "Advanced AI routing", "Custom SMTP", "Dedicated support", "Full analytics", "API access"]),
                is_active=True, is_featured=True, sort_order=2,
            ),
            Plan(
                id=str(uuid.uuid4()), name="Enterprise", description="Unlimited power for large-scale operations",
                price_monthly=9999, price_yearly=99990, email_limit_daily=5000, template_limit=200,
                campaign_limit=100, features_json=json.dumps(["5000 emails/day", "200 templates", "100 campaigns", "Premium AI routing", "Custom SMTP & domain", "24/7 dedicated support", "Full analytics & reports", "API access", "White-label option", "SLA guarantee"]),
                is_active=True, is_featured=False, sort_order=3,
            ),
        ]
        for plan in plans:
            db.add(plan)
        print("Created 4 pricing plans")

        # ── Policies ─────────────────────────────────────────────────────
        policies = [
            Policy(
                id=str(uuid.uuid4()), title="Terms of Service", slug="terms",
                content_html="<h2>Terms of Service</h2><p>Welcome to MailPilot. By using our service, you agree to these terms...</p><h3>1. Acceptable Use</h3><p>You agree not to use our service for spamming, phishing, or any illegal activity.</p><h3>2. Service Availability</h3><p>We strive for 99.9% uptime but cannot guarantee uninterrupted service.</p>",
                is_active=True,
            ),
            Policy(
                id=str(uuid.uuid4()), title="Privacy Policy", slug="privacy",
                content_html="<h2>Privacy Policy</h2><p>Your privacy is important to us. This policy describes how we collect, use, and protect your data...</p><h3>1. Data Collection</h3><p>We collect your email, name, and usage data to provide our services.</p><h3>2. Data Security</h3><p>All sensitive data is encrypted at rest and in transit.</p>",
                is_active=True,
            ),
            Policy(
                id=str(uuid.uuid4()), title="Refund Policy", slug="refund",
                content_html="<h2>Refund Policy</h2><p>We offer a 7-day money-back guarantee on all paid plans...</p>",
                is_active=True,
            ),
        ]
        for policy in policies:
            db.add(policy)
        print("Created 3 default policies")

        # ── App Settings ─────────────────────────────────────────────────
        app_settings = [
            # Branding
            AppSetting(id=str(uuid.uuid4()), key="app_name", value="MailPilot", category="branding", description="Application name"),
            AppSetting(id=str(uuid.uuid4()), key="app_tagline", value="AI-Powered Email Automation for Enterprise", category="branding", description="Tagline shown on landing page"),
            AppSetting(id=str(uuid.uuid4()), key="app_logo_url", value="", category="branding", description="Logo image URL"),

            # Landing page
            AppSetting(id=str(uuid.uuid4()), key="hero_title", value="Launch Your Emails Into Orbit", category="landing", description="Hero section headline"),
            AppSetting(id=str(uuid.uuid4()), key="hero_subtitle", value="AI-powered email automation that categorizes leads, personalizes messages, and sends at scale — all on autopilot.", category="landing", description="Hero section subtitle"),
            AppSetting(id=str(uuid.uuid4()), key="hero_cta_text", value="Start Free Trial", category="landing", description="Primary CTA button text"),
            AppSetting(id=str(uuid.uuid4()), key="features_json", value=json.dumps([
                {"icon": "🤖", "title": "AI Lead Routing", "desc": "Groq-powered AI automatically categorizes leads by project, location, and intent."},
                {"icon": "📊", "title": "Google Sheets Integration", "desc": "Connect your Google Sheet and let the engine process leads automatically."},
                {"icon": "✉️", "title": "Template Engine", "desc": "Create beautiful HTML email templates with dynamic personalization."},
                {"icon": "⚡", "title": "Smart Queue", "desc": "Rate-limited, anti-spam engine handles thousands of emails without issues."},
                {"icon": "📈", "title": "Real-time Analytics", "desc": "Track every email sent, opened, and campaign performance in real-time."},
                {"icon": "🔒", "title": "Enterprise Security", "desc": "Encrypted credentials, Google OAuth, and role-based access control."},
            ]), category="landing", description="Features list (JSON array)"),

            # Email engine defaults
            AppSetting(id=str(uuid.uuid4()), key="global_rate_limit_per_hour", value="500", category="limits", description="Max emails per hour across all clients"),
            AppSetting(id=str(uuid.uuid4()), key="default_batch_size", value="10", category="limits", description="Default emails per batch"),
            AppSetting(id=str(uuid.uuid4()), key="default_delay_seconds", value="3", category="limits", description="Default delay between emails (seconds)"),
            AppSetting(id=str(uuid.uuid4()), key="engine_paused", value="false", category="limits", description="Global engine pause flag"),

            # Razorpay (can be updated from admin)
            AppSetting(id=str(uuid.uuid4()), key="razorpay_key_id", value="", category="razorpay", description="Razorpay Key ID (public)"),
        ]
        for s in app_settings:
            db.add(s)
        print("Created default app settings")

        await db.commit()
        print("\nDatabase seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
