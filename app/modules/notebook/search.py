from app.modules.notebook.schemas import NoteView


class NotebookSearchService:
    """Bounded application-side search over decrypted owner notes."""

    def __init__(self, scan_limit: int) -> None:
        self.scan_limit = scan_limit

    def filter(self, notes: list[NoteView], query: str, limit: int) -> list[NoteView]:
        needle = query.strip().casefold()
        if not needle:
            return []
        return [
            note
            for note in notes[: self.scan_limit]
            if needle in note.content.casefold() or needle in (note.title or "").casefold()
        ][:limit]
