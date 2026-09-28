from datetime import date
from io import BytesIO

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from app.bot.context import BotContext
from app.bot.keyboards.notebook import (
    attachment_files,
    confirmation,
    finish_attachments,
    note_list,
)
from app.database.models.notebook import AttachmentType
from app.modules.notebook.exceptions import NotebookError, NotebookValidationError
from app.modules.notebook.runtime import NotebookRuntime
from app.modules.notebook.schemas import AttachmentInput
from app.modules.notebook.utils import attachment_type


class NotebookFlow(StatesGroup):
    content = State()
    title = State()
    date = State()
    project = State()
    tags = State()
    attach = State()


def runtime(context: BotContext) -> NotebookRuntime:
    if context.notebook is None:
        raise NotebookError("Notebook storage sozlanmagan.")
    return context.notebook


def summary(note) -> str:
    project = note.project.name if note.project else "-"
    tags = " ".join(f"#{tag.name}" for tag in note.tags) or "-"
    body = note.content if len(note.content) <= 3200 else note.content[:3200] + "..."
    attachments = "\n".join(
        f"- {item.original_name} [attachment {item.id}]" for item in note.attachments
    ) or "-"
    return (
        f"Notebook #{note.id}\nSana: {note.entry_date:%d.%m.%Y}\n"
        f"Project: {project}\nTags: {tags}\n\n{body}\n\nFayllar:\n{attachments}"
    )


async def menu(message: Message, app_context: BotContext) -> None:
    runtime(app_context)
    await message.answer(
        "Notebook\n\n/note - yangi yozuv\n/notes - oxirgi yozuvlar\n"
        "/note_today\n/note_date DD.MM.YYYY\n/note_project ID\n"
        "/note_tag TAG\n/note_search MATN\n/note_attach NOTE_ID\n"
        "/note_edit ID MATN\n/note_delete ID\n/notebook_projects\n/notebook_tags"
    )


async def start_note(message: Message, state: FSMContext, app_context: BotContext) -> None:
    notebook = runtime(app_context)
    command_text = (message.text or "").partition(" ")[2].strip()
    if not command_text:
        await state.set_state(NotebookFlow.content)
        await message.answer("Yozuv matnini kiriting. /cancel bilan bekor qiling.")
        return
    token = await notebook.actions.prepare(
        "create", {"content": command_text, "entry_date": notebook.service.today().isoformat()}
    )
    await message.answer(
        f"Yangi yozuv\nSana: {notebook.service.today():%d.%m.%Y}\n\n{command_text}\n\nSaqlansinmi?",
        reply_markup=confirmation(token),
    )


async def capture_content(message: Message, state: FSMContext, app_context: BotContext) -> None:
    content = (message.text or "").strip()
    if not content:
        await message.answer("Matn bo'sh bo'lmasligi kerak.")
        return
    runtime(app_context)
    await state.update_data(content=content)
    await state.set_state(NotebookFlow.title)
    await message.answer("Sarlavha kiriting yoki /skip.")


async def capture_title(message: Message, state: FSMContext) -> None:
    title = None if (message.text or "").startswith("/skip") else (message.text or "").strip()
    await state.update_data(title=title or None)
    await state.set_state(NotebookFlow.date)
    await message.answer("Sana: DD.MM.YYYY yoki bugun uchun /skip.")


async def capture_date(message: Message, state: FSMContext, app_context: BotContext) -> None:
    notebook = runtime(app_context)
    raw = (message.text or "").strip()
    if raw.startswith("/skip"):
        entry_date = notebook.service.today()
    else:
        try:
            day, month, year = (int(part) for part in raw.split("."))
            entry_date = date(year, month, day)
        except (TypeError, ValueError):
            await message.answer("Sana noto'g'ri. DD.MM.YYYY yoki /skip yuboring.")
            return
    await state.update_data(entry_date=entry_date.isoformat())
    await state.set_state(NotebookFlow.project)
    projects = await notebook.service.projects()
    options = "\n".join(f"{item.id} - {item.name}" for item in projects)
    await message.answer((options + "\n\n" if options else "") + "Project ID yoki /skip.")


