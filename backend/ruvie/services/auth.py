import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ruvie.models import AuthSession, User


SESSION_HOURS = 12


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


class AuthService:
    def __init__(self, session: Session):
        self.session = session

    def authenticate(self, email: str, password: str) -> User | None:
        """Return an active user with a matching password, or None for invalid credentials."""
        user = self.session.scalar(select(User).where(func.lower(User.email) == email.strip().casefold()))
        if not user or not user.is_active or not user.password_hash:
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

    def create_session(self, user_id: str) -> CreatedSession:
        """Generate cookie/CSRF secrets, store the token hash, and return the new session."""
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)
        self.session.add(AuthSession(
            id=str(uuid4()), user_id=user_id, token_hash=hashlib.sha256(token.encode()).hexdigest(),
            csrf_token=csrf, expires_at=expires,
        ))
        self.session.commit()
        return CreatedSession(token, csrf, expires)

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
