from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)


class AuthUser(BaseModel):
    id: str
    display_name: str


class AuthResponse(BaseModel):
    user: AuthUser
    csrf_token: str
