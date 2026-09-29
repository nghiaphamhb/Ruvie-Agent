from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from ruvie.document_citation import Citation, CitationBuilder
from ruvie.domain import Document, DocumentChunk, DocumentRevision, RevisionIngestionState
from ruvie.services.access import DocumentAccessService
from ruvie.services.audit import DocumentRetrievalAuditWriter


@dataclass(frozen=True)
class AuthorizedScope:
    user_id: str

    @classmethod
    def for_user(cls, user_id: str) -> "AuthorizedScope":
        return cls(user_id)


class DocumentRetrievalService:
    @staticmethod
    def retrieve_documents(session: Session, user_id: str) -> list[Document]:
        return list(session.scalars(DocumentAccessService.readable_documents_statement(session, user_id)))

    @staticmethod
    def retrieve_document(session: Session, user_id: str, document_id: str) -> Document | None:
        document = session.scalar(
            DocumentAccessService.readable_documents_statement(session, user_id).where(Document.id == document_id)
        )
        DocumentRetrievalAuditWriter.append(
            session,
            user_id,
            document_id,
            "allow" if document else "deny",
            "authorized" if document else "not authorized",
            document.project_id if document else None,
        )
        return document


class PgvectorChunkRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def search(self, scope: AuthorizedScope, query_embedding: list[float], *, limit: int = 10) -> list[DocumentChunk]:
        if len(query_embedding) != 1024 or limit <= 0:
            raise ValueError("query embedding must have 1024 dimensions and limit must be positive")
        readable = DocumentAccessService.readable_documents_statement(
            self.session, scope.user_id
        ).with_only_columns(Document.id)
        statement = select(DocumentChunk).join(
            DocumentRevision, DocumentChunk.document_revision_id == DocumentRevision.id
        ).where(
            DocumentChunk.document_id.in_(readable),
            DocumentRevision.ingestion_state == RevisionIngestionState.READY,
        )
        if self.session.get_bind().dialect.name == "postgresql":
            statement = statement.order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
        else:
            statement = statement.order_by(DocumentChunk.ordinal)
        return list(self.session.scalars(statement.limit(limit)))


@dataclass(frozen=True)
class RetrievalHit:
    chunk_id: str
    document_id: str
    text: str
    citation: Citation


class AuthorizedRetrievalService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def retrieve(self, user_id: str, query_embedding: list[float], *, limit: int = 10) -> list[RetrievalHit]:
        chunks = PgvectorChunkRepository(self.session).search(
            AuthorizedScope.for_user(user_id), query_embedding, limit=limit
        )
        hits = [self._build_hit(chunk) for chunk in chunks]
        self._append_audit(user_id, hits)
        self.session.commit()
        return hits

    def _build_hit(self, chunk: DocumentChunk) -> RetrievalHit:
        document = self.session.get(Document, chunk.document_id)
        revision = self.session.get(DocumentRevision, chunk.document_revision_id)
        if document is None or revision is None:
            raise RuntimeError("retrieved chunk is missing its document revision")
        citation = CitationBuilder.build(
            document.id, revision.id, chunk.id, chunk.ordinal, chunk.start_offset,
            chunk.end_offset, document.title, revision.content_hash, chunk.software,
            chunk.software_version,
        )
        return RetrievalHit(chunk.id, chunk.document_id, chunk.text, citation)

    def _append_audit(self, user_id: str, hits: list[RetrievalHit]) -> None:
        if hits:
            document = self.session.get(Document, hits[0].document_id)
            if document is None:
                raise RuntimeError("retrieved chunk is missing its document")
            DocumentRetrievalAuditWriter.append(
                self.session, user_id, document.id, "allow", "authorized results", document.project_id
            )
            return
        DocumentRetrievalAuditWriter.append(
            self.session, user_id, str(uuid4()), "deny", "no authorized results"
        )
