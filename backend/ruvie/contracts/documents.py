from pydantic import BaseModel


class RetrievalBody(BaseModel):
    """Retrieval JSON: {query, limit?}; identity/access are resolved by the server."""
    query: str
    limit: int = 10
