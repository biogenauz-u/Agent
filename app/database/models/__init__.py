"""Import all mapped models so migrations discover complete metadata."""

from app.database.models.audit_log import AuditLog
from app.database.models.daily import (
    DailyDelivery,
    DailyDeliveryStatus,
    DailyDeliveryType,
    DailySettings,
)
from app.database.models.email import (
    EmailDraftStatus,
    EmailMessage,
    EmailReplyDraft,
    IntegrationState,
)
from app.database.models.finance import (
    FinanceCategory,
    FinanceCategoryType,
    FinanceSource,
    FinanceTransaction,
    FinanceTransactionType,
)
from app.database.models.google_credential import GoogleCredential
from app.database.models.notebook import (
    AttachmentType,
    NotebookAttachment,
    NotebookEntry,
    NotebookEntryTag,
    NotebookProject,
    NotebookSource,
    NotebookTag,
)
from app.database.models.personal_telegram import (
    PersonalTelegramMessage,
    PersonalTelegramReplyDraft,
    PersonalTelegramSession,
    TelegramDraftStatus,
    TelegramMessageDirection,
)
from app.database.models.reminder import Reminder, ReminderChannel, ReminderStatus
from app.database.models.task import Task, TaskPriority, TaskSource, TaskStatus
from app.database.models.user import User

__all__ = [
    "AttachmentType",
    "AuditLog",
    "DailyDelivery",
    "DailyDeliveryStatus",
    "DailyDeliveryType",
    "DailySettings",
    "EmailDraftStatus",
    "EmailMessage",
    "EmailReplyDraft",
    "FinanceCategory",
    "FinanceCategoryType",
    "FinanceSource",
    "FinanceTransaction",
    "FinanceTransactionType",
    "GoogleCredential",
    "IntegrationState",
    "NotebookAttachment",
    "NotebookEntry",
    "NotebookEntryTag",
    "NotebookProject",
    "NotebookSource",
    "NotebookTag",
    "PersonalTelegramMessage",
    "PersonalTelegramReplyDraft",
    "PersonalTelegramSession",
    "Reminder",
    "ReminderChannel",
    "ReminderStatus",
    "Task",
    "TaskPriority",
    "TaskSource",
    "TaskStatus",
    "TelegramDraftStatus",
    "TelegramMessageDirection",
    "User",
]
