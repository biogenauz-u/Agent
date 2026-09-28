import asyncio
import json
from typing import Protocol

import httpx
from pydantic import ValidationError

from app.core.config import Settings
from app.modules.assistant.exceptions import (
    AssistantNotConfiguredError,
    AssistantProviderError,
)
from app.modules.assistant.prompts import SYSTEM_PROMPT, user_prompt
from app.modules.assistant.schemas import (
    ACTION_ADAPTER,
    AssistantAction,
    AssistantClarification,
    AssistantRequest,
)


class AssistantModelClient(Protocol):
    async def generate_structured_action(self, request: AssistantRequest) -> dict: ...


class OpenAIModelClient:
    """Provider-only HTTP adapter; it owns no application services or credentials beyond AI key."""

    def __init__(self, settings: Settings, http: httpx.AsyncClient | None = None) -> None:
        if not settings.ai_api_key or not settings.ai_model:
            raise AssistantNotConfiguredError("AI provider is not configured.")
        self.key = settings.ai_api_key
        self.model = settings.ai_model
        self.retries = settings.ai_max_retries
        self.http = http or httpx.AsyncClient(timeout=settings.ai_timeout_seconds)
        self._owned_http = http is None

    async def generate_structured_action(self, request: AssistantRequest) -> dict:
        payload = {
            "model": self.model,
            "input": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": user_prompt(
                        request.text,
                        request.current_datetime.isoformat(),
                        request.timezone,
                        request.context,
                    )
                    + "\nALLOWED_ACTION_SCHEMA_DATA:\n"
                    + json.dumps(ACTION_ADAPTER.json_schema(), separators=(",", ":")),
                },
            ],
            "text": {"format": {"type": "json_object"}},
            "max_output_tokens": 1200,
        }
        for attempt in range(self.retries + 1):
            try:
                response = await self.http.post(
                    "https://api.openai.com/v1/responses",
                    headers={"Authorization": f"Bearer {self.key.get_secret_value()}"},
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
                text = body.get("output_text") or next(
                    part["text"]
                    for item in body.get("output", [])
                    for part in item.get("content", [])
                    if part.get("type") == "output_text"
                )
                decoded = json.loads(text)
                if not isinstance(decoded, dict):
                    raise TypeError
                return decoded
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                status = (
                    exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
                )
                if status in {401, 403}:
                    raise AssistantProviderError(
                        "AI provider authentication or model access failed."
                    ) from None
                if status == 429:
                    raise AssistantProviderError(
                        "AI provider quota or rate limit reached."
                    ) from None
                if status is not None and 400 <= status < 500:
                    raise AssistantProviderError("AI provider rejected the request.") from None
                retryable = status is None or status >= 500
                if attempt >= self.retries or not retryable:
                    raise AssistantProviderError(
                        "AI provider is temporarily unavailable."
                    ) from None
                await asyncio.sleep(min(2**attempt, 4))
            except (KeyError, TypeError, ValueError, StopIteration):
                raise AssistantProviderError("AI provider returned an invalid response.") from None
        raise AssistantProviderError("AI provider is unavailable.")

    async def close(self) -> None:
        if self._owned_http:
            await self.http.aclose()


class AssistantParser:
    def __init__(self, client: AssistantModelClient) -> None:
        self.client = client

    async def parse(self, request: AssistantRequest) -> AssistantAction | AssistantClarification:
        raw = await self.client.generate_structured_action(request)
        try:
            action = ACTION_ADAPTER.validate_python(raw)
        except ValidationError:
            return AssistantClarification(question="So'rovni aniqroq yozing.")
        if action.action.value == "UNKNOWN":
            return AssistantClarification(question=action.response)
        return action
