import json
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    message: str = Field(min_length=1)


ChatEventType = Literal["delta", "citations", "completed", "error"]


@dataclass(frozen=True)
class ChatStreamEvent:
    event: ChatEventType
    data: dict[str, object]

    def to_sse(self) -> str:
        return f"event: {self.event}\ndata: {json.dumps(self.data, ensure_ascii=False, separators=(',', ':'))}\n\n"
