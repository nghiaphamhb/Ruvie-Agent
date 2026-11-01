"""Thin HTTP boundaries for owned conversation history and generation control."""
from uuid import UUID
from fastapi import APIRouter, Depends, Request, Response, Query, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from ruvie.api.security import check_origin, verify_csrf
from ruvie.dependencies import get_authenticated_user_id, get_session
from ruvie.contracts.conversations import RenameConversation, RetryTurn, StopTurn
from ruvie.services.conversations import ConversationService, ConversationError
from ruvie.services.chat import ChatService, ProviderUnavailableError


class HistoryRoute(APIRoute):
    """Sanitize failures and forbid caching on successes and errors alike."""
    def get_route_handler(self):
        handler = super().get_route_handler()
        async def safe(request: Request):
            try:
                response = await handler(request)
                response.headers['Cache-Control'] = 'no-store'
                return response
            except ConversationError as error:
                status, detail = error.status, {'code': error.code, **error.resources}
            except RequestValidationError:
                status, detail = 422, {'code': 'invalid_chat_request'}
            except ProviderUnavailableError:
                status, detail = 503, {'code': 'provider_unavailable'}
            except SQLAlchemyError:
                status, detail = 503, {'code': 'history_unavailable'}
            except ValueError:
                status, detail = 422, {'code': 'model_unavailable'}
            except HTTPException as error:
                status = error.status_code
                detail = {'code': 'authentication_required' if status == 401 else 'csrf_or_origin_invalid'}
            return JSONResponse(status_code=status, content={'detail': detail}, headers={'Cache-Control': 'no-store'})
        return safe


router = APIRouter(prefix='/conversations', tags=['conversations'], route_class=HistoryRoute)

@router.get('')
def list_conversations(limit: int = Query(30, ge=1, le=100), cursor: str | None = None,
                       user: str = Depends(get_authenticated_user_id), db: Session = Depends(get_session)):
    """GET /conversations returns owned metadata and an opaque next cursor."""
    return ConversationService(db).list(user, limit=limit, cursor=cursor)

@router.get('/{conversation_id}')
def detail(conversation_id: UUID, limit: int = Query(50, ge=1, le=100), before: str | None = None,
           user: str = Depends(get_authenticated_user_id), db: Session = Depends(get_session)):
    """GET /conversations/{id} returns the newest page with authorized assistant content."""
    return ConversationService(db).detail(user, str(conversation_id), limit=limit, before=before)

@router.patch('/{conversation_id}')
def rename(conversation_id: UUID, body: RenameConversation, request: Request,
           user: str = Depends(get_authenticated_user_id), db: Session = Depends(get_session)):
    check_origin(request, request.app.state.settings)
    verify_csrf(request, user, db)
    return ConversationService(db).rename(user, str(conversation_id), body.title, body.expected_version)

@router.delete('/{conversation_id}', status_code=204)
def delete(conversation_id: UUID, request: Request,
           user: str = Depends(get_authenticated_user_id), db: Session = Depends(get_session)):
    check_origin(request, request.app.state.settings)
    verify_csrf(request, user, db)
    ConversationService(db).delete(user, str(conversation_id))
    return Response(status_code=204)

@router.post('/{conversation_id}/turns/{turn_id}/stop')
def stop(conversation_id: UUID, turn_id: UUID, body: StopTurn, request: Request,
         user: str = Depends(get_authenticated_user_id), db: Session = Depends(get_session)):
    check_origin(request, request.app.state.settings)
    verify_csrf(request, user, db)
    return ConversationService(db).stop(user, str(conversation_id), str(turn_id), str(body.attempt_id))

@router.post('/{conversation_id}/turns/{turn_id}/retry')
def retry(conversation_id: UUID, turn_id: UUID, body: RetryTurn, request: Request,
          user: str = Depends(get_authenticated_user_id)):
    from ruvie.api.chat import _sse_response
    check_origin(request, request.app.state.settings)
    with request.app.state.session_factory() as db:
        verify_csrf(request, user, db)
    service = ChatService(request.app.state.query_embedder, request.app.state.settings, request.app.state.session_factory)
    return _sse_response(service.start(user, None, str(body.request_id), body.model_id, str(conversation_id), str(turn_id)))
