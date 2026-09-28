from io import BytesIO

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message

from app.bot.context import BotContext
from app.bot.keyboards.assistant import confirmation
from app.modules.assistant.exceptions import AssistantError, AssistantNotConfiguredError
from app.modules.audit.actions import AuditAction
from app.modules.voice.exceptions import VoiceError


def runtime(context: BotContext):
    if context.assistant is None:
        raise AssistantNotConfiguredError("AI assistant sozlanmagan.")
    return context.assistant


async def present(message: Message, result) -> None:
    await message.answer(
        result.message,
        reply_markup=confirmation(result.action_id) if result.kind == "confirmation" else None,
    )


async def text_fallback(message: Message, app_context: BotContext) -> None:
    try:
        await present(message, await runtime(app_context).router.route(message.text or ""))
    except AssistantError as error:
        await message.answer(str(error))


async def voice_fallback(message: Message, app_context: BotContext, bot: Bot) -> None:
    try:
        assistant = runtime(app_context)
        if assistant.stt is None:
            raise AssistantNotConfiguredError("Voice transcription sozlanmagan.")
        voice = message.voice
        assert voice is not None
        if (voice.file_size or 0) > assistant.stt.max_bytes:
            raise AssistantError("Voice fayl juda katta.")
        buffer = BytesIO()
        await bot.download(voice, destination=buffer)
        try:
            transcript = await assistant.stt.transcribe_bytes(
                buffer.getvalue(), language_hint="uz"
            )
        finally:
            buffer.close()
        await assistant.router.audit.record(
            AuditAction.VOICE_TRANSCRIBED,
            {"language": transcript.detected_language or "unknown"},
        )
        await message.answer(f"Tushundim:\n\n{transcript.text}")
        await present(message, await assistant.router.route(transcript.text))
    except AssistantError as error:
        await message.answer(str(error))
    except VoiceError:
        await message.answer(
            "Ovozli xabarni matnga aylantirib bo‘lmadi. Iltimos, birozdan keyin qayta yuboring."
        )


async def confirm_callback(callback: CallbackQuery, app_context: BotContext) -> None:
    action_id = (callback.data or "").rsplit(":", 1)[-1]
    try:
        if ":no:" in (callback.data or ""):
            await runtime(app_context).router.cancel(callback.from_user.id, action_id)
            text = "Bekor qilindi."
        else:
            result = await runtime(app_context).router.confirm(callback.from_user.id, action_id)
            text = result.message
    except AssistantError as error:
        text = str(error)
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(text)


def create_router() -> Router:
    router = Router(name="assistant_fallback")
    router.callback_query.register(confirm_callback, F.data.startswith("ai:yes:"))
    router.callback_query.register(confirm_callback, F.data.startswith("ai:no:"))
    router.message.register(voice_fallback, F.voice)
    router.message.register(text_fallback, F.text & ~F.text.startswith("/"))
    return router
