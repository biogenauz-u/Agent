"""Gmail read-only integration. Incoming content is always untrusted data."""

from app.modules.email.client import GMAIL_READONLY_SCOPE
from app.modules.email.service import EmailService

__all__ = ["GMAIL_READONLY_SCOPE", "EmailService"]
