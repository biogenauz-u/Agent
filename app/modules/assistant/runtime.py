from app.core.config import Settings
from app.modules.assistant.audit import AssistantAudit
from app.modules.assistant.confirmation import MemoryPendingActionStore, RedisPendingActionStore
from app.modules.assistant.context import AssistantContextStore
from app.modules.assistant.executor import AssistantActionExecutor
from app.modules.assistant.parser import AssistantParser, OpenAIModelClient
from app.modules.assistant.router import AssistantRouter
from app.modules.voice.transcriber import OpenAISpeechToTextClient, VoiceTranscriber


class AssistantRuntime:
    def __init__(self, settings: Settings, application) -> None:
        assert settings.telegram_owner_id is not None
        self.model = OpenAIModelClient(settings)
        self.stt = None
        if settings.stt_model and (settings.stt_api_key or settings.ai_api_key):
            self.stt_client = OpenAISpeechToTextClient(settings)
            self.stt = VoiceTranscriber(self.stt_client, settings.stt_max_file_size_mb)
        else:
            self.stt_client = None
        pending = (
            RedisPendingActionStore(
                application.redis.client, settings.redis_key_prefix, 900
            )
            if application.redis
            else MemoryPendingActionStore(900)
        )
        self.router = AssistantRouter(
            settings.telegram_owner_id,
            settings.timezone,
            AssistantParser(self.model),
            AssistantActionExecutor(application),
            pending,
            AssistantContextStore(
                settings.assistant_context_ttl_seconds,
                settings.assistant_context_max_messages,
            ),
            AssistantAudit(application.database, settings.telegram_owner_id),
            settings.ai_action_confidence_threshold,
            settings.ai_max_requests_per_minute,
        )

    async def close(self) -> None:
        await self.model.close()
        if self.stt_client:
            await self.stt_client.close()
