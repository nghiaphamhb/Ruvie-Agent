"""Organization connection administration and one model policy for all consumers."""
from dataclasses import dataclass, field
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from ruvie.adapters.llm import OpenAICompatibleLlmAdapter, normalize_llm_url
from ruvie.config import LlmProviderSettings, Settings
from ruvie.contracts.llm import (
    ConnectionResponse, ModelsResponse, OrganizationConnectionDraft,
    OrganizationConnectionUpdateRequest, OrganizationConnectionResponse, VerifiedConnectionResponse,
)
from ruvie.models import OrganizationLlmSettings, UserLlmSettings
from ruvie.services.admin import AdminAccountService
from ruvie.services.audit import AuditEventWriter
from ruvie.services.llm_secrets import LlmSecretStore


class LlmNotConfiguredError(RuntimeError):
    def __init__(self):
        super().__init__('llm_not_configured')


class LlmStorageError(RuntimeError):
    def __init__(self):
        super().__init__('llm_settings_unavailable')


class LlmConfigurationConflict(RuntimeError):
    def __init__(self):
        super().__init__('configuration_conflict')


@dataclass(frozen=True)
class OrganizationSnapshot:
    """Copy DB state before releasing its transaction for a provider call."""
    version: int
    base_url: str | None
    ciphertext: str | None = field(repr=False)
    allowed_ids: tuple[str, ...]
    default_id: str | None
    updated_at: object


