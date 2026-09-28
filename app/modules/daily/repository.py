from datetime import UTC, date, datetime, time

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database.models.daily import (
    DailyDelivery,
    DailyDeliveryStatus,
    DailyDeliveryType,
    DailySettings,
)
from app.database.session import DatabaseManager
from app.modules.daily.schemas import DailySettingsView
from app.modules.users.repository import UserRepository


class DailyRepository:
    def __init__(self, database: DatabaseManager, owner_id: int) -> None:
        self.database, self.owner_id = database, owner_id

    async def _owner(self, session, *, create: bool = False) -> int | None:
        users = UserRepository(session)
        owner = await users.get_by_telegram_user_id(self.owner_id)
        if owner is None and create:
            owner = await users.create(self.owner_id)
        return owner.id if owner else None

    async def get_or_create(self, morning: time, evening: time) -> DailySettingsView:
        async with self.database.session() as session:
            owner = await self._owner(session, create=True)
            assert owner is not None
            row = await session.scalar(select(DailySettings).where(DailySettings.user_id == owner))
            if row is None:
                row = DailySettings(
                    user_id=owner,
                    morning_enabled=True,
                    morning_time=morning,
                    evening_enabled=True,
                    evening_time=evening,
                )
                session.add(row)
                await session.flush()
            return DailySettingsView.model_validate(row)

    async def update_morning(self, enabled: bool, value: time | None = None) -> DailySettingsView:
        return await self._update("morning", enabled, value)

    async def update_evening(self, enabled: bool, value: time | None = None) -> DailySettingsView:
        return await self._update("evening", enabled, value)

    async def _update(self, kind: str, enabled: bool, value: time | None) -> DailySettingsView:
        async with self.database.session() as session:
            owner = await self._owner(session)
            row = await session.scalar(select(DailySettings).where(DailySettings.user_id == owner))
            if row is None:
                raise RuntimeError("Daily settings are not initialized.")
            setattr(row, f"{kind}_enabled", enabled)
            if value is not None:
                setattr(row, f"{kind}_time", value)
            await session.flush()
            return DailySettingsView.model_validate(row)

    async def claim(
        self, kind: DailyDeliveryType, day: date, scheduled_for: datetime
    ) -> int | None:
        try:
            async with self.database.session() as session:
                owner = await self._owner(session, create=True)
                assert owner is not None
                row = DailyDelivery(
                    user_id=owner,
                    delivery_type=kind,
                    scheduled_date=day,
                    scheduled_for=scheduled_for,
                    status=DailyDeliveryStatus.PENDING,
                    attempt_count=1,
                )
                session.add(row)
                await session.flush()
                return row.id
        except IntegrityError:
            return None

    async def mark(self, delivery_id: int, status: DailyDeliveryStatus) -> None:
        async with self.database.session() as session:
            row = await session.get(DailyDelivery, delivery_id)
            if row is None:
                return
            row.status = status
            if status == DailyDeliveryStatus.DELIVERED:
                row.delivered_at = datetime.now(UTC)
            await session.flush()

    async def already_delivered(self, kind: DailyDeliveryType, day: date) -> bool:
        async with self.database.session() as session:
            owner = await self._owner(session)
            if owner is None:
                return False
            row = await session.scalar(
                select(DailyDelivery.id).where(
                    DailyDelivery.user_id == owner,
                    DailyDelivery.delivery_type == kind,
                    DailyDelivery.scheduled_date == day,
                    DailyDelivery.status == DailyDeliveryStatus.DELIVERED,
                )
            )
            return row is not None
