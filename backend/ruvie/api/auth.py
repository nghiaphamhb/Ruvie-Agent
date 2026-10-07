from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from ruvie.contracts.auth import AuthResponse, AuthUser, LoginRequest
from ruvie.dependencies import get_authenticated_user_id, get_session
from ruvie.api.security import check_origin, verify_csrf
from ruvie.services.auth import AuthService, SESSION_HOURS


router = APIRouter(prefix="/auth", tags=["auth"])
COOKIE_NAME = "ruvie_session"


def _auth_response(user, csrf_token: str) -> AuthResponse:
    return AuthResponse(user=AuthUser(id=user.id, display_name=user.display_name), csrf_token=csrf_token)


@router.post("/login", response_model=AuthResponse)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_session),
) -> AuthResponse:
    """POST /auth/login: {email, password} -> user/CSRF token and a secure session cookie."""
    check_origin(request, request.app.state.settings)
    service = AuthService(db)
    user = service.authenticate(body.email, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="email or password is incorrect")
    created = service.create_session(user.id)
    # HttpOnly keeps the cookie out of JavaScript; CSRF token is returned separately.
    response.set_cookie(
        COOKIE_NAME, created.token,
        max_age=SESSION_HOURS * 3600,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    return _auth_response(user, created.csrf_token)


@router.get("/session", response_model=AuthResponse)
def current_session(
    request: Request,
    user_id: str = Depends(get_authenticated_user_id),
    db: Session = Depends(get_session),
) -> AuthResponse:
    """GET /auth/session: session cookie -> active user/CSRF token, or HTTP 401."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="authentication required")
    resolved = AuthService(db).resolve_session(token)
    if resolved is None or resolved.user.id != user_id:
        raise HTTPException(status_code=401, detail="authentication required")
    return _auth_response(resolved.user, resolved.csrf_token)


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    user_id: str = Depends(get_authenticated_user_id),
    db: Session = Depends(get_session),
) -> Response:
    """POST /auth/logout: session + Origin/CSRF -> revoke session, clear cookie, return 204."""
    check_origin(request, request.app.state.settings)
    verify_csrf(request, user_id, db)
    token = request.cookies[COOKIE_NAME]
    AuthService(db).revoke_session(token)
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, secure=True, samesite="lax")
    response.status_code = 204
    return response
