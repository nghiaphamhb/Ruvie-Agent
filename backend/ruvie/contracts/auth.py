import re
from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoginRequest(BaseModel):
    """Login JSON: {email, password}; reject extra fields."""
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)


class RegisterRequest(BaseModel):
    """Registration identity only; passwords are preserved exactly, including spaces."""
    model_config = ConfigDict(extra="forbid", strict=True)
    display_name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("display_name", "email", mode="before")
    @classmethod
    def normalize_identity(cls, value, info):
        if not isinstance(value, str):
            return value
        return value.strip().lower() if info.field_name == "email" else value.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        # Full match, unlike the legacy prefix regex: trailing text/whitespace is rejected.
        pattern = r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+"
        if re.fullmatch(pattern, value) is None:
            raise ValueError("invalid_email")
        return value


class AuthUser(BaseModel):
    id: str
    display_name: str


class AuthResponse(BaseModel):
    """Public login/session response: {user: {id, display_name}, csrf_token}."""
    user: AuthUser
    csrf_token: str
