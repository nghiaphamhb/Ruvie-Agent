"""Account administration contracts; request roles describe the recipient, not the actor."""
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.types import AwareDatetime

from ruvie.contracts.auth import RegisterRequest, SystemRole


class CreateAccountRequest(RegisterRequest):
    """Reuse identity/password validation; an authorized admin selects the recipient role."""
    system_role: SystemRole = "user"


class AccountLookupRequest(BaseModel):
    """One exact email, normalized and validated with the account creation rules."""
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)
    email: str = Field(min_length=3, max_length=320)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return RegisterRequest.validate_email(value)


class AccountListRequest(BaseModel):
    """Bounded admin search; URL parameters are parsed before service execution."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, hide_input_in_errors=True)
    q: str = Field(default="", max_length=255)
    page: int = Field(default=1, ge=1, le=1_000_000)
    page_size: int = Field(default=20, ge=1, le=100)


class UpdateAccountRequest(BaseModel):
    """Partial identity, role and optional password reset; activity stays server-owned."""
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: str | None = Field(default=None, min_length=3, max_length=320)
    system_role: SystemRole | None = None
    password: str | None = Field(default=None, min_length=12, max_length=128, repr=False)

    @field_validator("display_name", "email", mode="before")
    @classmethod
    def normalize_identity(cls, value, info):
        if not isinstance(value, str):
            return value
        return value.strip().lower() if info.field_name == "email" else value.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        return RegisterRequest.validate_email(value) if value is not None else value

    @model_validator(mode="after")
    def require_non_null_change(self):
        if not self.model_fields_set or any(
            getattr(self, field) is None for field in self.model_fields_set
        ):
            raise ValueError("at least one non-null identity field is required")
        return self


class AdminAccountSummary(BaseModel):
    """Allowlisted metadata from an account; credentials and session secrets are excluded."""
    model_config = ConfigDict(from_attributes=True, strict=True)
    id: str
    display_name: str
    email: str
    system_role: SystemRole
    is_active: bool
    created_at: AwareDatetime

    @field_validator("created_at", mode="before")
    @classmethod
    def normalize_naive_created_at(cls, value):
        """Treat timezone-naive database test values as UTC before serialization."""
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class CreateAccountResponse(BaseModel):
    """Creation result only; this response never establishes the recipient's session."""
    user: AdminAccountSummary


class AccountLookupResponse(BaseModel):
    """An exact-email lookup returns zero or one safe account summary."""
    users: list[AdminAccountSummary] = Field(max_length=1)


class AccountPresence(BaseModel):
    """Server-observed activity; account enablement remains separate."""
    is_online: bool
    last_active_at: AwareDatetime | None


class AccountListResponse(BaseModel):
    """One page of allowlisted metadata and the number of matching accounts."""
    users: list[AdminAccountSummary] = Field(max_length=100)
    total: int = Field(ge=0)
    page: int = Field(ge=1, le=1_000_000)
    page_size: int = Field(ge=1, le=100)
    presence: dict[str, AccountPresence] = Field(default_factory=dict)
