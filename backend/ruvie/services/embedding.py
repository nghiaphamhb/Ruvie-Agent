"""Embedding configuration uses fresh immutable snapshots and atomic audited writes."""
from dataclasses import dataclass, field
import math
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from ruvie.adapters.embedding import OpenAICompatibleQueryEmbedder
from ruvie.adapters.llm import normalize_llm_url
from ruvie.config import EmbeddingProfile, EmbeddingProviderSettings
from ruvie.contracts.embedding import (
    EmbeddingConnectionDraft, EmbeddingConnectionRequest, EmbeddingConnectionResponse,
    EmbeddingCatalogResponse, EmbeddingVerificationResponse,
)
from ruvie.models import OrganizationEmbeddingSettings
from ruvie.services.admin import AdminAccountService
from ruvie.services.audit import AuditEventWriter
from ruvie.services.llm import LlmConfigurationConflict
from ruvie.services.llm_secrets import LlmSecretStore


class EmbeddingUnavailableError(RuntimeError):
    """Safe embedding failure, without provider messages or credentials."""
    def __init__(self, code='embedding_settings_unavailable'):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class EmbeddingSnapshot:
    """Values copied out of the transaction before network I/O."""
    version: int
    base_url: str | None
    ciphertext: str | None = field(repr=False)
    model_id: str | None
    dimension: int | None
    distance_metric: str | None
    updated_at: object


class EmbeddingConnectionService:
    """Admin catalog/probe/apply and operation-scoped runtime resolution from PostgreSQL."""
    def __init__(self, session, settings):
        self.session, self.settings = session, settings

    def _snapshot(self):
        row = self.session.scalar(select(OrganizationEmbeddingSettings).where(
            OrganizationEmbeddingSettings.id == 1).execution_options(populate_existing=True))
        if row is None:
            raise EmbeddingUnavailableError()
        return EmbeddingSnapshot(row.version, row.base_url, row.api_key_ciphertext,
                                 row.model_id, row.dimension, row.distance_metric, row.updated_at)

    def _secrets(self):
        return LlmSecretStore(self.settings.llm_settings_encryption_key)

    @staticmethod
    def _metadata(snapshot):
        return EmbeddingConnectionResponse(configured=snapshot.version > 0,
            base_url=snapshot.base_url, has_api_key=snapshot.ciphertext is not None,
            model_id=snapshot.model_id, dimension=snapshot.dimension,
            distance_metric=snapshot.distance_metric, version=snapshot.version, updated_at=snapshot.updated_at)

    def get_organization(self, actor_id):
        """Read safe metadata after checking current database-backed administrator rights."""
        AdminAccountService(self.session).require_admin(actor_id)
        return self._metadata(self._snapshot())

    def _adapter(self, provider):
        return OpenAICompatibleQueryEmbedder(provider, EmbeddingProfile('baai/bge-m3',1024,'cosine'),
            allowed_local_origins=self.settings.llm_allowed_local_origins,
            proxy_url=self.settings.embedding_proxy_url)

    def _draft_provider(self, actor_id, body):
        AdminAccountService(self.session).require_admin(actor_id)
        snapshot = self._snapshot()
        if body.expected_version != snapshot.version:
            raise LlmConfigurationConflict()
        url = normalize_llm_url(body.base_url, self.settings.llm_allowed_local_origins)
        if body.key_action == 'keep':
            if snapshot.version == 0 or url != snapshot.base_url:
                raise ValueError('invalid_embedding_request')
            key = self._secrets().decrypt(snapshot.ciphertext)
        elif body.key_action == 'replace':
            key = body.api_key.get_secret_value().strip()
        else:
            key = ''
        self.session.rollback()
        return snapshot, EmbeddingProviderSettings(url, api_key=key)

    def _recheck(self, actor_id, version):
        AdminAccountService(self.session).require_admin(actor_id)
        if self._snapshot().version != version:
            raise LlmConfigurationConflict()

    def catalog(self, actor_id, command):
        """GET the draft provider's embedding catalog without persisting any draft values."""
        body = EmbeddingConnectionDraft.model_validate(command.model_dump(exclude_unset=True))
        snapshot, provider = self._draft_provider(actor_id, body)
        models = self._adapter(provider).list_models()
        self._recheck(actor_id, snapshot.version)
        return EmbeddingCatalogResponse(models=models, version=snapshot.version)

    def _probe(self, provider, model_id):
        if model_id != 'baai/bge-m3':
            raise ValueError('embedding_model_unsupported')
        # Probe uses fixed text, never a document or employee message.
        try:
            vector = self._adapter(provider).embed_query('Ruvie embedding connection test')
        except ValueError:
            raise ValueError('embedding_dimension_unsupported') from None
        if len(vector) != 1024 or any(isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) for value in vector):
            raise ValueError('embedding_dimension_unsupported')

    def verify_organization(self, actor_id, command):
        """Probe a draft and recheck authority/version; verification never saves it."""
        body = EmbeddingConnectionRequest.model_validate(command.model_dump(exclude_unset=True))
        snapshot, provider = self._draft_provider(actor_id, body)
        self._probe(provider, body.model_id)
        self._recheck(actor_id,snapshot.version)
        return EmbeddingVerificationResponse(model_id=body.model_id, dimension=1024,
            distance_metric='cosine', compatible=True, version=snapshot.version)

    def apply_organization(self, actor_id, command):
        """Probe again, then CAS configuration and audit under one transaction."""
        body = EmbeddingConnectionRequest.model_validate(command.model_dump(exclude_unset=True))
        snapshot, provider = self._draft_provider(actor_id, body)
        self._probe(provider, body.model_id)
        ciphertext = self._secrets().encrypt(provider.api_key)
        try:
            AdminAccountService(self.session).require_admin(actor_id, lock=True)
            changed = self.session.execute(update(OrganizationEmbeddingSettings).where(
                OrganizationEmbeddingSettings.id == 1,
                OrganizationEmbeddingSettings.version == snapshot.version,
            ).values(version=snapshot.version+1, base_url=provider.base_url,
                api_key_ciphertext=ciphertext, model_id=body.model_id, dimension=1024,
                distance_metric='cosine',updated_by=actor_id))
            if changed.rowcount != 1:
                raise LlmConfigurationConflict()
            AuditEventWriter.append(self.session, actor_id, action='embedding.organization_settings.update',
                resource_type='organization_embedding',resource_id='1',outcome='allow',
                reason=f'version:{snapshot.version}->{snapshot.version+1};profile:baai/bge-m3/1024/cosine;key:{body.key_action}')
            result = self._metadata(self._snapshot())
            self.session.commit()
            return result
        except SQLAlchemyError:
            self.session.rollback()
            raise EmbeddingUnavailableError() from None
        except Exception:
            self.session.rollback()
            raise

    def resolve_embedder(self):
        """Freeze URL/key/profile for one request or claimed job; never use environment fallback."""
        snapshot = self._snapshot()
        if snapshot.version == 0:
            raise EmbeddingUnavailableError('embedding_not_configured')
        provider = EmbeddingProviderSettings(snapshot.base_url, api_key=self._secrets().decrypt(snapshot.ciphertext))
        self.session.rollback()
        return self._adapter(provider)
