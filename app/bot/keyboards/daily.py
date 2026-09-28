from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def daily_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Morning settings", callback_data="daily:settings:morning"),
                InlineKeyboardButton(text="Evening settings", callback_data="daily:settings:evening"),
            ],
            [
                InlineKeyboardButton(text="Morning now", callback_data="daily:now:morning"),
                InlineKeyboardButton(text="Evening now", callback_data="daily:now:evening"),
            ],
        ]
    )


def period_settings(kind: str, enabled: bool) -> InlineKeyboardMarkup:
    action = "disable" if enabled else "enable"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="OFF" if enabled else "ON", callback_data=f"daily:{action}:{kind}")],
            [InlineKeyboardButton(text="Vaqtni o'zgartirish", callback_data=f"daily:time:{kind}")],
        ]
    )


def carry_forward(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Hammasini ko'chirish", callback_data=f"daily:carry:{token}")],
            [InlineKeyboardButton(text="Tanlab ko'chirish", callback_data="daily:carry:select")],
            [InlineKeyboardButton(text="Yo'q", callback_data=f"daily:cancel:{token}")],
        ]
    )
