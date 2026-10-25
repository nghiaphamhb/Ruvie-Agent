"""Account administration use cases; HTTP identity/security belong to the API layer."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ruvie.contracts.admin import (
    AccountLookupRequest, AccountLookupResponse, AdminAccountSummary, CreateAccountRequest,
    AccountListRequest, AccountListResponse, AccountPresence, UpdateAccountRequest,
)
from ruvie.models import AuthSession, User
from ruvie.services.audit import AuditEventWriter
from ruvie.services.auth import hash_password, PRESENCE_SECONDS


class AuthenticationRequired(PermissionError):
    """The trusted actor no longer exists or is inactive."""
    def __init__(self):
        super().__init__("authentication_required")


class AdminRequired(PermissionError):
    """An active actor lacks the system administrator role."""
    def __init__(self):
        super().__init__("admin_required")


class EmailTaken(ValueError):
    """An existing active or inactive account owns the normalized email."""
    def __init__(self):
        super().__init__("email_taken")


class AccountNotFound(LookupError):
    """The requested account ID does not exist."""
    def __init__(self):
        super().__init__("account_not_found")


class LastActiveAdmin(ValueError):
    """Refusing a change that would leave the application without an active admin."""
    def __init__(self):
        super().__init__("last_active_admin")


@dataclass(frozen=True)
class CreatedAccount:
    """Committed safe metadata; contains no ORM credentials or session secrets."""
    user: AdminAccountSummary


class AdminAccountService:
    """Create or inspect accounts using a trusted actor ID and database-backed rights."""
    def __init__(self, session: Session):
        self.session = session

    def require_admin(self, actor_user_id: str, *, lock: bool = False) -> User:
        """Reload the active admin; optionally lock their row until the caller ends the transaction."""
        # Refresh even an identity-map hit: a previously read role is not authorization.
        statement = select(User).where(User.id == actor_user_id).execution_options(populate_existing=True)
        if lock:
            statement = statement.with_for_update()
        actor = self.session.scalar(statement)
        if actor is None or not actor.is_active:
            raise AuthenticationRequired()
        if actor.system_role != "admin":
            raise AdminRequired()
        return actor

    def create_account(self, actor_user_id: str, command: CreateAccountRequest) -> CreatedAccount:
        """Commit a new active user/admin plus audit; never establish a recipient session or grants."""
        try:
            # The lock prevents role/activity changes between authorization and commit.
            actor = self.require_admin(actor_user_id, lock=True)
            # Revalidate because internal callers can mutate a previously validated model.
            body = CreateAccountRequest.model_validate(command.model_dump(warnings=False))
            existing = self.session.scalar(select(User.id).where(func.lower(User.email) == body.email))
            if existing is not None:
                raise EmailTaken()
            user = User(
                id=str(uuid4()), display_name=body.display_name, email=body.email,
                password_hash=hash_password(body.password), system_role=body.system_role, is_active=True,
            )
            self.session.add(user)
            self.session.flush()
            AuditEventWriter.append(
                self.session, actor.id, action="account.create", resource_type="user",
                resource_id=user.id, outcome="allow", reason=f"created_as_{body.system_role}",
            )
            # Snapshot only public fields before commit expires the ORM objects.
            summary = AdminAccountSummary.model_validate(user)
            self.session.commit()
            return CreatedAccount(user=summary)
        except IntegrityError as error:
            self.session.rollback()
            constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            # Prechecks do not prevent races; PostgreSQL's email constraints decide the winner.
            if constraint in ("uq_users_email_lower", "users_email_key"):
                raise EmailTaken() from None
            raise
        except Exception:
            self.session.rollback()
            raise

    def lookup_account(self, actor_user_id: str, email: str) -> AccountLookupResponse:
        """Return zero or one safe summary for an exact email, after rechecking admin rights."""
        self.require_admin(actor_user_id)
        body = AccountLookupRequest(email=email)
        user = self.session.scalar(select(User).where(func.lower(User.email) == body.email)
                                   .execution_options(populate_existing=True))
        users = [] if user is None else [AdminAccountSummary.model_validate(user)]
        return AccountLookupResponse(users=users)

    def get_account(self, actor_user_id: str, account_id: str) -> AdminAccountSummary:
        """Read one account by ID after rechecking the actor's current database role."""
        self.require_admin(actor_user_id)
        user = self.session.scalar(select(User).where(User.id == account_id))
        if user is None:
            raise AccountNotFound()
        return AdminAccountSummary.model_validate(user)

    def update_account(self, actor_user_id: str, account_id: str,
                       command: UpdateAccountRequest) -> AdminAccountSummary:
        """Update supplied account fields, revoke reset sessions, and audit atomically."""
        try:
            body = UpdateAccountRequest.model_validate(command.model_dump(exclude_unset=True))
            # Serialize role demotions before authorization/row locks. The actor role is
            # reloaded after acquiring this lock, so concurrent cross-demotions cannot
            # both pass with stale admin identities.
            if body.system_role == "user" and self.session.bind.dialect.name == "postgresql":
                self.session.execute(select(func.pg_advisory_xact_lock(0x52555649, 13)))
            actor = self.require_admin(actor_user_id, lock=True)
            if not body.model_fields_set:
                raise ValueError("empty_update")
            user = self.session.scalar(select(User).where(User.id == account_id).with_for_update())
            if user is None:
                raise AccountNotFound()
            if (body.system_role == "user" and user.system_role == "admin" and user.is_active
                    and self.session.scalar(select(func.count()).select_from(User).where(
                        User.system_role == "admin", User.is_active.is_(True),
                    )) <= 1):
                raise LastActiveAdmin()
            if body.email is not None and body.email != user.email.lower():
                existing = self.session.scalar(select(User.id).where(
                    func.lower(User.email) == body.email, User.id != user.id,
                ))
                if existing is not None:
                    raise EmailTaken()
            changed_fields = []
            if body.display_name is not None and body.display_name != user.display_name:
                user.display_name = body.display_name
                changed_fields.append("display_name")
            if body.email is not None and body.email != user.email.lower():
                user.email = body.email
                changed_fields.append("email")
            if body.system_role is not None and body.system_role != user.system_role:
                user.system_role = body.system_role
                changed_fields.append("system_role")
            if body.password is not None:
                user.password_hash = hash_password(body.password)
                self.session.execute(
                    AuthSession.__table__.delete().where(AuthSession.user_id == user.id)
                )
                changed_fields.append("password")
            if changed_fields:
                self.session.flush()
                AuditEventWriter.append(
                    self.session, actor.id, action="account.update", resource_type="user",
                    resource_id=user.id, outcome="allow", reason="updated_" + "_and_".join(changed_fields),
                )
            summary = AdminAccountSummary.model_validate(user)
            self.session.commit()
            return summary
        except IntegrityError as error:
            self.session.rollback()
            constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            if constraint in ("uq_users_email_lower", "users_email_key"):
                raise EmailTaken() from None
            raise
        except Exception:
            self.session.rollback()
            raise

    def list_accounts(self, actor_user_id: str, query: AccountListRequest) -> AccountListResponse:
        """List safe account metadata for a fresh database-verified admin, with filtered totals."""
        self.require_admin(actor_user_id)
        query = AccountListRequest.model_validate(query.model_dump())
        # Select public columns only; never load password hashes for a listing.
        statement = select(User.id, User.display_name, User.email, User.system_role,
                           User.is_active, User.created_at, User.last_active_at)
        if query.q:
            # Escape SQL LIKE wildcards: user input describes a literal substring.
            statement = statement.where(or_(
                User.display_name.icontains(query.q, autoescape=True),
                User.email.icontains(query.q, autoescape=True),
            ))
        total = self.session.scalar(select(func.count()).select_from(statement.subquery()))
        rows = list(self.session.execute(
            statement.order_by(User.created_at.desc(), User.id.asc())
            .offset((query.page - 1) * query.page_size).limit(query.page_size)
        ).mappings())
        now = datetime.now(timezone.utc)
        online = set(self.session.scalars(select(AuthSession.user_id).where(
            AuthSession.user_id.in_([row["id"] for row in rows]),
            AuthSession.expires_at > now,
            AuthSession.last_seen_at > now - timedelta(seconds=PRESENCE_SECONDS),
        ).distinct())) if rows else set()
        presence = {}
        for row in rows:
            last_active = row["last_active_at"]
            if last_active is not None and last_active.tzinfo is None:
                last_active = last_active.replace(tzinfo=timezone.utc)
            presence[row["id"]] = AccountPresence(
                is_online=row["is_active"] and row["id"] in online, last_active_at=last_active,
            )
        return AccountListResponse(
            users=[AdminAccountSummary.model_validate(row) for row in rows],
            total=total, page=query.page, page_size=query.page_size,
            presence=presence,
        )