async def capture_project(message: Message, state: FSMContext, app_context: BotContext) -> None:
    raw = (message.text or "").strip()
    if raw.startswith("/skip"):
        project_id = None
    elif raw.isdigit() and any(
        item.id == int(raw) for item in await runtime(app_context).service.projects()
    ):
        project_id = int(raw)
    else:
        await message.answer("Active project ID yoki /skip yuboring.")
        return
    await state.update_data(project_id=project_id)
    await state.set_state(NotebookFlow.tags)
    await message.answer("Taglarni vergul bilan kiriting yoki /skip.")


async def capture_tags(message: Message, state: FSMContext, app_context: BotContext) -> None:
    raw = (message.text or "").strip()
    tags = [] if raw.startswith("/skip") else [item.strip() for item in raw.split(",") if item.strip()]
    data = await state.get_data()
    data["tags"] = tags
    token = await runtime(app_context).actions.prepare("create", data)
    await state.clear()
    content = str(data["content"])
    project = data.get("project_id") or "-"
    tag_text = " ".join(f"#{tag.lstrip('#')}" for tag in tags) or "-"
    await message.answer(
        f"Yangi yozuv\nSana: {date.fromisoformat(data['entry_date']):%d.%m.%Y}\n"
        f"Project ID: {project}\nTags: {tag_text}\n\n{content}\n\nSaqlansinmi?",
        reply_markup=confirmation(token),
    )


async def confirm_action(callback: CallbackQuery, app_context: BotContext) -> None:
    notebook = runtime(app_context)
    token = (callback.data or "").rsplit(":", 1)[-1]
    if ":no:" in (callback.data or ""):
        await notebook.actions.cancel(token)
        text = "Bekor qilindi."
    else:
        text, _ = await notebook.actions.confirm(token)
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(text)


async def send_notes(message: Message, notes) -> None:
    if not notes:
        await message.answer("Yozuvlar topilmadi.")
        return
    lines, buttons = [], []
    for index, note in enumerate(notes, 1):
        label = note.title or note.content.replace("\n", " ")[:45]
        project = f" - {note.project.name}" if note.project else ""
        lines.append(f"{index}. {note.entry_date:%d.%m.%Y}{project} - {label}")
        buttons.append((note.id, f"{note.entry_date:%d.%m} - {label}"))
    await message.answer("Oxirgi yozuvlar:\n\n" + "\n".join(lines), reply_markup=note_list(buttons))


async def recent(message: Message, app_context: BotContext) -> None:
    await send_notes(message, await runtime(app_context).service.recent())


async def today(message: Message, app_context: BotContext) -> None:
    service = runtime(app_context).service
    await send_notes(message, await service.recent(entry_date=service.today()))


async def by_date(message: Message, app_context: BotContext) -> None:
    raw = (message.text or "").partition(" ")[2].strip()
    try:
        day, month, year = (int(part) for part in raw.split("."))
        requested = date(year, month, day)
    except (ValueError, TypeError):
        await message.answer("Format: /note_date DD.MM.YYYY")
        return
    await send_notes(message, await runtime(app_context).service.recent(entry_date=requested))


async def by_project(message: Message, app_context: BotContext) -> None:
    try:
        project_id = int((message.text or "").partition(" ")[2])
    except ValueError:
        await message.answer("Format: /note_project PROJECT_ID")
        return
    await send_notes(message, await runtime(app_context).service.recent(project_id=project_id))


async def by_tag(message: Message, app_context: BotContext) -> None:
    tag = (message.text or "").partition(" ")[2].strip()
    if not tag:
        await message.answer("Format: /note_tag TAG")
        return
    await send_notes(message, await runtime(app_context).service.recent(tag=tag))


