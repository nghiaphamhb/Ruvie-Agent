from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session

from ruvie.config import Settings
from ruvie.services.auth import AuthService


def account_validation_detail(errors) -> dict:
    """Reduce body/query/contract validation issues to allowlisted field and error codes."""
    fields = {}
    for issue in errors:
        location = issue.get("loc", ())
        field = None
        if len(location) == 2 and location[0] in ("body", "query"):
            field = location[1]
        elif len(location) == 1:
            field = location[0]
        if field not in ("display_name", "email", "password", "system_role"):
            continue
        kind = issue["type"]
        code = "invalid_type"
        if kind == "missing":
            code = "required"
        elif kind in ("string_too_short", "string_too_long"):
            code = {"display_name": "name_length", "email": "email_length",
                    "password": "password_length"}.get(field, "invalid_type")
        elif kind == "value_error" and field == "email":
            code = "invalid_email"
        elif kind == "literal_error" and field == "system_role":
            code = "invalid_role"
        elif kind == "extra_forbidden":
            code = "unexpected_field"
        fields[field] = code
    # Never serialize input, context, arbitrary field names or exception text.
    detail = {"code": "validation_error"}
    if fields:
        detail["fields"] = fields
    return detail


class AccountCreationRoute(APIRoute):
    """Protect account writes from untrusted origins and reflected validation input."""
    def get_route_handler(self):
        """Check Origin before parsing; return only allowlisted field/error codes."""
        handler = super().get_route_handler()
        if not self.methods.intersection({"POST", "PATCH"}):
            return handler

        async def safe_account_creation(request: Request):
            try:
                check_origin(request, request.app.state.settings)
            except HTTPException:
                return JSONResponse(status_code=403, content={"detail": {"code": "origin_not_allowed"}})
            try:
                return await handler(request)
            except RequestValidationError as error:
                return JSONResponse(status_code=422, content={"detail": account_validation_detail(error.errors())})

        return safe_account_creation


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
