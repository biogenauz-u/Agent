from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def confirmation(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Saqlash", callback_data=f"rem:yes:{token}"),
                InlineKeyboardButton(text="Bekor qilish", callback_data=f"rem:no:{token}"),
            ]
        ]
    )
