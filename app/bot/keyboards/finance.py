from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.modules.finance.schemas import FinanceCategoryView


def currency_keyboard(transaction_type: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=currency, callback_data=f"fin:currency:{transaction_type}:{currency}"
                )
                for currency in ("UZS", "USD", "EUR")
            ]
        ]
    )


def category_keyboard(
    categories: list[FinanceCategoryView], *, prefix: str = "fin:category"
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=item.name, callback_data=f"{prefix}:{item.id}")]
            for item in categories
        ]
    )


def confirmation(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Saqlash", callback_data=f"fin:yes:{token}"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"fin:no:{token}"),
            ]
        ]
    )


def category_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➖ Xarajat kategoriya", callback_data="fin:catadd:EXPENSE"),
                InlineKeyboardButton(text="➕ Daromad kategoriya", callback_data="fin:catadd:INCOME"),
            ],
            [InlineKeyboardButton(text="🗑 Kategoriyani o‘chirish", callback_data="fin:catdeactivate")],
        ]
    )


def edit_fields(transaction_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Summa", callback_data=f"fin:edit:amount:{transaction_id}"),
                InlineKeyboardButton(text="Kategoriya", callback_data=f"fin:edit:category:{transaction_id}"),
            ],
            [
                InlineKeyboardButton(text="Izoh", callback_data=f"fin:edit:description:{transaction_id}"),
                InlineKeyboardButton(text="Sana", callback_data=f"fin:edit:date:{transaction_id}"),
            ],
        ]
    )
