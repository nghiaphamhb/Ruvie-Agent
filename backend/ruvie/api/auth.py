from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session

from ruvie.contracts.auth import AuthResponse, AuthUser, LoginRequest, RegisterRequest, SetupStatusResponse
from ruvie.dependencies import get_authenticated_user_id, get_session
from ruvie.api.security import AccountCreationRoute, check_origin, verify_csrf
from ruvie.services.auth import AuthService, SetupAlreadyCompleted, SESSION_HOURS


class RegistrationRoute(AccountCreationRoute):
    """Apply shared creation protection to register; preserve other auth handlers."""
    def get_route_handler(self):
        handler = (super().get_route_handler() if self.path.endswith("/register")
                   else APIRoute.get_route_handler(self))

        async def uncached_auth(request: Request):
            """Session and setup responses must not be stored by browsers or intermediaries."""
            try:
                response = await handler(request)
            except HTTPException as error:
                error.headers = {**(error.headers or {}), "Cache-Control": "no-store"}
                raise
            response.headers["Cache-Control"] = "no-store"
            return response

        return uncached_auth


router = APIRouter(prefix="/auth", tags=["auth"], route_class=RegistrationRoute)
COOKIE_NAME = "ruvie_session"


def _auth_response(user, csrf_token: str) -> AuthResponse:
    return AuthResponse(user=AuthUser(
        id=user.id, display_name=user.display_name, system_role=user.system_role,
    ), csrf_token=csrf_token)


def _set_session_cookie(response: Response, token: str) -> None:
    """Login and registration share one 12-hour, browser-private cookie configuration."""
    response.set_cookie(
        COOKIE_NAME, token, max_age=SESSION_HOURS * 3600, httponly=True,
        secure=True, samesite="lax", path="/",
    )


@router.post("/login", response_model=AuthResponse)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_session),
) -> AuthResponse:
    """POST /auth/login: {email, password} -> user/CSRF and secure session cookie."""
    check_origin(request, request.app.state.settings)
    service = AuthService(db)
    user = service.authenticate(body.email, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="email or password is incorrect")
    created = service.create_session(user.id)
    _set_session_cookie(response, created.token)
    return _auth_response(user, created.csrf_token)


@router.get("/setup", response_model=SetupStatusResponse)
def setup_status(db: Session = Depends(get_session)) -> SetupStatusResponse:
    """GET /auth/setup: public {requires_initial_admin}; never infer empty on DB failure."""
    try:
        return SetupStatusResponse(requires_initial_admin=AuthService(db).get_setup_status())
    except Exception:
        raise HTTPException(status_code=503, detail={"code": "setup_unavailable"}) from None


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(
    body: RegisterRequest,
    response: Response,
    db: Session = Depends(get_session),
) -> AuthResponse:
    """POST /auth/register: identity/password -> first admin/session, only with zero users."""
    # RegistrationRoute checks Origin before body parsing, and never returns raw input.
    try:
        result = AuthService(db).register(body.display_name, body.email, body.password)
    except SetupAlreadyCompleted:
        raise HTTPException(status_code=409, detail={"code": "setup_already_completed"}) from None
    except Exception:
        # Do not serialize/log SQL parameters, passwords, or provider details.
        raise HTTPException(status_code=500, detail={"code": "account_creation_failed"}) from None
    _set_session_cookie(response, result.created_session.token)
    return _auth_response(result.user, result.created_session.csrf_token)


@router.get("/session", response_model=AuthResponse)
def current_session(
    request: Request,
    user_id: str = Depends(get_authenticated_user_id),
    db: Session = Depends(get_session),
) -> AuthResponse:
    """GET /auth/session: cookie -> active user/CSRF, or HTTP 401."""
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
    """POST /auth/logout: session + Origin/CSRF -> revoke session, clear cookie."""
    check_origin(request, request.app.state.settings)
    verify_csrf(request, user_id, db)
    AuthService(db).revoke_session(request.cookies[COOKIE_NAME])
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, secure=True, samesite="lax")
    response.status_code = 204
    return response


@router.post("/presence", status_code=204)
def presence(
    request: Request,
    user_id: str = Depends(get_authenticated_user_id),
    db: Session = Depends(get_session),
) -> Response:
    """POST /auth/presence: cookie + Origin/CSRF -> refresh server-time presence."""
    check_origin(request, request.app.state.settings)
    verify_csrf(request, user_id, db)
    if not AuthService(db).touch_presence(request.cookies[COOKIE_NAME], user_id):
        raise HTTPException(status_code=401, detail="authentication required")
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
