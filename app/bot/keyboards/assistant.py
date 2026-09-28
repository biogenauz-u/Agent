from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def confirmation(action_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Tasdiqlash", callback_data=f"ai:yes:{action_id}"),
                InlineKeyboardButton(text="Bekor qilish", callback_data=f"ai:no:{action_id}"),
            ]
        ]
    )