async def search(message: Message, app_context: BotContext) -> None:
    query = (message.text or "").partition(" ")[2].strip()
    if not query:
        await message.answer("Format: /note_search QIDIRUV")
        return
    await send_notes(message, await runtime(app_context).service.search(query))


async def view(callback: CallbackQuery, app_context: BotContext) -> None:
    note = await runtime(app_context).service.get_note(int((callback.data or "").rsplit(":", 1)[-1]))
    await callback.answer()
    if callback.message:
        files = [
            (item.id, item.original_name)
            for item in note.attachments
            if item.source_type != AttachmentType.LINK
        ]
        await callback.message.answer(summary(note), reply_markup=attachment_files(files))


async def edit(message: Message, app_context: BotContext) -> None:
    parts = (message.text or "").split(maxsplit=3)
    if len(parts) < 3 or not parts[1].isdigit():
        await message.answer("Format: /note_edit ID content|title|date|project|tags VALUE")
        return
    if len(parts) == 3:
        values = {"content": parts[2]}
    else:
        field, raw = parts[2].casefold(), parts[3].strip()
        if field in {"content", "title"}:
            values = {field: raw}
        elif field == "date":
            try:
                day, month, year = (int(part) for part in raw.split("."))
                values = {"entry_date": date(year, month, day).isoformat()}
            except (TypeError, ValueError):
                await message.answer("Date formati: DD.MM.YYYY")
                return
        elif field == "project" and raw.isdigit():
            values = {"project_id": int(raw)}
        elif field == "tags":
            values = {"tags": [item.strip() for item in raw.split(",") if item.strip()]}
        else:
            await message.answer("Field: content, title, date, project yoki tags.")
            return
    token = await runtime(app_context).actions.prepare(
        "update", {"id": int(parts[1]), **values}
    )
    await message.answer("Yozuv yangilansinmi?", reply_markup=confirmation(token))


async def delete(message: Message, app_context: BotContext) -> None:
    raw = (message.text or "").partition(" ")[2].strip()
    if not raw.isdigit():
        await message.answer("Format: /note_delete ID")
        return
    token = await runtime(app_context).actions.prepare("delete", {"id": int(raw)})
    await message.answer("Yozuv soft-delete qilinsinmi?", reply_markup=confirmation(token))


async def projects(message: Message, app_context: BotContext) -> None:
    service = runtime(app_context).service
    argument = (message.text or "").partition(" ")[2].strip()
    if argument.casefold().startswith("create "):
        project = await service.create_project(argument[7:].strip())
        await message.answer(f"Project yaratildi: {project.name} [ID {project.id}]")
        return
    if argument.casefold().startswith("deactivate "):
        raw_id = argument[11:].strip()
        if not raw_id.isdigit():
            await message.answer("Format: /notebook_projects deactivate ID")
            return
        await service.deactivate_project(int(raw_id))
        await message.answer("Project deaktivatsiya qilindi.")
        return
    rows = await service.projects()
    text = "\n".join(f"- {row.name} [ID {row.id}]" for row in rows) or "Projectlar yo'q."
    await message.answer(
        text
        + "\n\nYaratish: /notebook_projects create NOM"
        + "\nDeaktivatsiya: /notebook_projects deactivate ID"
    )


async def tags(message: Message, app_context: BotContext) -> None:
    rows = await runtime(app_context).service.tags()
    await message.answer(" ".join(f"#{row.name}" for row in rows) or "Taglar yo'q.")


async def start_attach(message: Message, state: FSMContext, app_context: BotContext) -> None:
    raw = (message.text or "").partition(" ")[2].strip()
    if not raw.isdigit():
        await message.answer("Format: /note_attach NOTE_ID")
        return
    await runtime(app_context).service.get_note(int(raw), audit=False)
    await state.set_state(NotebookFlow.attach)
    await state.update_data(note_id=int(raw))
    await message.answer(
        "Fayl, image, voice yoki http/https link yuboring. Bir nechta yuborish mumkin.",
        reply_markup=finish_attachments(),
    )


