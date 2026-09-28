from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def incoming_message_actions(message_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📖 To‘liq ko‘rish", callback_data=f"ptg:read:{message_id}"
                ),
                InlineKeyboardButton(
                    text="✍️ Javob tayyorlash", callback_data=f"ptg:draft:{message_id}"
                ),
            ],
            [InlineKeyboardButton(text="🔕 E'tiborsiz", callback_data=f"ptg:ignore:{message_id}")],
        ]
    )


def draft_confirmation(draft_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Yuborish", callback_data=f"ptg:send:{draft_id}"),
                InlineKeyboardButton(text="✏️ O‘zgartirish", callback_data=f"ptg:edit:{draft_id}"),
            ],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"ptg:cancel:{draft_id}")],
        ]
    )


def disconnect_confirmation() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Uzish", callback_data="ptg:disconnect:yes"),
                InlineKeyboardButton(text="❌ Bekor", callback_data="ptg:disconnect:no"),
            ]
        ]
    )
