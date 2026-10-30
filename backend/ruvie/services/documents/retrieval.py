"""Document search use case: embedding followed by default-deny retrieval."""
import httpx
from ruvie.services.retrieval import AuthorizedRetrievalService
from ruvie.services.embedding import EmbeddingUnavailableError


class DocumentRetrievalService:
    """Return only readable hits; the API owns response serialization."""
    def __init__(self, session, embedder):
        self.session, self.embedder = session, embedder

    def retrieve(self, user_id, query, limit):
        """Embed one query using the operation snapshot and enforce document ACLs in SQL."""
        try:
            vector = self.embedder.embed_query(query)
        except (httpx.HTTPError, ValueError):
            raise EmbeddingUnavailableError('embedding_provider_unavailable') from None
        return AuthorizedRetrievalService(self.session).retrieve(user_id, vector, limit=limit)
