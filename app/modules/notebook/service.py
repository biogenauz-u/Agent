from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path

from sqlalchemy.exc import IntegrityError

from app.core.encryption import CredentialEncryption
from app.database.models.notebook import NotebookEntry, NotebookTag
from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction
from app.modules.notebook.audit import NotebookAudit
from app.modules.notebook.exceptions import (
    NotebookDuplicateError,
    NotebookNotFoundError,
    NotebookValidationError,
)
from app.modules.notebook.repository import NotebookRepository
from app.modules.notebook.schemas import (
    AttachmentInput,
    AttachmentView,
    NoteCreate,
    NoteUpdate,
    NoteView,
    ProjectView,
    TagView,
)
from app.modules.notebook.search import NotebookSearchService
from app.modules.notebook.storage import EncryptedLocalStorage, StoredFile
from app.modules.notebook.utils import normalize_label, safe_original_name, validate_url
from app.modules.users.repository import UserRepository


class NotebookService:
    def __init__(
        self,
        database: DatabaseManager,
        owner_id: int,
        storage: EncryptedLocalStorage,
        encryption_key,
        timezone,
        recent_limit: int,
        search_scan_limit: int,
        allowed_schemes: tuple[str, ...],
    ) -> None:
        self.database, self.owner_id, self.storage = database, owner_id, storage
        self.cipher = CredentialEncryption(encryption_key)
        self.timezone, self.recent_limit = timezone, recent_limit
        self.allowed_schemes = allowed_schemes
        self.searcher = NotebookSearchService(search_scan_limit)
        self.audit = NotebookAudit(database, owner_id)

    async def _owner(self, session, *, create: bool = False) -> int | None:
        users = UserRepository(session)
        owner = await users.get_by_telegram_user_id(self.owner_id)
        if owner is None and create:
            owner = await users.create(self.owner_id)
        return owner.id if owner else None

    async def _tags(
        self, repository: NotebookRepository, user_id: int, values: list[str]
    ) -> tuple[list[NotebookTag], list[int]]:
        result: list[NotebookTag] = []
        created: list[int] = []
        seen: set[str] = set()
        for value in values:
            name, slug = normalize_label(value)
            if slug in seen:
                continue
            seen.add(slug)
            tag = await repository.tag_by_slug(user_id, slug)
            if tag is None:
                tag = await repository.create_tag(user_id, name, slug)
                created.append(tag.id)
            result.append(tag)
        return result, created

    async def _audit_created_tags(self, tag_ids: list[int]) -> None:
        for tag_id in tag_ids:
            await self.audit.record(
                AuditAction.NOTE_TAG_CREATED,
                entity_type="notebook_tag",
                entity_id=tag_id,
                details={"tag_id": tag_id},
            )

    def _view(self, row: NotebookEntry) -> NoteView:
        return NoteView(
            id=row.id,
            title=row.title,
            content=self.cipher.decrypt(row.content_encrypted, self.owner_id, "notebook_note"),
            entry_date=row.entry_date,
            project=ProjectView.model_validate(row.project) if row.project else None,
            tags=[TagView.model_validate(tag) for tag in row.tags],
            attachments=[
                AttachmentView(
                    id=item.id,
                    original_name=item.original_name,
                    mime_type=item.mime_type,
                    file_size=item.file_size,
                    checksum=item.checksum,
                    source_type=item.source_type,
                    width=item.width,
                    height=item.height,
                    duration_seconds=item.duration_seconds,
                )
                for item in row.attachments
                if item.deleted_at is None
            ],
            is_pinned=row.is_pinned,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def today(self) -> date:
        return datetime.now(self.timezone).date()

    async def create_note(self, request: NoteCreate) -> NoteView:
        encrypted = self.cipher.encrypt(request.content, self.owner_id, "notebook_note")
        async with self.database.session() as session:
            owner = await self._owner(session, create=True)
            assert owner is not None
            repository = NotebookRepository(session)
            if request.project_id and not await repository.project(owner, request.project_id):
                raise NotebookValidationError("Project not found or inactive.")
            tags, created_tags = await self._tags(repository, owner, request.tags)
            row = await repository.create_entry(
                owner,
                encrypted,
                title=request.title.strip() if request.title else None,
                entry_date=request.entry_date,
                project_id=request.project_id,
                source=request.source,
                is_pinned=request.is_pinned,
                tags=tags,
            )
            note_id = row.id
        view = await self.get_note(note_id, audit=False)
        await self._audit_created_tags(created_tags)
        await self.audit.record(
            AuditAction.NOTE_CREATED,
            entity_type="notebook_entry",
            entity_id=note_id,
            details={"note_id": note_id},
        )
        return view

    async def get_note(self, note_id: int, *, audit: bool = True) -> NoteView:
        async with self.database.session() as session:
            owner = await self._owner(session)
            row = await NotebookRepository(session).entry(owner, note_id) if owner else None
            if row is None:
                raise NotebookNotFoundError("Note not found.")
            view = self._view(row)
        if audit:
            await self.audit.record(
                AuditAction.NOTE_VIEWED,
                entity_type="notebook_entry",
                entity_id=note_id,
                details={"note_id": note_id},
            )
        return view

    async def recent(
        self,
        *,
        entry_date: date | None = None,
        project_id: int | None = None,
        tag: str | None = None,
        limit: int | None = None,
    ) -> list[NoteView]:
        slug = normalize_label(tag)[1] if tag else None
        async with self.database.session() as session:
            owner = await self._owner(session)
            rows = (
                await NotebookRepository(session).recent(
                    owner,
                    limit or self.recent_limit,
                    entry_date=entry_date,
                    project_id=project_id,
                    tag_slug=slug,
                )
                if owner
                else []
            )
            return [self._view(row) for row in rows]

    async def count_for_date(self, day: date) -> int:
        return len(await self.recent(entry_date=day, limit=self.searcher.scan_limit))

    async def search(self, query: str) -> list[NoteView]:
        candidates = await self.recent(limit=self.searcher.scan_limit)
        result = self.searcher.filter(candidates, query, self.recent_limit)
        await self.audit.record(
            AuditAction.NOTE_SEARCHED,
            entity_type="notebook_entry",
            entity_id=None,
            details={"result_count": len(result)},
        )
        return result

    async def update_note(self, note_id: int, request: NoteUpdate) -> NoteView:
        values = request.model_dump(exclude_unset=True)
        async with self.database.session() as session:
            owner = await self._owner(session)
            repository = NotebookRepository(session)
            row = await repository.entry(owner, note_id) if owner else None
            if row is None or owner is None:
                raise NotebookNotFoundError("Note not found.")
            if "content" in values:
                values["content_encrypted"] = self.cipher.encrypt(
                    str(values.pop("content")), self.owner_id, "notebook_note"
                )
            if (
                "project_id" in values
                and values["project_id"] is not None
                and not await repository.project(owner, int(values["project_id"]))
            ):
                raise NotebookValidationError("Project not found or inactive.")
            if "tags" in values:
                values["tags"], created_tags = await self._tags(
                    repository, owner, values["tags"]
                )
            else:
                created_tags = []
            await repository.update_entry(row, values)
        view = await self.get_note(note_id, audit=False)
        await self._audit_created_tags(created_tags)
        await self.audit.record(
            AuditAction.NOTE_UPDATED,
            entity_type="notebook_entry",
            entity_id=note_id,
            details={"note_id": note_id},
        )
        return view

    async def delete_note(self, note_id: int) -> None:
        async with self.database.session() as session:
            owner = await self._owner(session)
            if not owner or not await NotebookRepository(session).soft_delete(owner, note_id):
                raise NotebookNotFoundError("Note not found.")
        await self.audit.record(
            AuditAction.NOTE_DELETED,
            entity_type="notebook_entry",
            entity_id=note_id,
            details={"note_id": note_id},
        )

    async def create_project(
        self, name: str, description: str | None = None
    ) -> ProjectView:
        display, slug = normalize_label(name)
        try:
            async with self.database.session() as session:
                owner = await self._owner(session, create=True)
                assert owner is not None
                repository = NotebookRepository(session)
                if await repository.project_by_slug(owner, slug):
                    raise NotebookDuplicateError("Project already exists.")
                row = await repository.create_project(owner, display, slug, description)
                view = ProjectView.model_validate(row)
        except IntegrityError:
            raise NotebookDuplicateError("Project already exists.") from None
        await self.audit.record(
            AuditAction.NOTE_PROJECT_CREATED,
            entity_type="notebook_project",
            entity_id=view.id,
            details={"project_id": view.id},
        )
        return view

    async def projects(self) -> list[ProjectView]:
        async with self.database.session() as session:
            owner = await self._owner(session)
            rows = await NotebookRepository(session).projects(owner) if owner else []
            return [ProjectView.model_validate(row) for row in rows]

    async def deactivate_project(self, project_id: int) -> None:
        async with self.database.session() as session:
            owner = await self._owner(session)
            if not owner or not await NotebookRepository(session).deactivate_project(owner, project_id):
                raise NotebookNotFoundError("Project not found.")

    async def tags(self) -> list[TagView]:
        async with self.database.session() as session:
            owner = await self._owner(session)
            rows = await NotebookRepository(session).tags(owner) if owner else []
            return [TagView.model_validate(row) for row in rows]

    async def add_file(
        self, note_id: int, value: bytes, metadata: AttachmentInput
    ) -> AttachmentView:
        note = await self.get_note(note_id, audit=False)
        stored = await self.storage.save_bytes(
            self.owner_id, value, note.entry_date.year, note.entry_date.month
        )
        try:
            async with self.database.session() as session:
                owner = await self._owner(session)
                repository = NotebookRepository(session)
                if owner is None or await repository.entry(owner, note_id) is None:
                    raise NotebookNotFoundError("Note not found.")
                if await repository.attachment_by_checksum(note_id, stored.checksum):
                    raise NotebookDuplicateError("Attachment already exists on this note.")
                row = await repository.create_attachment(
                    entry_id=note_id,
                    user_id=owner,
                    original_name=safe_original_name(metadata.original_name),
                    storage_name=stored.storage_name,
                    mime_type=metadata.mime_type,
                    file_size=stored.size,
                    checksum=stored.checksum,
                    encrypted_path=stored.relative_path,
                    source_type=metadata.source_type,
                    telegram_file_id=metadata.telegram_file_id,
                    telegram_file_unique_id=metadata.telegram_file_unique_id,
                    width=metadata.width,
                    height=metadata.height,
                    duration_seconds=metadata.duration_seconds,
                )
                attachment_id = row.id
        except BaseException:
            await self.storage.delete(stored.relative_path)
            raise
        await self.audit.record(
            AuditAction.NOTE_ATTACHMENT_ADDED,
            entity_type="notebook_attachment",
            entity_id=attachment_id,
            details={"note_id": note_id, "attachment_id": attachment_id},
        )
        return (await self.get_note(note_id, audit=False)).attachments[-1]

    async def add_link(self, note_id: int, url: str) -> AttachmentView:
        clean = validate_url(url, self.allowed_schemes)
        encrypted = self.cipher.encrypt(clean, self.owner_id, "notebook_link")
        checksum = __import__("hashlib").sha256(clean.encode()).hexdigest()
        try:
            async with self.database.session() as session:
                owner = await self._owner(session)
                repository = NotebookRepository(session)
                if owner is None or await repository.entry(owner, note_id) is None:
                    raise NotebookNotFoundError("Note not found.")
                if await repository.attachment_by_checksum(note_id, checksum):
                    raise NotebookDuplicateError("Link already exists on this note.")
                row = await repository.create_attachment(
                    entry_id=note_id,
                    user_id=owner,
                    original_name="link",
                    storage_name=None,
                    mime_type="text/uri-list",
                    file_size=len(clean.encode()),
                    checksum=checksum,
                    encrypted_path=None,
                    source_type="LINK",
                    link_encrypted=encrypted,
                )
                attachment_id = row.id
        except IntegrityError:
            raise NotebookDuplicateError("Link already exists on this note.") from None
        await self.audit.record(
            AuditAction.NOTE_ATTACHMENT_ADDED,
            entity_type="notebook_attachment",
            entity_id=attachment_id,
            details={"note_id": note_id, "attachment_id": attachment_id},
        )
        return (await self.get_note(note_id, audit=False)).attachments[-1]

    async def link(self, attachment_id: int) -> str:
        async with self.database.session() as session:
            owner = await self._owner(session)
            row = await NotebookRepository(session).attachment(owner, attachment_id) if owner else None
            if row is None or row.link_encrypted is None:
                raise NotebookNotFoundError("Link not found.")
            return self.cipher.decrypt(row.link_encrypted, self.owner_id, "notebook_link")

    @asynccontextmanager
    async def attachment_temp(self, attachment_id: int) -> AsyncIterator[tuple[Path, str]]:
        async with self.database.session() as session:
            owner = await self._owner(session)
            row = await NotebookRepository(session).attachment(owner, attachment_id) if owner else None
            if row is None or not row.encrypted_path or not row.storage_name:
                raise NotebookNotFoundError("File attachment not found.")
            stored = StoredFile(row.storage_name, row.encrypted_path, row.file_size, row.checksum)
            original_name = row.original_name
        async with self.storage.decrypted_temp(self.owner_id, stored) as path:
            yield path, original_name
        await self.audit.record(
            AuditAction.NOTE_ATTACHMENT_VIEWED,
            entity_type="notebook_attachment",
            entity_id=attachment_id,
            details={"attachment_id": attachment_id},
        )