class LlmConnectionService:
    """Only organization settings resolve credentials; preferences never grant access."""
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session, self.settings = session, settings

    def _snapshot(self) -> OrganizationSnapshot:
        row = self.session.scalar(select(OrganizationLlmSettings).where(
            OrganizationLlmSettings.id == 1).execution_options(populate_existing=True))
        if row is None:
            raise LlmStorageError()
        return OrganizationSnapshot(row.version, row.base_url, row.api_key_ciphertext,
                                    tuple(row.allowed_model_ids), row.default_model_id, row.updated_at)

    def _secrets(self):
        return LlmSecretStore(getattr(self.settings, 'llm_settings_encryption_key', None))

    def _adapter(self, provider: LlmProviderSettings | None):
        """Retain the existing server-owned DNS, TLS, origin and proxy guard."""
        if provider is None:
            raise LlmNotConfiguredError()
        base_url = normalize_llm_url(provider.base_url, self.settings.llm_allowed_local_origins)
        return OpenAICompatibleLlmAdapter(
            LlmProviderSettings(base_url, provider.model, provider.api_key),
            allowed_local_origins=self.settings.llm_allowed_local_origins,
            proxy_url=getattr(self.settings, 'llm_proxy_url', None),
        )

    @staticmethod
    def _metadata(snapshot):
        return OrganizationConnectionResponse(
            configured=snapshot.version > 0, base_url=snapshot.base_url,
            has_api_key=snapshot.ciphertext is not None, allowed_model_ids=list(snapshot.allowed_ids),
            default_model_id=snapshot.default_id, version=snapshot.version, updated_at=snapshot.updated_at)

    def get_organization(self, actor_id: str):
        """Return safe DB metadata to a current administrator, without a provider probe."""
        AdminAccountService(self.session).require_admin(actor_id)
        return self._metadata(self._snapshot())

    def _draft_provider(self, actor_id, body):
        AdminAccountService(self.session).require_admin(actor_id)
        snapshot = self._snapshot()
        if snapshot.version != body.expected_version:
            raise LlmConfigurationConflict()
        url = normalize_llm_url(body.base_url, self.settings.llm_allowed_local_origins)
        if body.key_action == 'keep':
            if snapshot.version == 0 or url != snapshot.base_url:
                raise ValueError('invalid_llm_request')
            key = self._secrets().decrypt(snapshot.ciphertext)
        elif body.key_action == 'replace':
            key = body.api_key.get_secret_value().strip()
        else:
            key = ''
        # No row locks or idle read transactions remain open over network I/O.
        self.session.rollback()
        return snapshot, LlmProviderSettings(url, api_key=key)

    def verify_organization(self, actor_id: str, command: OrganizationConnectionDraft):
        """Probe one draft without changing persistence; recheck authority/version afterwards."""
        body = OrganizationConnectionDraft.model_validate(command.model_dump(exclude_unset=True))
        snapshot, provider = self._draft_provider(actor_id, body)
        catalog = self._adapter(provider).list_models()
        AdminAccountService(self.session).require_admin(actor_id)
        if self._snapshot().version != snapshot.version:
            raise LlmConfigurationConflict()
        return VerifiedConnectionResponse(models=catalog, version=snapshot.version)

    def apply_organization(self, actor_id: str, command: OrganizationConnectionUpdateRequest):
        """Probe then compare-and-swap the entire policy and its audit in one transaction."""
        body = OrganizationConnectionUpdateRequest.model_validate(command.model_dump(exclude_unset=True))
        snapshot, provider = self._draft_provider(actor_id, body)
        catalog = self._adapter(provider).list_models()
        if not set(body.allowed_model_ids).issubset({item['id'] for item in catalog}):
            raise ValueError('invalid_llm_request')
        ciphertext = self._secrets().encrypt(provider.api_key)
        try:
            # Lock actor first: concurrent role/activity updates must finish before authorization.
            AdminAccountService(self.session).require_admin(actor_id, lock=True)
            changed = self.session.execute(update(OrganizationLlmSettings).where(
                OrganizationLlmSettings.id == 1,
                OrganizationLlmSettings.version == snapshot.version,
            ).values(version=snapshot.version + 1, base_url=provider.base_url,
                     api_key_ciphertext=ciphertext, allowed_model_ids=body.allowed_model_ids,
                     default_model_id=body.default_model_id, updated_by=actor_id))
            if changed.rowcount != 1:
                raise LlmConfigurationConflict()
            AuditEventWriter.append(self.session, actor_id, action='llm.organization_settings.update',
                                    resource_type='organization_llm', resource_id='1', outcome='allow',
                                    reason=f'version:{snapshot.version}->{snapshot.version + 1};models:{len(body.allowed_model_ids)};key:{body.key_action}')
            result = self._metadata(self._snapshot())
            self.session.commit()
            return result
        except SQLAlchemyError:
            self.session.rollback()
            raise LlmStorageError() from None
        except Exception:
            self.session.rollback()
            raise

    def _resolve(self, user_id: str):
        """Return copied organization/preference state, never personal or environment settings."""
        snapshot = self._snapshot()
        if snapshot.version == 0:
            raise LlmNotConfiguredError()
        record = self.session.get(UserLlmSettings, user_id)
        preference = record.selected_model_id if record else None
        provider = LlmProviderSettings(snapshot.base_url, api_key=self._secrets().decrypt(snapshot.ciphertext))
        self.session.rollback()
        adapter = self._adapter(provider)
        catalog = [item for item in adapter.list_models() if item['id'] in snapshot.allowed_ids]
        return snapshot, preference, adapter, catalog

    @staticmethod
    def _selection(preference, snapshot, catalog):
        desired = preference if preference is not None else snapshot.default_id
        return desired if desired in {item['id'] for item in catalog} else None

    def get_connection(self, user_id: str) -> ConnectionResponse:
        """Public metadata omits provider details and does not claim live availability."""
        snapshot = self._snapshot()
        record = self.session.get(UserLlmSettings, user_id)
        selected = record.selected_model_id if record and record.selected_model_id else snapshot.default_id
        return ConnectionResponse(configured=snapshot.version > 0,
                                  selected_model_id=selected if selected in snapshot.allowed_ids else None,
                                  configuration_version=snapshot.version)

    def list_models(self, user_id: str) -> ModelsResponse:
        snapshot, preference, _, catalog = self._resolve(user_id)
        selected = self._selection(preference, snapshot, catalog)
        return ModelsResponse(models=catalog, selected_model_id=selected,
                              selection_required=selected is None, configuration_version=snapshot.version)

    def resolve_chat_adapter(self, user_id: str, model_id: str | None = None):
        """Resolve and freeze policy before embedding/retrieval or starting a stream."""
        snapshot, preference, adapter, catalog = self._resolve(user_id)
        selected = model_id if model_id is not None else self._selection(preference, snapshot, catalog)
        if selected not in {item['id'] for item in catalog}:
            raise ValueError('model_not_allowed' if model_id is not None else 'model_selection_required')
        return self._adapter(LlmProviderSettings(adapter.provider.base_url, selected, adapter.provider.api_key))

    def select_model(self, user_id: str, model_id: str):
        """Persist only the actor's preference after the same fresh policy check used by chat."""
        snapshot, _, _, catalog = self._resolve(user_id)
        if model_id not in {item['id'] for item in catalog}:
            raise ValueError('model_not_allowed')
        try:
            record = self.session.get(UserLlmSettings, user_id)
            if record is None:
                record = UserLlmSettings(user_id=user_id)
                self.session.add(record)
            record.selected_model_id = model_id
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            raise LlmStorageError() from None
        return {'selected_model_id':model_id, 'configuration_version':snapshot.version}
