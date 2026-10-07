from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session

from ruvie.adapters.llm import InvalidLlmUrl, LlmProviderError
from ruvie.api.security import check_origin, verify_csrf
from ruvie.contracts.llm import ConnectionResponse, ConnectionUpdateRequest, ModelSelectionRequest, ModelsResponse
from ruvie.dependencies import get_authenticated_user_id, get_session, get_settings
from ruvie.config import Settings
from ruvie.services.llm import LlmConnectionService, LlmNotConfiguredError, LlmStorageError


class LlmRoute(APIRoute):
    """Hide validation input so API keys cannot be echoed in HTTP error responses."""

    def get_route_handler(self):
        """Wrap the FastAPI handler and sanitize request validation errors."""
        # Keep FastAPI parsing/dependencies intact; replace only unsafe validation details.
        handler = super().get_route_handler()

        async def safe_handler(request: Request):
            try:
                return await handler(request)
            except RequestValidationError:
                # FastAPI's default validation response may echo a body containing the key.
                raise HTTPException(status_code=422, detail="Invalid LLM request") from None
        return safe_handler


router = APIRouter(tags=["llm"], route_class=LlmRoute)


def get_service(
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> LlmConnectionService:
    """Build the connection service with this request session and server settings."""
    return LlmConnectionService(db, settings)


def require_write_access(
    request: Request,
    user_id: str = Depends(get_authenticated_user_id),
    db: Session = Depends(get_session),
) -> str:
    """Check session, Origin and CSRF; return the trusted user ID for writes."""
    check_origin(request, request.app.state.settings)
    verify_csrf(request, user_id, db)
    return user_id


def _call(function, *args):
    """Translate service failures into safe 422/502/503 responses without provider details."""
    try:
        return function(*args)
    except (InvalidLlmUrl, ValueError):
        raise HTTPException(status_code=422, detail="LLM URL or model is invalid or not allowed") from None
    except LlmProviderError:
        raise HTTPException(status_code=502, detail="LLM provider could not return models") from None
    except (LlmNotConfiguredError, LlmStorageError):
        raise HTTPException(status_code=503, detail="LLM connection or settings are unavailable") from None


@router.get("/llm/connection", response_model=ConnectionResponse)
def get_connection(
    user_id: str = Depends(get_authenticated_user_id),
    service: LlmConnectionService = Depends(get_service),
):
    """GET /llm/connection -> source, URL, has_api_key and selected ID; never return the key."""
    return _call(service.get_connection, user_id)


@router.put("/llm/connection", response_model=ModelsResponse)
def save_connection(
    body: ConnectionUpdateRequest,
    user_id: str = Depends(require_write_access),
    service: LlmConnectionService = Depends(get_service),
):
    """PUT /llm/connection: {base_url, api_key?} -> verified models and selection state."""
    return _call(service.save_connection, user_id, body)


@router.get("/models", response_model=ModelsResponse)
def list_models(
    user_id: str = Depends(get_authenticated_user_id),
    service: LlmConnectionService = Depends(get_service),
):
    """GET /models -> fresh {models, selected_model_id, selection_required}; no DB writes."""
    return _call(service.list_models, user_id)


@router.patch("/llm/connection/model")
def select_model(
    body: ModelSelectionRequest,
    user_id: str = Depends(require_write_access),
    service: LlmConnectionService = Depends(get_service),
) -> dict[str, str]:
    """PATCH /llm/connection/model: {model_id} -> selected_model_id after verification."""
    return _call(service.select_model, user_id, body.model_id)


@router.delete("/llm/connection", status_code=204)
def delete_connection(
    user_id: str = Depends(require_write_access),
    service: LlmConnectionService = Depends(get_service),
):
    """DELETE /llm/connection -> remove personal settings/preferences and return 204."""
    _call(service.delete_connection, user_id)
    return Response(status_code=204)
