import asyncio
import os
import tempfile
from pathlib import Path
from typing import Protocol

import httpx

from app.core.config import Settings
from app.modules.voice.exceptions import (
    VoiceFileTooLargeError,
    VoiceNotConfiguredError,
    VoiceProviderError,
)
from app.modules.voice.schemas import TranscriptionResult


class SpeechToTextClient(Protocol):
    async def transcribe(
        self, path: Path, language_hint: str | None = None
    ) -> TranscriptionResult: ...


class OpenAISpeechToTextClient:
    def __init__(self, settings: Settings, http: httpx.AsyncClient | None = None) -> None:
        key = settings.stt_api_key or settings.ai_api_key
        if not key or not settings.stt_model:
            raise VoiceNotConfiguredError("STT provider is not configured.")
        self.key, self.model = key, settings.stt_model
        self.http = http or httpx.AsyncClient(timeout=settings.stt_timeout_seconds)
        self._owned = http is None

    async def transcribe(self, path: Path, language_hint: str | None = None) -> TranscriptionResult:
        try:
            content = await asyncio.to_thread(path.read_bytes)
            data = {"model": self.model, "temperature": "0"}
            if language_hint == "uz":
                data["prompt"] = (
                    "Audio o‘zbek tilida. O‘zbek lotin yozuvida aynan transkripsiya qil, "
                    "tarjima qilma va turkcha yozma. Sana, vaqt, raqam va ismlarni aniq saqla. "
                    "Ko‘p uchraydigan so‘zlar: bugun, ertaga, indinga, soat, daqiqa, eslat, "
                    "eslatma, shifokor, uchrashuv, vazifa, qo‘ng‘iroq, kalendar. "
                    "Masalan: Ertaga soat 10:00 da shifokorga borishni eslat."
                )
            elif language_hint:
                data["language"] = language_hint
            response = await self.http.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {self.key.get_secret_value()}"},
                data=data,
                files={"file": (path.name, content, "audio/ogg")},
            )
            response.raise_for_status()
            body = response.json()
            return TranscriptionResult(
                text=body["text"],
                detected_language=body.get("language"),
                duration=body.get("duration"),
            )
        except (httpx.HTTPError, KeyError, ValueError):
            raise VoiceProviderError("Voice transcription failed.") from None

    async def close(self) -> None:
        if self._owned:
            await self.http.aclose()


class VoiceTranscriber:
    def __init__(self, client: SpeechToTextClient, max_size_mb: int) -> None:
        self.client, self.max_bytes = client, max_size_mb * 1024 * 1024

    async def transcribe_bytes(
        self, content: bytes, language_hint: str | None = None
    ) -> TranscriptionResult:
        if len(content) > self.max_bytes:
            raise VoiceFileTooLargeError("Voice message exceeds configured size limit.")
        fd, name = tempfile.mkstemp(prefix="assistant-voice-", suffix=".ogg")
        path = Path(name)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
            return await self.client.transcribe(path, language_hint)
        finally:
            await asyncio.to_thread(path.unlink, missing_ok=True)
