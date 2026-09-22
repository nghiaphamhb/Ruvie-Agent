from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ruvie.document_access import DocumentAccessService
from ruvie.document_audit import DocumentRetrievalAuditWriter
from ruvie.domain import Document, DocumentChunk, DocumentRevision, RevisionIngestionState


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
        document = session.scalar(DocumentAccessService.readable_documents_statement(session, user_id).where(Document.id == document_id))
        DocumentRetrievalAuditWriter.append(session, user_id, document_id, "allow" if document else "deny", "authorized" if document else "not authorized", document.project_id if document else None)
        return document


class PgvectorChunkRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def search(self, scope: AuthorizedScope, query_embedding: list[float], *, limit: int = 10) -> list[DocumentChunk]:
        if len(query_embedding) != 1024 or limit <= 0:
            raise ValueError("query embedding must have 1024 dimensions and limit must be positive")
        readable = DocumentAccessService.readable_documents_statement(self.session, scope.user_id).with_only_columns(Document.id)
        statement = select(DocumentChunk).join(DocumentRevision, DocumentChunk.document_revision_id == DocumentRevision.id).where(DocumentChunk.document_id.in_(readable), DocumentRevision.ingestion_state == RevisionIngestionState.READY)
        if self.session.get_bind().dialect.name == "postgresql":
            statement = statement.order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
        else:
            statement = statement.order_by(DocumentChunk.ordinal)
        return list(self.session.scalars(statement.limit(limit)))
