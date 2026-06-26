"""
SQLAlchemy models package.
"""
from backend.models.user import User
from backend.models.client import Client
from backend.models.plan import Plan
from backend.models.template import Template
from backend.models.campaign import Campaign
from backend.models.email_log import EmailLog
from backend.models.payment import Payment
from backend.models.app_settings import Policy, AppSetting, DemoRequest, Notification
from backend.models.email_queue import EmailQueue
from backend.models.promo_code import PromoCode
from backend.models.image import UploadedImage
from backend.models.appointment import Appointment
from backend.models.newsletter import NewsletterSubscriber
__all__ = [
    "User", "Client", "Plan", "Template", "Campaign",
    "EmailLog", "Payment", "Policy", "AppSetting", "DemoRequest", "Notification",
    "EmailQueue", "PromoCode", "UploadedImage", "Appointment", "NewsletterSubscriber"
]
