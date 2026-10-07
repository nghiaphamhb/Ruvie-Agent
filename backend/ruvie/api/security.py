from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from ruvie.config import Settings
from ruvie.services.auth import AuthService


def check_origin(request: Request, settings: Settings) -> None:
    """Allow writes only from configured browser origins; missing/invalid Origin is 403."""
    origin = request.headers.get("origin", "").rstrip("/")
    if not origin or origin not in settings.auth_allowed_origins:
        raise HTTPException(status_code=403, detail="origin not allowed")


def verify_csrf(request: Request, user_id: str, session: Session) -> None:
    """Match the session user and X-CSRF-Token; reject missing/invalid credentials."""
    token = request.cookies.get("ruvie_session")
    resolved = AuthService(session).resolve_session(token) if token else None
    if resolved is None or resolved.user.id != user_id:
        raise HTTPException(status_code=401, detail="authentication required")
    if not AuthService.verify_csrf(resolved.csrf_token, request.headers.get("x-csrf-token")):
        raise HTTPException(status_code=403, detail="csrf validation failed")
