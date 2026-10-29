"""Safe HTTP boundaries for organization LLM administration and personal preferences."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from ruvie.adapters.llm import InvalidLlmUrl, LlmProviderError
from ruvie.api.security import check_origin, verify_csrf
from ruvie.config import Settings
from ruvie.contracts.llm import (ConnectionResponse, ModelSelectionRequest, ModelsResponse,
    OrganizationConnectionDraft, OrganizationConnectionUpdateRequest,
    OrganizationConnectionResponse, VerifiedConnectionResponse)
from ruvie.dependencies import get_authenticated_user_id, get_admin_user_id, get_session, get_settings
from ruvie.services.admin import AdminAccountService, AdminRequired, AuthenticationRequired
from ruvie.services.llm import (LlmConnectionService, LlmNotConfiguredError, LlmStorageError,
                                LlmConfigurationConflict)
from ruvie.services.llm_secrets import LlmSecretError


class LlmRoute(APIRoute):
    """Never reflect request/provider/SQL errors, including validation failures containing keys."""
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def safe_handler(request: Request):
            status, code = 503, 'llm_settings_unavailable'
            try:
                if request.method in {'POST','PUT','PATCH','DELETE'}:
                    try:
                        check_origin(request, request.app.state.settings)
                    except HTTPException:
                        raise HTTPException(403, detail={'code':'origin_invalid'}) from None
                user_id = get_authenticated_user_id(request)
                if request.url.path == '/llm/connection' and request.method in {'PUT','DELETE'}:
                    # Retired mutation bodies are ignored, never redirected to global settings.
                    with request.app.state.session_factory() as db:
                        AdminAccountService(db).require_admin(user_id)
                        verify_csrf(request, user_id, db)
                    raise HTTPException(410, detail={'code':'personal_llm_configuration_removed'})
                response = await handler(request)
                response.headers['Cache-Control'] = 'no-store'
                return response
            except (RequestValidationError, ValidationError):
                status, code = 422, 'invalid_llm_request'
            except AuthenticationRequired:
                status, code = 401, 'authentication_required'
            except AdminRequired:
                status, code = 403, 'admin_required'
            except LlmConfigurationConflict:
                status, code = 409, 'configuration_conflict'
            except LlmNotConfiguredError:
                status, code = 503, 'llm_not_configured'
            except (LlmStorageError, LlmSecretError, SQLAlchemyError):
                pass
            except LlmProviderError:
                status, code = 502, 'llm_provider_unavailable'
            except (InvalidLlmUrl, ValueError):
                status, code = 422, 'invalid_llm_request'
            except HTTPException as error:
                status = error.status_code
                detail = error.detail
                known = {'origin_invalid','csrf_invalid','authentication_required','admin_required',
                         'personal_llm_configuration_removed'}
                code = detail.get('code') if isinstance(detail, dict) else None
                if code not in known:
                    code = 'authentication_required' if status == 401 else 'csrf_invalid'
            except Exception:
                # Do not log bound SQL parameters or raw upstream exceptions here.
                pass
            return JSONResponse(status_code=status, content={'detail':{'code':code}},
                                headers={'Cache-Control':'no-store'})
        return safe_handler


router = APIRouter(tags=['llm'], route_class=LlmRoute)


def get_service(db: Session = Depends(get_session), settings: Settings = Depends(get_settings)):
    return LlmConnectionService(db, settings)


def require_write_access(request: Request, user_id: str = Depends(get_authenticated_user_id),
                         db: Session = Depends(get_session)) -> str:
    """Origin is checked before parsing; validate the CSRF token for this cookie identity."""
    verify_csrf(request, user_id, db)
    return user_id


def require_admin_write_access(actor: str = Depends(get_admin_user_id),
                               checked: str = Depends(require_write_access)) -> str:
    return actor


@router.get('/admin/llm/connection', response_model=OrganizationConnectionResponse)
def get_organization(actor: str = Depends(get_admin_user_id), service=Depends(get_service)):
    """GET metadata without probing the provider or returning credentials."""
    return service.get_organization(actor)


@router.post('/admin/llm/connection/verify', response_model=VerifiedConnectionResponse)
def verify_organization(body: OrganizationConnectionDraft,
                        actor: str = Depends(require_admin_write_access), service=Depends(get_service)):
    """POST {base_url,key_action,api_key?,expected_version} -> catalog, unchanged version."""
    return service.verify_organization(actor, body)


@router.put('/admin/llm/connection', response_model=OrganizationConnectionResponse)
def apply_organization(body: OrganizationConnectionUpdateRequest,
                       actor: str = Depends(require_admin_write_access), service=Depends(get_service)):
    """PUT verified draft/policy -> safe committed metadata and the new version."""
    return service.apply_organization(actor, body)


@router.get('/llm/connection', response_model=ConnectionResponse)
def get_connection(user: str = Depends(get_authenticated_user_id), service=Depends(get_service)):
    return service.get_connection(user)


@router.get('/models', response_model=ModelsResponse)
def list_models(user: str = Depends(get_authenticated_user_id), service=Depends(get_service)):
    return service.list_models(user)


@router.patch('/llm/connection/model')
def select_model(body: ModelSelectionRequest, user: str = Depends(require_write_access), service=Depends(get_service)):
    return service.select_model(user, body.model_id)


@router.put('/llm/connection')
@router.delete('/llm/connection')
def retired_connection():
    """The route wrapper rejects legacy mutations before parsing any body."""
    raise HTTPException(410, detail={'code':'personal_llm_configuration_removed'})
