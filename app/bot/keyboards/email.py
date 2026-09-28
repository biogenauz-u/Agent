from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def draft_confirmation(draft_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Tasdiqlash va yuborish",
                    callback_data=f"email:send:{draft_id}",
                )
            ],
            [
                InlineKeyboardButton(text="✏️ O‘zgartirish", callback_data=f"email:edit:{draft_id}"),
                InlineKeyboardButton(
                    text="❌ Bekor qilish", callback_data=f"email:cancel:{draft_id}"
                ),
            ],
        ]
    )
