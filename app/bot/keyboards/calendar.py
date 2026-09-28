from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def confirmation(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Tasdiqlash", callback_data=f"cal:yes:{token}"),
                InlineKeyboardButton(text="Bekor qilish", callback_data=f"cal:no:{token}"),
            ]
        ]
    )
