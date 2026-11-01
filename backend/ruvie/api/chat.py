from collections.abc import Iterable

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from ruvie.api.conversations import HistoryRoute
from ruvie.api.security import check_origin, verify_csrf
from ruvie.contracts.chat import ChatRequest, ChatStreamEvent
from ruvie.dependencies import get_authenticated_user_id
from ruvie.services.chat import ChatService


router = APIRouter(tags=["chat"], route_class=HistoryRoute)


def _sse_response(events: Iterable[ChatStreamEvent]) -> StreamingResponse:
    """Encode service events as SSE; disable proxy buffering."""
    return StreamingResponse(
        (event.to_sse() for event in events),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@router.post("/chat")
def chat(
    body: ChatRequest,
    request: Request,
    user_id: str = Depends(get_authenticated_user_id),
) -> StreamingResponse:
    """POST /chat: {message, request_id, conversation_id?, model_id?} -> durable answer SSE."""
    check_origin(request, request.app.state.settings)
    service = ChatService(
        request.app.state.query_embedder,
        request.app.state.settings,
        request.app.state.session_factory,
    )
    with request.app.state.session_factory() as db:
        verify_csrf(request, user_id, db)
    return _sse_response(service.start(user_id, body.message, str(body.request_id),
                                     body.model_id, str(body.conversation_id) if body.conversation_id else None))
