from pydantic import BaseModel, Field


class TranscriptionResult(BaseModel):
    text: str = Field(min_length=1, max_length=20_000)
    detected_language: str | None = None
    duration: float | None = Field(default=None, ge=0)
    confidence: float | None = Field(default=None, ge=0, le=1)
