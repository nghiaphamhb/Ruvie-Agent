from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session

from ruvie.contracts.auth import AuthResponse, AuthUser, LoginRequest, RegisterRequest
from ruvie.dependencies import get_authenticated_user_id, get_session
from ruvie.api.security import check_origin, verify_csrf
from ruvie.services.auth import AuthService, EmailTaken, SESSION_HOURS


class RegistrationRoute(APIRoute):
    """Redact register validation before FastAPI's default handler can echo passwords."""
    def get_route_handler(self):
        handler = super().get_route_handler()
        if not self.path.endswith("/register"):
            return handler

        async def safe_register(request: Request):
            try:
                check_origin(request, request.app.state.settings)
            except HTTPException:
                return JSONResponse(status_code=403, content={"detail": {"code": "origin_not_allowed"}})
            try:
                return await handler(request)
            except RequestValidationError as error:
                fields = {}
                for issue in error.errors():
                    location = issue.get("loc", ())
                    field = location[1] if len(location) == 2 and location[0] == "body" else None
                    if field not in ("display_name", "email", "password"):
                        continue
                    kind = issue["type"]
                    code = "invalid_type"
                    if kind == "missing":
                        code = "required"
                    elif kind in ("string_too_short", "string_too_long"):
                        code = {"display_name": "name_length", "email": "email_length",
                                "password": "password_length"}[field]
                    elif kind == "value_error" and field == "email":
                        code = "invalid_email"
                    fields[field] = code
                detail = {"code": "validation_error"}
                if fields:
                    detail["fields"] = fields
                return JSONResponse(status_code=422, content={"detail": detail})

        return safe_register


router = APIRouter(prefix="/auth", tags=["auth"], route_class=RegistrationRoute)
COOKIE_NAME = "ruvie_session"


def _auth_response(user, csrf_token: str) -> AuthResponse:
    return AuthResponse(user=AuthUser(id=user.id, display_name=user.display_name), csrf_token=csrf_token)


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


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(
    body: RegisterRequest,
    response: Response,
    db: Session = Depends(get_session),
) -> AuthResponse:
    """POST /auth/register: {display_name,email,password} -> committed account/session."""
    # RegistrationRoute checks Origin before body parsing, and never returns raw input.
    try:
        result = AuthService(db).register(body.display_name, body.email, body.password)
    except EmailTaken:
        raise HTTPException(status_code=409, detail={
            "code": "email_taken", "fields": {"email": "email_taken"},
        }) from None
    except Exception:
        # Do not serialize/log SQL parameters, passwords, or provider details.
        raise HTTPException(status_code=500, detail={"code": "registration_failed"}) from None
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
