"""Public commands and labels; never derive audit fields from arbitrary message text."""

COMMANDS = {
    "calendar": "Calendar",
    "today": "Bugungi rejalar",
    "tomorrow": "Ertangi rejalar",
    "upcoming": "Keyingi rejalar",
    "event_add": "Event yaratish",
    "event_update": "Event yangilash",
    "event_delete": "Event o'chirish",
    "free": "Bo'sh vaqt",
    "google_connect": "Google ulash",
    "google_status": "Google holati",
    "google_disconnect": "Google uzish",
    "cancel": "Bekor qilish",
    "remind": "Reminder yaratish",
    "reminders": "Keyingi reminderlar",
    "reminder_cancel": "Reminderni bekor qilish",
    "start": "Bosh sahifa",
    "help": "Yordam",
    "status": "Tizim holati",
    "id": "Telegram ID",
    "menu": "Menyu",
    "lock": "Qulflash",
    "unlock": "Ochish",
    "email": "Email",
    "emails": "Oxirgi emaillar",
    "email_unread": "O'qilmagan emaillar",
    "email_read": "Email o'qish",
    "email_search": "Email qidirish",
    "email_reply": "Javob draft",
    "google_gmail_status": "Gmail holati",
    "gmail_connect": "Gmail ulash",
    "gmail_disconnect": "Gmail uzish",
    "telegram": "Personal Telegram",
    "telegram_status": "Personal Telegram holati",
    "telegram_connect": "Personal Telegram ulash",
    "telegram_disconnect": "Personal Telegram uzish",
    "tg_recent": "Oxirgi personal xabarlar",
    "tg_read": "Personal xabarni o'qish",
    "tg_search": "Personal Telegram qidirish",
    "tg_reply": "Personal Telegram javob draft",
    "finance": "Finance",
    "expense": "Xarajat qo'shish",
    "income": "Daromad qo'shish",
    "transactions": "Oxirgi operatsiyalar",
    "finance_today": "Bugungi finance",
    "finance_week": "Haftalik finance",
    "finance_month": "Oylik finance",
    "finance_year": "Yillik finance",
    "finance_categories": "Finance kategoriyalar",
    "finance_edit": "Operatsiyani tahrirlash",
    "finance_delete": "Operatsiyani o'chirish",
    "skip": "O'tkazib yuborish",
    "notebook": "Notebook",
    "note": "Yangi yozuv",
    "notes": "Oxirgi yozuvlar",
    "note_today": "Bugungi yozuvlar",
    "note_date": "Sana bo'yicha yozuvlar",
    "note_project": "Project yozuvlari",
    "note_tag": "Tag yozuvlari",
    "note_search": "Notebook qidiruv",
    "note_edit": "Yozuvni tahrirlash",
    "note_delete": "Yozuvni o'chirish",
    "note_attach": "Yozuvga fayl qo'shish",
    "notebook_projects": "Notebook projectlari",
    "notebook_tags": "Notebook taglari",
    "tasks_menu": "Tasks menyusi",
    "task": "Yangi task",
    "tasks": "Ochiq tasklar",
    "task_today": "Bugungi tasklar",
    "task_tomorrow": "Ertangi tasklar",
    "task_overdue": "Kechikkan tasklar",
    "task_done": "Taskni bajarildi qilish",
    "task_edit": "Taskni tahrirlash",
    "task_delete": "Taskni o'chirish",
    "task_priority": "Task priority",
    "task_calendar": "Task Calendar sync",
    "task_carry": "Tasklarni ko'chirish",
    "daily": "Daily automation",
    "morning_now": "Morning briefing hozir",
    "evening_now": "Evening summary hozir",
    "daily_settings": "Daily sozlamalar",
}
LOCKED_ALLOWED_COMMANDS = frozenset({"start", "help", "status", "id", "unlock", "lock"})
HOME = "🏠 Bosh sahifa"
LOCK = "🔐 Lock"
MODULE_LABELS = (
    "📅 Calendar",
    "✅ Tasks",
    "⏰ Reminders",
    "📧 Email",
    "💬 Telegram",
    "💰 Finance",
    "📝 Notebook",
    "🔎 Search",
    "⚙️ Settings",
)
DENIED = "⛔ Access denied."
LOCKED = "🔐 Tizim qulflangan. Davom etish uchun /unlock buyrug‘idan foydalaning."
PLACEHOLDER = "🚧 Bu modul keyingi bosqichda ishga tushiriladi."
PIN_PROMPT = "🔐 PIN kodni kiriting."
UNLOCKED = "🔓 Tizim ochildi."
WRONG_PIN = "❌ PIN noto‘g‘ri."
LOCKOUT = "⏳ Urinishlar vaqtincha bloklandi. Keyinroq /unlock orqali qayta urinib ko‘ring."


def command_name(text: str | None) -> str | None:
    if not text or not text.startswith("/"):
        return None
    name = text.split(maxsplit=1)[0][1:].split("@", maxsplit=1)[0]
    return name if name in COMMANDS else None
