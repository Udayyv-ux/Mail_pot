import asyncio
import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select
from backend.database import SessionLocal
from backend.models.app_settings import Policy

async def run():
    async with SessionLocal() as db:
        res = await db.execute(select(Policy))
        policies = res.scalars().all()
        
        # We will delete existing policies and insert fresh ones
        for p in policies:
            await db.delete(p)
        await db.commit()

        # Create fresh policies
        data_policy = Policy(
            title="Data & Privacy Policy",
            slug="data-policy",
            icon="🔒",
            description="Learn how we protect and handle your Google Workspace and Meta data.",
            content_html="""
            <h2>1. Introduction</h2>
            <p>Welcome to <strong>Sheetx.io</strong>. We are committed to protecting your privacy and ensuring the security of your data. This Data Policy explains how we collect, use, process, and protect the information you provide when using our Email and WhatsApp automation platform.</p>
            
            <h2>2. Data We Collect</h2>
            <p>When you use Sheetx.io, we collect and process the following types of data:</p>
            <ul>
                <li><strong>Account Information:</strong> Your name, email address, and authentication details (e.g., Google OAuth tokens).</li>
                <li><strong>Integration Data:</strong> API tokens and connection credentials for third-party services like Google Workspace (Gmail, Google Sheets) and Meta (WhatsApp Business API).</li>
                <li><strong>Campaign Data:</strong> Specific columns from your connected Google Sheets (e.g., target names, contact details, notes) that you explicitly map for use in AI generation or sending.</li>
            </ul>

            <h2>3. How We Use Your Data</h2>
            <p>We use the data we collect solely for the purpose of providing, maintaining, and improving the Sheetx.io service. This includes:</p>
            <ul>
                <li>Executing your automated email and WhatsApp campaigns.</li>
                <li>Using AI to categorize lead notes and generate relevant messages (data is sent securely to our AI providers and is not used to train public models).</li>
                <li>Logging campaign statuses back to your Google Sheets.</li>
            </ul>

            <h2>4. Third-Party Sharing</h2>
            <p>We do not sell, rent, or lease your data to third parties. We only share data with essential service providers necessary to run our platform (e.g., Google APIs, Meta APIs, AI models, and secure cloud hosting).</p>

            <h2>5. Security & Retention</h2>
            <p>We implement industry-standard encryption (AES-256) for data at rest and in transit. We retain your campaign data only as long as necessary to fulfill the services requested by you, after which it is securely deleted.</p>
            """,
            is_active=True
        )

        terms_policy = Policy(
            title="Terms of Service",
            slug="terms-of-service",
            icon="⚖️",
            description="The rules and guidelines for using the Sheetx.io platform.",
            content_html="""
            <h2>1. Acceptance of Terms</h2>
            <p>By accessing or using Sheetx.io, you agree to be bound by these Terms of Service and all applicable laws and regulations. If you do not agree with any of these terms, you are prohibited from using or accessing this site.</p>
            
            <h2>2. Use License</h2>
            <p>Permission is granted to temporarily use the Sheetx.io platform for business outreach and automation, subject to the following restrictions:</p>
            <ul>
                <li>You may not use the platform to send unsolicited spam, malicious content, or engage in any illegal activities.</li>
                <li>You must comply with all regional laws regarding electronic communications (e.g., CAN-SPAM, GDPR).</li>
                <li>You may not attempt to decompile or reverse engineer any software contained on Sheetx.io.</li>
            </ul>

            <h2>3. API Usage and Limits</h2>
            <p>Sheetx.io connects to third-party APIs (Google and Meta). You are responsible for ensuring that your usage complies with the terms of service of those respective platforms. We automatically throttle sending speeds to protect reputation, but we are not liable for any account suspensions from third-party providers resulting from your campaign content.</p>

            <h2>4. Disclaimer</h2>
            <p>The materials on Sheetx.io's website are provided on an 'as is' basis. Sheetx.io makes no warranties, expressed or implied, and hereby disclaims and negates all other warranties including, without limitation, implied warranties or conditions of merchantability, fitness for a particular purpose, or non-infringement of intellectual property or other violation of rights.</p>
            """,
            is_active=True
        )

        acceptable_use = Policy(
            title="Acceptable Use Policy",
            slug="acceptable-use",
            icon="✅",
            description="Guidelines on what content and behavior is permitted on our platform.",
            content_html="""
            <h2>1. Overview</h2>
            <p>This Acceptable Use Policy outlines the acceptable and unacceptable uses of the Sheetx.io platform. Our goal is to ensure a high-quality, reputable environment for all users.</p>

            <h2>2. Prohibited Content</h2>
            <p>You may not use Sheetx.io to transmit any message that:</p>
            <ul>
                <li>Is unlawful, harmful, threatening, abusive, harassing, defamatory, vulgar, obscene, or invasive of another's privacy.</li>
                <li>Promotes discrimination, violence, or illegal acts.</li>
                <li>Infringes upon any patent, trademark, trade secret, copyright, or other proprietary rights of any party.</li>
                <li>Contains software viruses or any other computer code designed to interrupt, destroy, or limit the functionality of any computer software or hardware.</li>
            </ul>

            <h2>3. Anti-Spam Policy</h2>
            <p>Sheetx.io has a strict zero-tolerance policy against spam. You must only send messages to individuals who have opted-in or with whom you have a legitimate business interest (B2B outreach), in compliance with local laws. You must always provide a clear and easy way for recipients to opt-out or unsubscribe from your communications.</p>

            <h2>4. Enforcement</h2>
            <p>Sheetx.io reserves the right to investigate and take appropriate legal action against anyone who, in our sole discretion, violates this provision, including without limitation, removing the offending content, suspending or terminating the account of such violators, and reporting you to law enforcement authorities.</p>
            """,
            is_active=True
        )

        db.add_all([data_policy, terms_policy, acceptable_use])
        await db.commit()
        print("Successfully populated policies!")

asyncio.run(run())