async def collect_attachment(
    message: Message, state: FSMContext, app_context: BotContext, bot: Bot
) -> None:
    service = runtime(app_context).service
    note_id = int((await state.get_data())["note_id"])
    if message.text:
        await service.add_link(note_id, message.text)
        await message.answer("Link qo'shildi.", reply_markup=finish_attachments())
        return
    item = message.voice or message.document or message.video or (
        message.photo[-1] if message.photo else None
    )
    if item is None:
        await message.answer("Qo'llab-quvvatlanadigan fayl yoki link yuboring.")
        return
    size = item.file_size or 0
    if size > service.storage.max_bytes:
        raise NotebookValidationError("Attachment exceeds configured size limit.")
    buffer = BytesIO()
    await bot.download(item, destination=buffer)
    mime = getattr(item, "mime_type", None) or (
        "image/jpeg" if message.photo else "audio/ogg" if message.voice else "application/octet-stream"
    )
    name = getattr(item, "file_name", None) or (
        "voice.ogg" if message.voice else "image.jpg" if message.photo else "attachment"
    )
    await service.add_file(
        note_id,
        buffer.getvalue(),
        AttachmentInput(
            original_name=name,
            mime_type=mime,
            source_type=attachment_type(mime, voice=message.voice is not None),
            telegram_file_id=item.file_id,
            telegram_file_unique_id=item.file_unique_id,
            width=getattr(item, "width", None),
            height=getattr(item, "height", None),
            duration_seconds=getattr(item, "duration", None),
        ),
    )
    buffer.close()
    await message.answer("Fayl shifrlab qo'shildi.", reply_markup=finish_attachments())


async def finish_attach(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    if callback.message:
        await callback.message.edit_text("Attachment capture tugadi.")


async def send_attachment(
    callback: CallbackQuery, app_context: BotContext, bot: Bot
) -> None:
    attachment_id = int((callback.data or "").rsplit(":", 1)[-1])
    async with runtime(app_context).service.attachment_temp(attachment_id) as (path, name):
        await bot.send_document(callback.from_user.id, BufferedInputFile(path.read_bytes(), name))
    await callback.answer()


async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Bekor qilindi.")


def create_router() -> Router:
    router = Router(name="notebook")
    router.message.register(menu, Command("notebook"))
    router.message.register(start_note, Command("note"))
    router.message.register(recent, Command("notes"))
    router.message.register(today, Command("note_today"))
    router.message.register(by_date, Command("note_date"))
    router.message.register(by_project, Command("note_project"))
    router.message.register(by_tag, Command("note_tag"))
    router.message.register(search, Command("note_search"))
    router.message.register(edit, Command("note_edit"))
    router.message.register(delete, Command("note_delete"))
    router.message.register(start_attach, Command("note_attach"))
    router.message.register(projects, Command("notebook_projects"))
    router.message.register(tags, Command("notebook_tags"))
    router.callback_query.register(confirm_action, F.data.startswith("nb:yes:"))
    router.callback_query.register(confirm_action, F.data.startswith("nb:no:"))
    router.callback_query.register(view, F.data.startswith("nb:view:"))
    router.callback_query.register(send_attachment, F.data.startswith("nb:file:"))
    router.callback_query.register(finish_attach, F.data.startswith("nb:attach:"))
    router.message.register(cancel, Command("cancel"), StateFilter(NotebookFlow))
    router.message.register(capture_content, StateFilter(NotebookFlow.content))
    router.message.register(capture_title, StateFilter(NotebookFlow.title))
    router.message.register(capture_date, StateFilter(NotebookFlow.date))
    router.message.register(capture_project, StateFilter(NotebookFlow.project))
    router.message.register(capture_tags, StateFilter(NotebookFlow.tags))
    router.message.register(collect_attachment, StateFilter(NotebookFlow.attach))
    return router
