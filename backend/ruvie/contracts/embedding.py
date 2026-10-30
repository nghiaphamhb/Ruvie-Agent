"""Write-only embedding drafts and safe administrator results."""
from datetime import datetime
from pydantic import BaseModel
from ruvie.contracts.llm import OrganizationConnectionDraft, ModelId
from ruvie.contracts.network import NetworkConfig


class EmbeddingConnectionDraft(OrganizationConnectionDraft):
    """Catalog draft uses the same explicit key actions as the reply connection."""


class EmbeddingConnectionRequest(EmbeddingConnectionDraft):
    """Verify/apply require a selected model; dimension is never accepted from clients."""
    model_id: ModelId


class EmbeddingConnectionResponse(BaseModel):
    configured: bool
    base_url: str | None
    has_api_key: bool
    network: NetworkConfig
    model_id: str | None
    dimension: int | None
    distance_metric: str | None
    version: int
    updated_at: datetime | None


class EmbeddingModelInfo(BaseModel):
    id: str
    name: str
    dimension: int | None
    supported: bool
    reason_code: str | None


class EmbeddingCatalogResponse(BaseModel):
    models: list[EmbeddingModelInfo]
    version: int


class EmbeddingVerificationResponse(BaseModel):
    model_id: str
    dimension: int
    distance_metric: str
    compatible: bool
    version: int
