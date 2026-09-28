from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def priorities() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="LOW", callback_data="task:priority:LOW"),
                InlineKeyboardButton(text="NORMAL", callback_data="task:priority:NORMAL"),
            ],
            [
                InlineKeyboardButton(text="HIGH", callback_data="task:priority:HIGH"),
                InlineKeyboardButton(text="URGENT", callback_data="task:priority:URGENT"),
            ],
        ]
    )


def yes_no(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Ha", callback_data=f"task:{prefix}:yes"),
                InlineKeyboardButton(text="Yo'q", callback_data=f"task:{prefix}:no"),
            ]
        ]
    )


def confirmation(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Tasdiqlash", callback_data=f"task:yes:{token}"),
                InlineKeyboardButton(text="Bekor qilish", callback_data=f"task:no:{token}"),
            ]
        ]
    )
