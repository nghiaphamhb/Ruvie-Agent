"""Public request contracts for private chat history."""
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class RenameConversation(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=120)
    expected_version: int = Field(strict=True, ge=1)

class RetryTurn(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    request_id: UUID
    model_id: str | None = Field(default=None, min_length=1)

class StopTurn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    attempt_id: UUID
