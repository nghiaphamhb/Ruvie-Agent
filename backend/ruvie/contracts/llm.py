from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class ConnectionUpdateRequest(BaseModel):
    """Connection JSON: {base_url, api_key?}; omitted key, empty key and URL changes differ."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    base_url: str = Field(min_length=1, max_length=2048)
    # SecretStr masks repr/log output; field presence distinguishes omitted from empty.
    api_key: SecretStr = Field(default=SecretStr(""), max_length=4096)


class ModelSelectionRequest(BaseModel):
    """Selection JSON: {model_id}; the service checks it against the current catalog."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    model_id: str = Field(min_length=1, max_length=4096)


class ModelInfo(BaseModel):
    """Normalized provider model: {id, name}, with ID used when name is missing."""
    id: str
    name: str


class ConnectionResponse(BaseModel):
    """Public metadata; has_api_key reports presence without revealing the key."""
    source: Literal["personal", "server", "none"]
    base_url: str | None
    has_api_key: bool
    selected_model_id: str | None


class ModelsResponse(BaseModel):
    """Fresh models/chosen ID; selection_required is true when a saved model is missing."""
    models: list[ModelInfo]
    selected_model_id: str | None
    selection_required: bool
