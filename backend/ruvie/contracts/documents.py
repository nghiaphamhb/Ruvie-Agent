from pydantic import BaseModel


class UploadBody(BaseModel):
    project_id: str
    title: str
    filename: str
    content_base64: str
    mime_type: str
    software: str
    software_version: str
    allowed_role_codes: list[str]


class RetrievalBody(BaseModel):
    query: str
    limit: int = 10
