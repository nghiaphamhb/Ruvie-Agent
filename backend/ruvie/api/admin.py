"""Protected account administration HTTP boundary; account rules stay in the service."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from ruvie.api.security import AccountCreationRoute, account_validation_detail, verify_csrf
from ruvie.contracts.admin import (
    AccountLookupRequest, AccountLookupResponse, CreateAccountRequest, CreateAccountResponse,
    AccountListRequest, AccountListResponse, AdminAccountSummary, UpdateAccountRequest,
)
from ruvie.dependencies import get_admin_user_id, get_session
from ruvie.services.admin import (
    AccountNotFound, AdminAccountService, AdminRequired, AuthenticationRequired, EmailTaken,
    LastActiveAdmin,
)


class AdminRoute(AccountCreationRoute):
    """Redact every admin error and forbid caching account metadata, including failed requests."""
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def safe_admin(request: Request):
            try:
                response = await handler(request)
            except (RequestValidationError, ValidationError) as error:
                response = JSONResponse(status_code=422, content={"detail": account_validation_detail(error.errors())})
            except AuthenticationRequired:
                response = JSONResponse(status_code=401, content={"detail": {"code": "authentication_required"}})
            except AdminRequired:
                response = JSONResponse(status_code=403, content={"detail": {"code": "admin_required"}})
            except EmailTaken:
                response = JSONResponse(status_code=409, content={
                    "detail": {"code": "email_taken", "fields": {"email": "email_taken"}},
                })
            except AccountNotFound:
                response = JSONResponse(status_code=404, content={
                    "detail": {"code": "account_not_found"},
                })
            except LastActiveAdmin:
                response = JSONResponse(status_code=409, content={
                    "detail": {"code": "last_active_admin"},
                })
            except HTTPException as error:
                response = JSONResponse(status_code=error.status_code, content={"detail": error.detail})
            except Exception:
                # No SQL parameters, credentials or exception text may leave this boundary.
                operation = {"POST": "account_creation_failed", "PATCH": "account_update_unavailable"}.get(
                    request.method, "account_lookup_unavailable",
                )
                response = JSONResponse(status_code=500 if request.method == "POST" else 503, content={
                    "detail": {"code": operation},
                })
            response.headers["Cache-Control"] = "no-store"
            return response

        return safe_admin


router = APIRouter(prefix="/admin", tags=["admin"], route_class=AdminRoute)


def require_admin_write_access(
    request: Request,
    actor_user_id: str = Depends(get_admin_user_id),
    db: Session = Depends(get_session),
) -> str:
    """Check CSRF against the current cookie; AccountCreationRoute checks Origin before parsing."""
    try:
        verify_csrf(request, actor_user_id, db)
    except HTTPException as error:
        code = "authentication_required" if error.status_code == 401 else "csrf_invalid"
        raise HTTPException(status_code=error.status_code, detail={"code": code}) from None
    return actor_user_id


@router.post("/users", response_model=CreateAccountResponse, status_code=201)
def create_account(
    body: CreateAccountRequest,
    actor_user_id: str = Depends(require_admin_write_access),
    db: Session = Depends(get_session),
) -> CreateAccountResponse:
    """POST /admin/users: identity/password/role -> safe recipient metadata; no session cookie."""
    result = AdminAccountService(db).create_account(actor_user_id, body)
    return CreateAccountResponse(user=result.user)


@router.get("/users", response_model=AccountLookupResponse)
def lookup_account(
    query: Annotated[AccountLookupRequest, Query()],
    actor_user_id: str = Depends(get_admin_user_id),
    db: Session = Depends(get_session),
) -> AccountLookupResponse:
    """GET /admin/users?email=...: exact normalized email -> zero or one safe summary."""
    return AdminAccountService(db).lookup_account(actor_user_id, query.email)


@router.get("/users/list", response_model=AccountListResponse)
def list_accounts(
    query: Annotated[AccountListRequest, Query()],
    actor_user_id: str = Depends(get_admin_user_id),
    db: Session = Depends(get_session),
) -> AccountListResponse:
    """GET /admin/users/list?q=an&page=1&page_size=20 -> users/total/page/page_size."""
    return AdminAccountService(db).list_accounts(actor_user_id, query)


@router.get("/users/{account_id}", response_model=CreateAccountResponse)
def get_account(
    account_id: str,
    actor_user_id: str = Depends(get_admin_user_id),
    db: Session = Depends(get_session),
) -> CreateAccountResponse:
    """GET /admin/users/{id}: read one safe account summary for reconciliation."""
    return CreateAccountResponse(user=AdminAccountService(db).get_account(actor_user_id, account_id))


@router.patch("/users/{account_id}", response_model=CreateAccountResponse)
def update_account(
    account_id: str,
    body: UpdateAccountRequest,
    actor_user_id: str = Depends(require_admin_write_access),
    db: Session = Depends(get_session),
) -> CreateAccountResponse:
    """PATCH /admin/users/{id}: update identity fields with Origin, CSRF and DB-backed admin."""
    result = AdminAccountService(db).update_account(actor_user_id, account_id, body)
    return CreateAccountResponse(user=result)
