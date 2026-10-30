"""Strict public LLM contracts; credentials are accepted only in admin drafts."""
from datetime import datetime
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, SecretStr, StrictInt, model_validator

from ruvie.contracts.network import NetworkConfig

ModelId = Annotated[str, Field(min_length=1, max_length=4096)]


class OrganizationConnectionDraft(BaseModel):
    """POST verify: URL, explicit key action and version of the edited configuration."""
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    base_url: str = Field(min_length=1, max_length=2048)
    key_action: Literal['keep', 'replace', 'clear']
    api_key: SecretStr | None = Field(default=None, max_length=4096)
    expected_version: StrictInt = Field(ge=0)
    network: NetworkConfig

    @model_validator(mode='after')
    def validate_key_action(self):
        """Reject ambiguous keys; keep/clear must omit api_key entirely."""
        if self.key_action == 'replace':
            if self.api_key is None or not self.api_key.get_secret_value().strip():
                raise ValueError('invalid_llm_request')
        elif 'api_key' in self.model_fields_set:
            raise ValueError('invalid_llm_request')
        return self


class OrganizationConnectionUpdateRequest(OrganizationConnectionDraft):
    """PUT replaces the allowed IDs and their default after a fresh probe."""
    allowed_model_ids: list[ModelId] = Field(min_length=1)
    default_model_id: ModelId

    @model_validator(mode='after')
    def validate_model_policy(self):
        if len(set(self.allowed_model_ids)) != len(self.allowed_model_ids) or self.default_model_id not in self.allowed_model_ids:
            raise ValueError('invalid_llm_request')
        return self


class ModelSelectionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    model_id: ModelId


class ModelInfo(BaseModel):
    id: str
    name: str


class OrganizationConnectionResponse(BaseModel):
    """Administrator metadata; ciphertext and API keys have no public field."""
    configured: bool
    base_url: str | None
    has_api_key: bool
    network: NetworkConfig
    allowed_model_ids: list[str]
    default_model_id: str | None
    version: int
    updated_at: datetime | None


class VerifiedConnectionResponse(BaseModel):
    models: list[ModelInfo]
    version: int


class ConnectionResponse(BaseModel):
    configured: bool
    selected_model_id: str | None
    configuration_version: int


class ModelsResponse(BaseModel):
    models: list[ModelInfo]
    selected_model_id: str | None
    selection_required: bool
    configuration_version: int


class OrganizationModelProbeRequest(OrganizationConnectionDraft):
    """Probe only the administrator-selected default using fixed server text."""
    model_id: ModelId
