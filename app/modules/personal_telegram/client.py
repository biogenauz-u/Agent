from collections.abc import Awaitable, Callable
from typing import Any

from telethon import TelegramClient, events
from telethon.errors import (
    ApiIdPublishedFloodError,
    ChatWriteForbiddenError,
    FloodWaitError,
    PeerFloodError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    PhoneNumberBannedError,
    PhoneNumberFloodError,
    PhoneNumberInvalidError,
    RPCError,
    SendCodeUnavailableError,
    SessionPasswordNeededError,
    UserPrivacyRestrictedError,
)
from telethon.sessions import StringSession

from app.core.config import Settings
from app.modules.personal_telegram.exceptions import (
    PersonalTelegramAuthenticationError,
    PersonalTelegramCodeError,
    PersonalTelegramConfigurationError,
    PersonalTelegramFloodWaitError,
    PersonalTelegramPasswordRequired,
    PersonalTelegramUnavailableError,
    PersonalTelegramWriteForbiddenError,
)
from app.modules.personal_telegram.schemas import PersonalAccount

IncomingHandler = Callable[[Any], Awaitable[None]]


class PersonalTelegramClient:
    """Thin Telethon adapter. Construction and module import perform no network I/O."""

    def __init__(self, settings: Settings, session: str = "") -> None:
        if settings.telegram_api_id is None:
            raise PersonalTelegramConfigurationError("TELEGRAM_API_ID is required.")
        if settings.telegram_api_hash is None:
            raise PersonalTelegramConfigurationError("TELEGRAM_API_HASH is required.")
        self._api_id = settings.telegram_api_id
        self._api_hash = settings.telegram_api_hash.get_secret_value()
        self._session = session
        self._client: TelegramClient | None = None
        self._handler: IncomingHandler | None = None
        self._adapter: IncomingHandler | None = None
        self._phone_code_hash: str | None = None

    def __repr__(self) -> str:
        return "PersonalTelegramClient(configured=True)"

    @property
    def raw(self) -> TelegramClient:
        if self._client is None:
            raise PersonalTelegramUnavailableError("Personal Telegram client is not connected.")
        return self._client

    async def connect(self) -> None:
        if self._client is None:
            self._client = TelegramClient(
                StringSession(self._session),
                self._api_id,
                self._api_hash,
                auto_reconnect=True,
                connection_retries=3,
                retry_delay=2,
                flood_sleep_threshold=0,
            )
        try:
            await self._client.connect()
        except (OSError, ConnectionError, RPCError):
            raise PersonalTelegramUnavailableError(
                "Personal Telegram is temporarily unavailable."
            ) from None

    async def disconnect(self) -> None:
        if self._client is not None:
            await self._client.disconnect()
            self._client = None
        self._phone_code_hash = None

    async def is_authorized(self) -> bool:
        return bool(await self.raw.is_user_authorized())

    async def get_me(self) -> PersonalAccount:
        me = await self.raw.get_me()
        if me is None:
            raise PersonalTelegramAuthenticationError("Personal Telegram session is unauthorized.")
        return PersonalAccount(id=int(me.id), username=getattr(me, "username", None))

    @staticmethod
    def _delivery_name(result: Any) -> str:
        name = type(getattr(result, "type", None)).__name__.lower()
        if "sms" in name:
            return "sms"
        if "call" in name:
            return "call"
        if "email" in name:
            return "email"
        if "fragment" in name:
            return "fragment"
        return "telegram_app"

    async def send_code_request(self, phone: str) -> str:
        try:
            result = await self.raw.send_code_request(phone)
            phone_code_hash = getattr(result, "phone_code_hash", None)
            if not isinstance(phone_code_hash, str) or not phone_code_hash:
                raise PersonalTelegramAuthenticationError(
                    "Telegram login request did not return a verification token."
                )
            self._phone_code_hash = phone_code_hash
            return self._delivery_name(result)
        except FloodWaitError as error:
            raise PersonalTelegramFloodWaitError(error.seconds) from None
        except PhoneNumberInvalidError:
            raise PersonalTelegramAuthenticationError(
                "Telegram telefon raqamini noto‘g‘ri deb rad etdi. Xalqaro formatni tekshiring."
            ) from None
        except PhoneNumberBannedError:
            raise PersonalTelegramAuthenticationError(
                "Telegram bu telefon raqamidan login qilishni bloklagan."
            ) from None
        except PhoneNumberFloodError:
            raise PersonalTelegramAuthenticationError(
                "Bu telefon raqami uchun juda ko‘p login kodi so‘ralgan. Keyinroq urinib ko‘ring."
            ) from None
        except ApiIdPublishedFloodError:
            raise PersonalTelegramAuthenticationError(
                "Telegram API ID ni xavfsizlik sababli bloklagan. Yangi API ilovasi kerak."
            ) from None
        except SendCodeUnavailableError:
            raise PersonalTelegramAuthenticationError(
                "Telegram hozir login kodini yubora olmayapti. Keyinroq urinib ko‘ring."
            ) from None
        except RPCError:
            raise PersonalTelegramAuthenticationError("Telegram login request failed.") from None

    async def sign_in_code(self, phone: str, code: str) -> bool:
        normalized_code = "".join(character for character in code if character.isdigit())
        if not normalized_code or self._phone_code_hash is None:
            raise PersonalTelegramCodeError(
                "Telegram login flow expired. Start /telegram_connect again."
            )
        try:
            await self.raw.sign_in(
                phone=phone,
                code=normalized_code,
                phone_code_hash=self._phone_code_hash,
            )
            self._phone_code_hash = None
            return True
        except SessionPasswordNeededError:
            raise PersonalTelegramPasswordRequired(
                "Telegram two-step verification password is required."
            ) from None
        except (PhoneCodeInvalidError, PhoneCodeExpiredError):
            raise PersonalTelegramCodeError("Telegram login code is invalid or expired.") from None
        except FloodWaitError as error:
            raise PersonalTelegramFloodWaitError(error.seconds) from None
        except RPCError:
            raise PersonalTelegramAuthenticationError("Telegram login failed safely.") from None

    async def sign_in_password(self, password: str) -> bool:
        try:
            await self.raw.sign_in(password=password)
            return True
        except FloodWaitError as error:
            raise PersonalTelegramFloodWaitError(error.seconds) from None
        except RPCError:
            raise PersonalTelegramAuthenticationError(
                "Telegram two-step verification failed."
            ) from None

    def session_string(self) -> str:
        value = self.raw.session.save()
        if not isinstance(value, str) or not value:
            raise PersonalTelegramAuthenticationError("Telegram session could not be created.")
        return value

    async def get_recent_private_messages(self, limit: int) -> list[Any]:
        messages: list[Any] = []
        dialogs = await self.raw.get_dialogs(limit=min(limit * 2, 50))
        for dialog in dialogs:
            entity = getattr(dialog, "entity", None)
            if not getattr(dialog, "is_user", False) or getattr(entity, "bot", False):
                continue
            rows = await self.raw.get_messages(entity, limit=min(5, limit - len(messages)))
            messages.extend(row for row in rows if not getattr(row, "out", False))
            if len(messages) >= limit:
                break
        return sorted(messages, key=lambda row: row.date, reverse=True)[:limit]

    async def search_messages(self, query: str, limit: int) -> list[Any]:
        return [row async for row in self.raw.iter_messages(None, search=query, limit=limit)]

    async def send_message(self, chat_id: int, text: str, reply_to: int) -> int:
        try:
            result = await self.raw.send_message(chat_id, text, reply_to=reply_to)
            return int(result.id)
        except FloodWaitError as error:
            raise PersonalTelegramFloodWaitError(error.seconds) from None
        except (PeerFloodError, ChatWriteForbiddenError, UserPrivacyRestrictedError):
            raise PersonalTelegramWriteForbiddenError(
                "Bu suhbatga xabar yuborib bo‘lmaydi."
            ) from None
        except (OSError, ConnectionError, RPCError):
            raise PersonalTelegramUnavailableError(
                "Personal Telegram xabarni yubora olmadi."
            ) from None

    def register_incoming_handler(self, handler: IncomingHandler) -> None:
        self._handler = handler

        async def adapter(event: Any) -> None:
            await handler(event)

        self._adapter = adapter
        self.raw.add_event_handler(adapter, events.NewMessage(incoming=True))

    def remove_incoming_handler(self) -> None:
        if self._adapter is not None and self._client is not None:
            self._client.remove_event_handler(self._adapter)
        self._handler = None
        self._adapter = None
