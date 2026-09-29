from collections.abc import Iterable

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from ruvie.contracts.chat import ChatRequest
from ruvie.dependencies import get_authenticated_user_id
from ruvie.services.chat import ChatService, ProviderUnavailableError, error_event


router = APIRouter(tags=["chat"])


def _sse_response(events: Iterable[str]) -> StreamingResponse:
    return StreamingResponse(
        events,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat")
def chat(body: ChatRequest, request: Request, user_id: str = Depends(get_authenticated_user_id)) -> StreamingResponse:
    service = ChatService(
        request.app.state.query_embedder,
        request.app.state.llm_adapter,
        request.app.state.session_factory,
    )
    try:
        hits = service.prepare(user_id, body.message)
    except ProviderUnavailableError:
        return _sse_response(iter((error_event("provider_unavailable"),)))
    return _sse_response(service.stream(body.message, hits))
