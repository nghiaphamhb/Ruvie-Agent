import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from ruvie.contracts.auth import ChangePasswordRequest, RegisterRequest

from ruvie.models import AuthSession, User
from ruvie.services.audit import AuditEventWriter


SESSION_HOURS = 12
PRESENCE_SECONDS = 180
PRESENCE_WRITE_SECONDS = 25


def hash_password(password: str) -> str:
    """Return scrypt$N$r$p$salt$digest with a fresh random salt; never store plaintext."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt$16384$8$1${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    """Check a password against its stored scrypt record; malformed records return False."""
    try:
        algorithm, n, r, p, salt_hex, digest_hex = encoded.split("$")
        if algorithm != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt_hex), n=int(n), r=int(r), p=int(p), dklen=len(bytes.fromhex(digest_hex))
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError, MemoryError):
        return False


@dataclass(frozen=True)
class CreatedSession:
    """New session secrets returned to the login route; store only the cookie token hash."""
    token: str
    csrf_token: str
    expires_at: datetime


@dataclass(frozen=True)
class ResolvedSession:
    """Active user and CSRF token after validating the session cookie."""
    user: User
    csrf_token: str


@dataclass(frozen=True)
class RegisteredAccount:
    """Committed user and session secrets; HTTP serialization belongs to the route."""
    user: User
    created_session: CreatedSession


class AccountDisabledError(ValueError):
    """Login rejected because the account exists but is deactivated."""


class SetupAlreadyCompleted(ValueError):
    """Any existing account closes public bootstrap, regardless of role or activity."""
    def __init__(self):
        super().__init__("setup_already_completed")


class PasswordChangeError(ValueError):
    """A safe self-service password failure identified by a stable internal code."""
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ChangedPasswordResult:
    """Safe result for the actor; contains no credential or session secret."""
    user_id: str


class AuthService:
    def __init__(self, session: Session):
        self.session = session

    def authenticate(self, email: str, password: str) -> User | None:
        """Return an active user with a matching password, or None for invalid credentials.

        Raises AccountDisabledError when the password is correct but the account
        is deactivated.  The password check runs first so that an incorrect
        password never reveals whether the email exists (anti-enumeration).
        """
        # Hold the account row through create_session's commit so an admin reset
        # cannot race a successful login and leave a freshly minted old-password session.
        user = self.session.scalar(
            select(User).where(func.lower(User.email) == email.strip().casefold()).with_for_update()
        )
        if not user or not user.password_hash:
            return None
        if not user.is_active:
            # Only reveal disabled status when the password is correct.
            if verify_password(password, user.password_hash):
                raise AccountDisabledError()
            return None
        return user if verify_password(password, user.password_hash) else None

    def set_existing_user_password(self, email: str, password: str) -> bool:
        """Update/commit a password hash for an existing email; return whether it exists."""
        user = self.session.scalar(select(User).where(func.lower(User.email) == email.strip().casefold()))
        if user is None:
            return False
        user.password_hash = hash_password(password)
        self.session.commit()
        return True

    def change_password(
        self,
        actor_user_id: str,
        session_token: str,
        command: ChangePasswordRequest,
    ) -> ChangedPasswordResult:
        """Change the actor's password, preserve this active session and revoke their others."""
        try:
            # Match login, presence and admin-reset lock order: account, then session.
            actor = self.session.scalar(
                select(User).where(User.id == actor_user_id)
                .execution_options(populate_existing=True).with_for_update()
            )
            if actor is None or not actor.is_active:
                raise PasswordChangeError("authentication_required")

            token_hash = hashlib.sha256(session_token.encode()).hexdigest()
            current_session = self.session.scalar(
                select(AuthSession).where(
                    AuthSession.user_id == actor_user_id,
                    AuthSession.token_hash == token_hash,
                ).execution_options(populate_existing=True).with_for_update()
            )
            if current_session is None:
                raise PasswordChangeError("authentication_required")

            expires_at = current_session.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at <= datetime.now(timezone.utc):
                raise PasswordChangeError("authentication_required")

            # Revalidate even when an internal caller bypasses the HTTP contract.
            body = ChangePasswordRequest.model_validate(command.model_dump())
            if not actor.password_hash or not verify_password(body.current_password, actor.password_hash):
                raise PasswordChangeError("current_password_incorrect")
            if body.new_password == body.current_password:
                raise PasswordChangeError("password_unchanged")

            actor.password_hash = hash_password(body.new_password)
            self.session.execute(
                AuthSession.__table__.delete().where(
                    AuthSession.user_id == actor_user_id,
                    AuthSession.id != current_session.id,
                )
            )
            AuditEventWriter.append(
                self.session,
                actor_user_id,
                action="account.password_change",
                resource_type="user",
                resource_id=actor_user_id,
                outcome="allow",
                reason="self_service",
            )
            self.session.commit()
            return ChangedPasswordResult(user_id=actor_user_id)
        except Exception:
            self.session.rollback()
            raise

    def get_setup_status(self) -> bool:
        """Return whether there are no accounts; database errors propagate to the caller."""
        return self.session.scalar(select(User.id).limit(1)) is None

    def register(self, display_name: str, email: str, password: str) -> RegisteredAccount:
        """Bootstrap one admin, session and audit atomically, without resource grants."""
        body = RegisterRequest(display_name=display_name, email=email, password=password)
        try:
            # Shared across processes, held until commit/rollback. Check emptiness only
            # after the lock: different emails must not create multiple first admins.
            # PostgreSQL is the system of record; SQLite serves serial unit tests only.
            if self.session.get_bind().dialect.name == "postgresql":
                self.session.execute(select(func.pg_advisory_xact_lock(0x52555649, 12)))
            if not self.get_setup_status():
                raise SetupAlreadyCompleted()
            user = User(id=str(uuid4()), display_name=body.display_name, email=body.email,
                        password_hash=hash_password(body.password), is_active=True, system_role="admin")
            self.session.add(user)
            # Flush the parent row before its FK-dependent session; neither write is committed yet.
            self.session.flush()
            created = self._stage_session(user.id)
            AuditEventWriter.append(
                self.session, user.id, action="account.bootstrap", resource_type="user",
                resource_id=user.id, outcome="allow", reason="created_as_admin",
            )
            self.session.commit()
            return RegisteredAccount(user=user, created_session=created)
        except Exception:
            self.session.rollback()
            raise

    def create_session(self, user_id: str) -> CreatedSession:
        """Commit a session for an existing user, preserving the login contract."""
        created = self._stage_session(user_id)
        self.session.commit()
        return created

    def _stage_session(self, user_id: str) -> CreatedSession:
        """Add a session without committing; registration owns the shared transaction."""
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=SESSION_HOURS)
        self.session.add(AuthSession(
            id=str(uuid4()), user_id=user_id, token_hash=hashlib.sha256(token.encode()).hexdigest(),
            csrf_token=csrf, expires_at=expires, last_seen_at=now,
        ))
        self._record_activity(user_id, now)
        return CreatedSession(token, csrf, expires)

    def _record_activity(self, user_id: str, now: datetime) -> None:
        """Keep activity monotonic when two sessions heartbeat concurrently."""
        self.session.execute(update(User).where(
            User.id == user_id,
            or_(User.last_active_at.is_(None), User.last_active_at < now),
        ).values(last_active_at=now).execution_options(synchronize_session=False))

    def touch_presence(self, token: str, user_id: str) -> bool:
        """Refresh only the trusted cookie session; throttle tabs sharing that cookie."""
        now = datetime.now(timezone.utc)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        # Match password-reset lock order (user, then sessions) to avoid cross-request deadlocks.
        if self.session.scalar(select(User.id).where(
            User.id == user_id, User.is_active.is_(True),
        ).with_for_update()) is None:
            return False
        valid = (
            AuthSession.token_hash == token_hash,
            AuthSession.user_id == user_id,
            AuthSession.expires_at > now,
            select(User.id).where(User.id == user_id, User.is_active.is_(True)).exists(),
        )
        changed = self.session.execute(update(AuthSession).where(
            *valid,
            or_(AuthSession.last_seen_at.is_(None),
                AuthSession.last_seen_at <= now - timedelta(seconds=PRESENCE_WRITE_SECONDS)),
        ).values(last_seen_at=now).execution_options(synchronize_session=False))
        if changed.rowcount:
            self._record_activity(user_id, now)
        elif self.session.scalar(select(AuthSession.id).where(*valid)) is None:
            self.session.rollback()
            return False
        self.session.commit()
        return True

    def resolve_session(self, token: str) -> ResolvedSession | None:
        """Resolve a cookie token; remove expired sessions and reject inactive users."""
        # The browser holds the raw token; database lookup uses only its SHA-256 hash.
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        record = self.session.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash))
        if record is None:
            return None
        expires_at = record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            self.session.delete(record)
            self.session.commit()
            return None
        user = self.session.get(User, record.user_id)
        if user is None or not user.is_active:
            return None
        return ResolvedSession(user, record.csrf_token)

    def revoke_session(self, token: str) -> bool:
        """Delete/commit the matching session; return False when it is already absent."""
        # The browser holds the raw token; database lookup uses only its SHA-256 hash.
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        record = self.session.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash))
        if record is None:
            return False
        self.session.delete(record)
        self.session.commit()
        return True

    @staticmethod
    def verify_csrf(expected: str, supplied: str | None) -> bool:
        """Compare CSRF secrets in constant time; a missing supplied token fails."""
        return bool(supplied) and hmac.compare_digest(expected, supplied)
