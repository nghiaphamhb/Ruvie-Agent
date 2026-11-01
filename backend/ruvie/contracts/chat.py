import json
from uuid import UUID
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """Chat JSON accepts a question, request UUID and optional conversation/model IDs."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    request_id: UUID
    conversation_id: UUID | None = None
    message: str = Field(min_length=1)
    model_id: str | None = Field(default=None, min_length=1)


ChatEventType = Literal["accepted", "delta", "citations", "completed", "error"]


@dataclass(frozen=True)
class ChatStreamEvent:
    """Named SSE event with public JSON data, including committed admission IDs."""
    event: ChatEventType
    data: dict[str, object]

    def to_sse(self) -> str:
        """Encode event/data lines; the blank line terminates each SSE message."""
        return f"event: {self.event}\ndata: {json.dumps(self.data, ensure_ascii=False, separators=(',', ':'))}\n\n"
