from app.modules.personal_telegram.utils import safe_preview


class PersonalTelegramDraftTextService:
    """Deterministic foundation: owner text is preserved; no LLM is involved."""

    async def prepare(self, owner_text: str) -> str:
        value = owner_text.strip()
        if not value or len(value) > 4000:
            raise ValueError("Draft must contain 1-4000 characters.")
        # Remove control characters without pretending to rewrite the owner's meaning.
        return safe_preview(value, 4000)
