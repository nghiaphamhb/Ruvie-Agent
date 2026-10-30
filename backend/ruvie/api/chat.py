from collections.abc import Iterable

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from ruvie.services.embedding import EmbeddingUnavailableError
from ruvie.contracts.chat import ChatRequest, ChatStreamEvent
from ruvie.dependencies import get_authenticated_user_id
from ruvie.services.chat import ChatService, ProviderUnavailableError, error_event


router = APIRouter(tags=["chat"])


def _sse_response(events: Iterable[ChatStreamEvent]) -> StreamingResponse:
    """Encode service events as SSE; disable proxy buffering."""
    return StreamingResponse(
        (event.to_sse() for event in events),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat")
def chat(
    body: ChatRequest,
    request: Request,
    user_id: str = Depends(get_authenticated_user_id),
) -> StreamingResponse:
    """POST /chat: {message, model_id?} + session -> authorized answer/citation SSE."""
    service = ChatService(
        request.app.state.query_embedder,
        request.app.state.settings,
        request.app.state.session_factory,
    )
    try:
        prepared = service.prepare(user_id, body.message, body.model_id)
    except EmbeddingUnavailableError:
        return _sse_response((error_event("embedding_unavailable"),))
    except ProviderUnavailableError:
        return _sse_response((error_event("provider_unavailable"),))
    except ValueError:
        raise HTTPException(status_code=422, detail="Selected model is not available; choose a model again") from None
    return _sse_response(service.stream(body.message, prepared))
