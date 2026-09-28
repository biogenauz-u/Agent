from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def confirmation(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Saqlash", callback_data=f"nb:yes:{token}"),
                InlineKeyboardButton(text="Bekor qilish", callback_data=f"nb:no:{token}"),
            ]
        ]
    )


def note_list(ids_and_labels: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label[:60], callback_data=f"nb:view:{identifier}")]
            for identifier, label in ids_and_labels
        ]
    )


def finish_attachments() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Tugatish", callback_data="nb:attach:done")],
            [InlineKeyboardButton(text="Bekor qilish", callback_data="nb:attach:cancel")],
        ]
    )


def attachment_files(items: list[tuple[int, str]]) -> InlineKeyboardMarkup | None:
    rows = [
        [InlineKeyboardButton(text=name[:60], callback_data=f"nb:file:{identifier}")]
        for identifier, name in items
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None
