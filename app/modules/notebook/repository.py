from datetime import UTC, date, datetime

from sqlalchemy import Select, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models.notebook import (
    NotebookAttachment,
    NotebookEntry,
    NotebookProject,
    NotebookTag,
)


class NotebookRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _loaded() -> tuple[object, ...]:
        return (
            selectinload(NotebookEntry.tags),
            selectinload(NotebookEntry.attachments),
        )

    async def project(self, user_id: int, project_id: int) -> NotebookProject | None:
        return await self.session.scalar(
            select(NotebookProject).where(
                NotebookProject.user_id == user_id,
                NotebookProject.id == project_id,
                NotebookProject.is_active.is_(True),
            )
        )

    async def project_by_slug(self, user_id: int, slug: str) -> NotebookProject | None:
        return await self.session.scalar(
            select(NotebookProject).where(
                NotebookProject.user_id == user_id, NotebookProject.slug == slug
            )
        )

    async def projects(self, user_id: int, *, active_only: bool = True) -> list[NotebookProject]:
        query = select(NotebookProject).where(NotebookProject.user_id == user_id)
        if active_only:
            query = query.where(NotebookProject.is_active.is_(True))
        return list(await self.session.scalars(query.order_by(NotebookProject.name)))

    async def create_project(
        self, user_id: int, name: str, slug: str, description: str | None
    ) -> NotebookProject:
        row = NotebookProject(user_id=user_id, name=name, slug=slug, description=description)
        self.session.add(row)
        await self.session.flush()
        return row

    async def deactivate_project(self, user_id: int, project_id: int) -> bool:
        result = await self.session.execute(
            update(NotebookProject)
            .where(
                NotebookProject.user_id == user_id,
                NotebookProject.id == project_id,
                NotebookProject.is_active.is_(True),
            )
            .values(is_active=False)
            .returning(NotebookProject.id)
        )
        return result.scalar_one_or_none() is not None

    async def tag_by_slug(self, user_id: int, slug: str) -> NotebookTag | None:
        return await self.session.scalar(
            select(NotebookTag).where(NotebookTag.user_id == user_id, NotebookTag.slug == slug)
        )

    async def tags(self, user_id: int) -> list[NotebookTag]:
        return list(
            await self.session.scalars(
                select(NotebookTag)
                .where(NotebookTag.user_id == user_id)
                .order_by(NotebookTag.name)
            )
        )

    async def create_tag(self, user_id: int, name: str, slug: str) -> NotebookTag:
        row = NotebookTag(user_id=user_id, name=name, slug=slug)
        self.session.add(row)
        await self.session.flush()
        return row

    async def create_entry(
        self,
        user_id: int,
        encrypted: bytes,
        *,
        title: str | None,
        entry_date: date,
        project_id: int | None,
        source: object,
        is_pinned: bool,
        tags: list[NotebookTag],
    ) -> NotebookEntry:
        row = NotebookEntry(
            user_id=user_id,
            title=title,
            content_encrypted=encrypted,
            entry_date=entry_date,
            project_id=project_id,
            source=source,
            is_pinned=is_pinned,
            tags=tags,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    def _entry_query(self, user_id: int) -> Select[tuple[NotebookEntry]]:
        return (
            select(NotebookEntry)
            .options(*self._loaded())
            .where(NotebookEntry.user_id == user_id, NotebookEntry.deleted_at.is_(None))
        )

    async def entry(self, user_id: int, entry_id: int) -> NotebookEntry | None:
        return await self.session.scalar(
            self._entry_query(user_id).where(NotebookEntry.id == entry_id)
        )

    async def recent(
        self,
        user_id: int,
        limit: int,
        *,
        entry_date: date | None = None,
        project_id: int | None = None,
        tag_slug: str | None = None,
    ) -> list[NotebookEntry]:
        query = self._entry_query(user_id)
        if entry_date is not None:
            query = query.where(NotebookEntry.entry_date == entry_date)
        if project_id is not None:
            query = query.where(NotebookEntry.project_id == project_id)
        if tag_slug is not None:
            query = query.where(NotebookEntry.tags.any(NotebookTag.slug == tag_slug))
        rows = await self.session.scalars(
            query.order_by(
                NotebookEntry.is_pinned.desc(),
                NotebookEntry.entry_date.desc(),
                NotebookEntry.created_at.desc(),
                NotebookEntry.id.desc(),
            ).limit(limit)
        )
        return list(rows.unique())

    async def update_entry(self, row: NotebookEntry, values: dict[str, object]) -> NotebookEntry:
        tags = values.pop("tags", None)
        for key, value in values.items():
            setattr(row, key, value)
        if tags is not None:
            row.tags = tags
        await self.session.flush()
        return row

    async def soft_delete(self, user_id: int, entry_id: int) -> bool:
        result = await self.session.execute(
            update(NotebookEntry)
            .where(
                NotebookEntry.user_id == user_id,
                NotebookEntry.id == entry_id,
                NotebookEntry.deleted_at.is_(None),
            )
            .values(deleted_at=datetime.now(UTC))
            .returning(NotebookEntry.id)
        )
        return result.scalar_one_or_none() is not None

    async def attachment_by_checksum(
        self, entry_id: int, checksum: str
    ) -> NotebookAttachment | None:
        return await self.session.scalar(
            select(NotebookAttachment).where(
                NotebookAttachment.entry_id == entry_id,
                NotebookAttachment.checksum == checksum,
                NotebookAttachment.deleted_at.is_(None),
            )
        )

    async def create_attachment(self, **values: object) -> NotebookAttachment:
        row = NotebookAttachment(**values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def attachment(
        self, user_id: int, attachment_id: int
    ) -> NotebookAttachment | None:
        return await self.session.scalar(
            select(NotebookAttachment).where(
                NotebookAttachment.user_id == user_id,
                NotebookAttachment.id == attachment_id,
                NotebookAttachment.deleted_at.is_(None),
            )
        )

