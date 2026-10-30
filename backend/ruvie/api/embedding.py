"""Administrator-only embedding HTTP boundaries with secret-safe errors."""
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from ruvie.api.security import check_origin
from ruvie.api.llm import require_admin_write_access
from ruvie.dependencies import get_admin_user_id, get_session, get_settings
from ruvie.contracts.embedding import (
    EmbeddingConnectionDraft, EmbeddingConnectionRequest, EmbeddingConnectionResponse,
    EmbeddingCatalogResponse, EmbeddingVerificationResponse,
)
from ruvie.services.embedding import EmbeddingConnectionService, EmbeddingUnavailableError
from ruvie.services.admin import AdminRequired, AuthenticationRequired
from ruvie.services.llm import LlmConfigurationConflict
from ruvie.services.llm_secrets import LlmSecretError
from ruvie.adapters.network import InvalidNetworkConfiguration, ProxyUnavailableError, NetworkConfigurationPendingError
from ruvie.adapters.llm import InvalidLlmUrl


class EmbeddingRoute(APIRoute):
    """Never reflect request validation inputs, upstream bodies, SQL or credential errors."""
    def get_route_handler(self):
        handler = super().get_route_handler()
        async def safe_handler(request: Request):
            status, code = 503, 'embedding_settings_unavailable'
            try:
                if request.method != 'GET':
                    try:
                        check_origin(request, request.app.state.settings)
                    except HTTPException:
                        raise HTTPException(403, detail={'code':'origin_invalid'}) from None
                response = await handler(request)
                response.headers['Cache-Control'] = 'no-store'
                return response
            except (RequestValidationError, ValidationError) as error:
                status = 422
                code = 'invalid_network_configuration' if any('network' in str(piece.get('loc', ())) for piece in error.errors()) else 'invalid_embedding_request'
            except AuthenticationRequired:
                status, code = 401, 'authentication_required'
            except AdminRequired:
                status, code = 403, 'admin_required'
            except LlmConfigurationConflict:
                status, code = 409, 'configuration_conflict'
            except NetworkConfigurationPendingError:
                status, code = 503, 'network_configuration_pending'
            except ProxyUnavailableError:
                status, code = 503, 'proxy_unavailable'
            except httpx.ProxyError:
                status, code = 503, 'proxy_unavailable'
            except InvalidNetworkConfiguration:
                status, code = 422, 'invalid_network_configuration'
            except EmbeddingUnavailableError as error:
                code = error.code
            except (LlmSecretError, SQLAlchemyError):
                pass
            except httpx.TimeoutException:
                code = 'embedding_timeout'
            except httpx.HTTPStatusError as error:
                upstream_status=error.response.status_code
                code = ('embedding_authentication_failed' if upstream_status in (401,403)
                        else 'embedding_rate_limited' if upstream_status == 429
                        else 'embedding_catalog_unavailable' if request.url.path.endswith('/catalog') and upstream_status in (404,405)
                        else 'embedding_provider_unavailable')
            except httpx.HTTPError:
                code = 'embedding_provider_unavailable'
            except (InvalidLlmUrl, ValueError) as error:
                status = 422
                code = str(error) if str(error) in {'embedding_model_unsupported', 'embedding_dimension_unsupported'} else 'invalid_embedding_request'
            except HTTPException as error:
                status = error.status_code
                detail = error.detail
                code = detail.get('code') if isinstance(detail,dict) else None
                if code not in {'origin_invalid','csrf_invalid','authentication_required','admin_required'}:
                    code = 'authentication_required' if status == 401 else 'csrf_invalid'
            except Exception:
                pass
            return JSONResponse(status_code=status, content={'detail':{'code':code}}, headers={'Cache-Control':'no-store'})
        return safe_handler


router = APIRouter(prefix='/admin/embedding/connection', tags=['embedding'],route_class=EmbeddingRoute)


def get_service(db=Depends(get_session), settings=Depends(get_settings)):
    return EmbeddingConnectionService(db,settings)


@router.get('', response_model=EmbeddingConnectionResponse)
def metadata(actor=Depends(get_admin_user_id),service=Depends(get_service)):
    """GET safe saved metadata, without probing a provider."""
    return service.get_organization(actor)


@router.post('/catalog', response_model=EmbeddingCatalogResponse)
def catalog(body: EmbeddingConnectionDraft, actor=Depends(require_admin_write_access),service=Depends(get_service)):
    """POST a draft -> embedding catalog, without saving."""
    return service.catalog(actor,body)


@router.post('/verify', response_model=EmbeddingVerificationResponse)
def verify(body: EmbeddingConnectionRequest, actor=Depends(require_admin_write_access),service=Depends(get_service)):
    """POST a draft/model -> real vector compatibility, without saving."""
    return service.verify_organization(actor,body)


@router.put('', response_model=EmbeddingConnectionResponse)
def apply(body: EmbeddingConnectionRequest, actor=Depends(require_admin_write_access),service=Depends(get_service)):
    """PUT re-probes then atomically saves the versioned connection and audit."""
    return service.apply_organization(actor,body)
