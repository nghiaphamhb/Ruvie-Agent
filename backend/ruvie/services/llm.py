from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ruvie.adapters.llm import OpenAICompatibleLlmAdapter, normalize_llm_url
from ruvie.config import LlmProviderSettings, Settings
from ruvie.contracts.llm import ConnectionResponse, ConnectionUpdateRequest, ModelsResponse
from ruvie.models import UserLlmSettings


class LlmNotConfiguredError(RuntimeError):
    pass


class LlmStorageError(RuntimeError):
    pass


class LlmConnectionService:
    """Manage one user connection/selection; verify the provider before database writes."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self.session, self.settings = session, settings

    def _resolve(self, user_id: str):
        """Return (user row, effective provider, source), preferring personal settings."""
        record = self.session.get(UserLlmSettings, user_id)
        if record is not None and record.base_url is not None:
            return (
                record,
                LlmProviderSettings(
                    record.base_url, record.selected_model_id or "", record.api_key or ""
                ),
                "personal",
            )
        return record, self.settings.llm, "server" if self.settings.llm else "none"

    def _adapter(self, provider: LlmProviderSettings | None):
        """Validate the URL and return an adapter with server network permissions."""
        if provider is None:
            raise LlmNotConfiguredError("LLM connection is not configured")
        base_url = normalize_llm_url(provider.base_url, self.settings.llm_allowed_local_origins)
        return OpenAICompatibleLlmAdapter(
            LlmProviderSettings(base_url, provider.model, provider.api_key),
            allowed_local_origins=self.settings.llm_allowed_local_origins,
        )

    def _commit(self) -> None:
        """Commit settings or roll back and raise a safe storage error."""
        try:
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            raise LlmStorageError("LLM settings could not be saved") from None

    @staticmethod
    def _selection(record, catalog, default_model="", new_connection=False):
        """Keep a valid saved ID; missing saved IDs require selection, new connections use a default."""
        ids = {model["id"] for model in catalog}
        if record is not None and not new_connection:
            if record.selected_model_id:
                return record.selected_model_id if record.selected_model_id in ids else None
            # A prior catalog with no selection means the user must choose again.
            if record.models:
                return None
        return default_model if default_model in ids else catalog[0]["id"]

    def get_connection(self, user_id: str) -> ConnectionResponse:
        """Return user connection metadata without calling the provider or returning the key."""
        record, provider, source = self._resolve(user_id)
        return ConnectionResponse(
            source=source, base_url=provider.base_url if provider else None,
            has_api_key=bool(provider and provider.api_key),
            selected_model_id=(
                (record.selected_model_id if record is not None else provider.model or None)
                if provider else None
            ),
        )

    def list_models(self, user_id: str) -> ModelsResponse:
        """Fetch fresh models/selection state; leave stored settings unchanged."""
        record, provider, _ = self._resolve(user_id)
        catalog = self._adapter(provider).list_models()
        selected = self._selection(record, catalog, provider.model)
        return ModelsResponse(
            models=catalog, selected_model_id=selected, selection_required=selected is None
        )

    def resolve_chat_adapter(self, user_id: str, model_id: str | None = None) -> OpenAICompatibleLlmAdapter:
        """Validate a fresh catalog and return a request adapter without saving preferences."""
        record, provider, _ = self._resolve(user_id)
        adapter = self._adapter(provider)
        catalog = adapter.list_models()
        selected = model_id if model_id is not None else self._selection(record, catalog, provider.model)
        if selected not in {model["id"] for model in catalog}:
            raise ValueError("Selected model is not available")
        # Frozen settings copy the URL/key/ID; later DB changes cannot affect this request.
        return self._adapter(LlmProviderSettings(adapter.provider.base_url, selected, provider.api_key))

    def save_connection(self, user_id: str, body: ConnectionUpdateRequest) -> ModelsResponse:
        """Verify URL/key/models, then save the personal connection and return selection state."""
        base_url = normalize_llm_url(body.base_url, self.settings.llm_allowed_local_origins)
        record = self.session.get(UserLlmSettings, user_id)
        same_connection = record is not None and record.base_url == base_url
        # Omitted key keeps the old key only for the same URL; empty key explicitly clears it.
        if "api_key" in body.model_fields_set:
            api_key = body.api_key.get_secret_value().strip() or None
        else:
            api_key = record.api_key if same_connection else None
        # Verify the new connection before mutating the stored row.
        catalog = self._adapter(LlmProviderSettings(base_url, api_key=api_key or "")).list_models()
        selected = self._selection(record, catalog, new_connection=not same_connection)
        if record is None:
            record = UserLlmSettings(user_id=user_id)
            self.session.add(record)
        record.base_url, record.api_key = base_url, api_key
        record.models, record.selected_model_id = catalog, selected
        self._commit()
        return ModelsResponse(
            models=catalog, selected_model_id=selected, selection_required=selected is None
        )

    def select_model(self, user_id: str, model_id: str) -> dict[str, str]:
        """Verify the ID against fresh models, save the preference, and return the chosen ID."""
        record, provider, _ = self._resolve(user_id)
        catalog = self._adapter(provider).list_models()
        if model_id not in {model["id"] for model in catalog}:
            raise ValueError("Selected model is not available")
        if record is None:
            record = UserLlmSettings(user_id=user_id)
            self.session.add(record)
        # A server-model preference stores no copy of the server URL or key.
        record.models, record.selected_model_id = catalog, model_id
        self._commit()
        return {"selected_model_id": model_id}

    def delete_connection(self, user_id: str) -> None:
        """Remove personal settings/preferences so later reads use the server fallback."""
        record = self.session.get(UserLlmSettings, user_id)
        if record is not None:
            self.session.delete(record)
            self._commit()
