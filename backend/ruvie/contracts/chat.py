import json
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """Chat JSON accepts {message, model_id?}; provider credentials and scope are forbidden."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    message: str = Field(min_length=1)
    model_id: str | None = Field(default=None, min_length=1)


ChatEventType = Literal["delta", "citations", "completed", "error"]


@dataclass(frozen=True)
class ChatStreamEvent:
    """Named SSE event with JSON data: delta, citations, completed or error."""
    event: ChatEventType
    data: dict[str, object]

    def to_sse(self) -> str:
        """Encode event/data lines; the blank line terminates each SSE message."""
        return f"event: {self.event}\ndata: {json.dumps(self.data, ensure_ascii=False, separators=(',', ':'))}\n\n"
