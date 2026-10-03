from pydantic import BaseModel


class RetrievalBody(BaseModel):
    query: str
    limit: int = 10
