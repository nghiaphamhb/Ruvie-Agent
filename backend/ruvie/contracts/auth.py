from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """Login JSON: {email, password}; reject extra fields."""
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)


class AuthUser(BaseModel):
    id: str
    display_name: str


class AuthResponse(BaseModel):
    """Public login/session response: {user: {id, display_name}, csrf_token}."""
    user: AuthUser
    csrf_token: str
