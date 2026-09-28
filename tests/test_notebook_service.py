import base64
from datetime import date, datetime
from pathlib import Path

import pytest
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import Settings
from app.database.models import AuditLog, NotebookEntry
from app.database.models.notebook import AttachmentType
from app.database.session import DatabaseManager
from app.modules.notebook.exceptions import (
    NotebookDuplicateError,
    NotebookNotFoundError,
    NotebookValidationError,
)
from app.modules.notebook.schemas import AttachmentInput, NoteCreate, NoteUpdate
from app.modules.notebook.service import NotebookService
from app.modules.notebook.storage import EncryptedLocalStorage

TODAY = datetime(2026, 9, 24).date()  # noqa: DTZ001 - fixed date fixture


def secret() -> SecretStr:
    return SecretStr(base64.urlsafe_b64encode(b"s" * 32).decode())


def service(engine, tmp_path: Path, *, scan_limit: int = 500) -> NotebookService:
    database = DatabaseManager(Settings(_env_file=None))
    database._sessions = async_sessionmaker(engine, expire_on_commit=False)
    storage = EncryptedLocalStorage(str(tmp_path), secret(), 1)
    return NotebookService(
        database,
        42,
        storage,
        secret(),
        Settings(_env_file=None).timezone,
        10,
        scan_limit,
        ("http", "https"),
    )


async def test_note_content_encrypted_and_created_for_specific_date(engine, tmp_path) -> None:
    notes = service(engine, tmp_path)
    view = await notes.create_note(
        NoteCreate(content="very private journal", entry_date=date(2026, 9, 24))
    )
    assert view.content == "very private journal"
    assert view.entry_date == date(2026, 9, 24)
    async with async_sessionmaker(engine)() as session:
        row = await session.scalar(select(NotebookEntry).where(NotebookEntry.id == view.id))
        assert row and b"very private journal" not in row.content_encrypted


async def test_today_uses_tashkent(engine, tmp_path) -> None:
    notes = service(engine, tmp_path)
    assert notes.today() == datetime.now(notes.timezone).date()


async def test_project_normalization_duplicate_and_assignment(engine, tmp_path) -> None:
    notes = service(engine, tmp_path)
    project = await notes.create_project("  Neurocit  ")
    with pytest.raises(NotebookDuplicateError):
        await notes.create_project("NEUROCIT")
    note = await notes.create_note(
        NoteCreate(content="meeting", entry_date=TODAY, project_id=project.id)
    )
    assert note.project and note.project.slug == "neurocit"
    assert (await notes.recent(project_id=project.id))[0].id == note.id


async def test_tags_normalize_deduplicate_and_filter(engine, tmp_path) -> None:
    notes = service(engine, tmp_path)
    note = await notes.create_note(
        NoteCreate(
            content="tagged",
            entry_date=TODAY,
            tags=["#Neurocit", "neurocit", "MEETING"],
        )
    )
    assert {tag.slug for tag in note.tags} == {"neurocit", "meeting"}
    assert len(await notes.tags()) == 2
    assert (await notes.recent(tag="#NEUROCIT"))[0].id == note.id


async def test_edit_and_soft_delete_exclude_note(engine, tmp_path) -> None:
    notes = service(engine, tmp_path)
    note = await notes.create_note(NoteCreate(content="old", entry_date=TODAY))
    updated = await notes.update_note(note.id, NoteUpdate(content="new", title="Title"))
    assert updated.content == "new" and updated.title == "Title"
    await notes.delete_note(note.id)
    assert await notes.recent() == []
    with pytest.raises(NotebookNotFoundError):
        await notes.get_note(note.id)


async def test_recent_order_and_date_filter(engine, tmp_path) -> None:
    notes = service(engine, tmp_path)
    older = await notes.create_note(NoteCreate(content="older", entry_date=date(2026, 9, 1)))
    newer = await notes.create_note(NoteCreate(content="newer", entry_date=date(2026, 9, 2)))
    assert [row.id for row in await notes.recent()] == [newer.id, older.id]
    assert [row.id for row in await notes.recent(entry_date=date(2026, 9, 1))] == [older.id]


async def test_bounded_decrypted_keyword_search(engine, tmp_path) -> None:
    notes = service(engine, tmp_path, scan_limit=1)
    await notes.create_note(NoteCreate(content="hidden needle", entry_date=date(2026, 9, 1)))
    newest = await notes.create_note(NoteCreate(content="visible needle", entry_date=date(2026, 9, 2)))
    assert [row.id for row in await notes.search("needle")] == [newest.id]


async def test_attachment_round_trip_duplicate_and_metadata(engine, tmp_path) -> None:
    notes = service(engine, tmp_path)
    await notes.storage.initialize()
    note = await notes.create_note(NoteCreate(content="with file", entry_date=TODAY))
    metadata = AttachmentInput(
        original_name="../../proposal.pdf",
        mime_type="application/pdf",
        source_type=AttachmentType.PDF,
    )
    attachment = await notes.add_file(note.id, b"pdf bytes", metadata)
    assert attachment.original_name == "proposal.pdf"
    async with notes.attachment_temp(attachment.id) as (path, name):
        assert path.read_bytes() == b"pdf bytes" and name == "proposal.pdf"
    with pytest.raises(NotebookDuplicateError):
        await notes.add_file(note.id, b"pdf bytes", metadata)
    assert len(list(tmp_path.rglob("*.enc"))) == 1


async def test_link_is_encrypted_and_dangerous_scheme_rejected(engine, tmp_path) -> None:
    notes = service(engine, tmp_path)
    note = await notes.create_note(NoteCreate(content="links", entry_date=TODAY))
    link = await notes.add_link(note.id, "https://example.com/private?token=x")
    assert await notes.link(link.id) == "https://example.com/private?token=x"
    with pytest.raises(NotebookValidationError):
        await notes.add_link(note.id, "javascript:alert(1)")


async def test_audit_never_contains_note_content(engine, tmp_path) -> None:
    notes = service(engine, tmp_path)
    await notes.create_note(NoteCreate(content="TOP SECRET NOTE", entry_date=TODAY))
    async with async_sessionmaker(engine)() as session:
        rows = list(await session.scalars(select(AuditLog)))
        assert rows
        assert "TOP SECRET NOTE" not in repr([row.details for row in rows])
