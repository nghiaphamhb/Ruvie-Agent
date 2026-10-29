from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session

from ruvie.contracts.auth import (
    AuthResponse, AuthUser, ChangePasswordRequest, LoginRequest, RegisterRequest,
    SetupStatusResponse,
)
from ruvie.dependencies import get_authenticated_user_id, get_session
from ruvie.api.security import AccountCreationRoute, check_origin, verify_csrf
from ruvie.services.auth import (
    AccountDisabledError, AuthService, PasswordChangeError, SetupAlreadyCompleted,
    SESSION_HOURS,
)


class RegistrationRoute(AccountCreationRoute):
    """Apply shared creation protection to register; preserve other auth handlers."""
    def get_route_handler(self):
        if self.path.endswith("/register"):
            handler = super().get_route_handler()
        elif self.path.endswith("/password"):
            route_handler = APIRoute.get_route_handler(self)

            async def safe_password_change(request: Request):
                """Check Origin before parsing and redact request validation details."""
                try:
                    check_origin(request, request.app.state.settings)
                except HTTPException:
                    return JSONResponse(
                        status_code=403,
                        content={"detail": {"code": "origin_not_allowed"}},
                    )
                try:
                    response = await route_handler(request)
                except HTTPException as error:
                    if error.status_code == 401:
                        return JSONResponse(
                            status_code=401,
                            content={"detail": {"code": "authentication_required"}},
                        )
                    if error.status_code == 403:
                        return JSONResponse(
                            status_code=403,
                            content={"detail": {"code": "csrf_invalid"}},
                        )
                    raise
                except RequestValidationError as error:
                    return JSONResponse(
                        status_code=422,
                        content={"detail": _password_validation_detail(error.errors())},
                    )
                if response.status_code == 401:
                    return JSONResponse(
                        status_code=401,
                        content={"detail": {"code": "authentication_required"}},
                    )
                if response.status_code == 403:
                    return JSONResponse(
                        status_code=403,
                        content={"detail": {"code": "csrf_invalid"}},
                    )
                return response

            handler = safe_password_change
        else:
            handler = APIRoute.get_route_handler(self)

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


def _password_validation_detail(errors: list[dict]) -> dict:
    """Map request validation errors to allowlisted fields and codes only."""
    fields = {}
    mismatch = False
    allowed_fields = {"current_password", "new_password", "password_confirmation"}
    for error in errors:
        if error.get("type") == "password_confirmation_mismatch":
            mismatch = True
            fields["password_confirmation"] = "password_confirmation_mismatch"
            continue
        location = error.get("loc", ())
        if len(location) != 2 or location[0] != "body" or location[1] not in allowed_fields:
            continue
        kind = error.get("type")
        if kind == "missing":
            code = "required"
        elif kind in ("string_too_short", "string_too_long"):
            code = "password_length"
        else:
            code = "invalid_type"
        fields[location[1]] = code
    if mismatch:
        return {"code": "password_confirmation_mismatch", "fields": fields}
    return {"code": "validation_error", **({"fields": fields} if fields else {})}


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
    try:
        user = service.authenticate(body.email, body.password)
    except AccountDisabledError:
        raise HTTPException(
            status_code=403, detail={"code": "account_disabled"},
        ) from None
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


@router.post("/password", status_code=204)
def change_password(
    body: ChangePasswordRequest,
    request: Request,
    user_id: str = Depends(get_authenticated_user_id),
    db: Session = Depends(get_session),
) -> Response:
    """POST /auth/password: current/new/confirmation + session/CSRF -> 204."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail={"code": "authentication_required"})
    try:
        verify_csrf(request, user_id, db)
        AuthService(db).change_password(user_id, token, body)
    except HTTPException as error:
        if error.status_code == 401:
            raise HTTPException(
                status_code=401, detail={"code": "authentication_required"}
            ) from None
        if error.status_code == 403:
            raise HTTPException(status_code=403, detail={"code": "csrf_invalid"}) from None
        raise
    except PasswordChangeError as error:
        if error.code == "authentication_required":
            raise HTTPException(status_code=401, detail={"code": error.code}) from None
        if error.code == "current_password_incorrect":
            raise HTTPException(status_code=422, detail={
                "code": error.code,
                "fields": {"current_password": error.code},
            }) from None
        if error.code == "password_unchanged":
            raise HTTPException(status_code=422, detail={
                "code": error.code,
                "fields": {"new_password": error.code},
            }) from None
        if error.code == "password_confirmation_mismatch":
            raise HTTPException(status_code=422, detail={
                "code": error.code,
                "fields": {"password_confirmation": error.code},
            }) from None
        raise HTTPException(status_code=503, detail={"code": "password_change_unavailable"}) from None
    except (RequestValidationError, ValidationError) as error:
        raise HTTPException(
            status_code=422,
            detail=_password_validation_detail(error.errors()),
        ) from None
    except Exception:
        raise HTTPException(
            status_code=503, detail={"code": "password_change_unavailable"}
        ) from None
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


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
