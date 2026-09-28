from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.bot.constants import HOME, LOCK, MODULE_LABELS


def main_menu(*, include_lock: bool = True) -> ReplyKeyboardMarkup:
    labels = (HOME, *MODULE_LABELS, *((LOCK,) if include_lock else ()))
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=label) for label in labels[index : index + 2]]
            for index in range(0, len(labels), 2)
        ],
        resize_keyboard=True,
    )
