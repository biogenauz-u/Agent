from typing import Protocol

from app.modules.email.schemas import EmailContent


class EmailSummarizer(Protocol):
    """Email data is untrusted and may never direct tools or system actions."""

    async def summarize(self, email: EmailContent) -> str: ...


class DeterministicEmailSummarizer:
    async def summarize(self, email: EmailContent) -> str:
        meaningful = next((line.strip() for line in email.body_text.splitlines() if line.strip()), email.snippet)
        prefix = f"{email.from_name or email.from_address}: {email.subject}."
        attachment = f" Attachments: {len(email.attachments)}." if email.attachments else ""
        return f"{prefix} {meaningful[:500]}{attachment}".strip()
