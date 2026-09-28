from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app.database.models import Reminder
from app.modules.reminders.schemas import ReminderDeliveryResult
from app.modules.reminders.utils import sanitize_failure


class TelegramReminderDelivery:
    """Telegram transport only; the destination is the configured owner, never a row field."""

    def __init__(self, bot: Bot, owner_id: int, timezone: ZoneInfo) -> None:
        self.bot, self.owner_id, self.timezone = bot, owner_id, timezone

    def text(self, reminder: Reminder) -> str:
        if reminder.offset_minutes == 1440:
            heading = "Ertaga:"
        elif reminder.offset_minutes == 60:
            heading = "1 soatdan keyin:"
        elif reminder.offset_minutes:
            heading = f"{reminder.offset_minutes} daqiqadan keyin:"
        else:
            heading = "Eslatma"
        details = reminder.message or reminder.title
        event_time = (
            f"\n\n{reminder.event_start_at.astimezone(self.timezone):%H:%M}"
            if reminder.event_start_at
            else ""
        )
        return f"⏰ {heading}\n\n{details}{event_time}"

    async def deliver(self, reminder: Reminder) -> ReminderDeliveryResult:
        try:
            await self.bot.send_message(self.owner_id, self.text(reminder), parse_mode=None)
            return ReminderDeliveryResult(success=True)
        except (TelegramAPIError, OSError, TimeoutError) as error:
            return ReminderDeliveryResult(success=False, failure_reason=sanitize_failure(error))
