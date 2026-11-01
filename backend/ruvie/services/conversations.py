"""Private history use cases. Every resource lookup is scoped to the trusted owner."""
import base64
import json
from datetime import datetime, timezone
from dataclasses import fields
from sqlalchemy import select, update, func, or_, and_
from sqlalchemy.orm import Session
from ruvie.models import Document, DocumentChunk, DocumentRevision
from ruvie.models.chat import ChatConversation, ChatTurn, ChatGenerationAttempt, ChatAttemptSource
from ruvie.services.access import DocumentAccessService
from ruvie.services.documents.citation import Citation


class ConversationError(Exception):
    """Safe service failure; HTTP encoding belongs to the API."""
    def __init__(self, status: int, code: str, **resources):
        super().__init__(code)
        self.status, self.code, self.resources = status, code, resources


def encode_cursor(value: list) -> str:
    return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip('=')


def decode_cursor(value: str) -> list:
    try:
        if len(value) > 1024:
            raise ValueError
        result = json.loads(base64.b64decode(value + '=' * (-len(value) % 4), altchars=b'-_', validate=True))
        if not isinstance(result, list):
            raise ValueError
        return result
    except (ValueError, TypeError, UnicodeError):
        raise ConversationError(422, 'invalid_cursor') from None


class ConversationService:
    """Read and mutate history using short caller-owned database sessions."""
    def __init__(self, session: Session):
        self.db = session

    @staticmethod
    def metadata(chat: ChatConversation) -> dict:
        return dict(id=chat.id, title=chat.title, version=chat.version,
                    created_at=chat.created_at.isoformat(), updated_at=chat.updated_at.isoformat())

    def owned(self, owner: str, conversation_id: str, *, lock=False) -> ChatConversation:
        statement = select(ChatConversation).where(ChatConversation.id == conversation_id,
                                                   ChatConversation.owner_user_id == owner)
        if lock:
            statement = statement.with_for_update()
        chat = self.db.scalar(statement)
        if chat is None:
            raise ConversationError(404, 'conversation_not_found')
        return chat

    def recover(self, owner: str, conversation_id: str):
        """Fence abandoned attempts; a read never calls a provider to recover work."""
        now = datetime.now(timezone.utc)
        self.db.execute(update(ChatGenerationAttempt).execution_options(synchronize_session='fetch').where(
            ChatGenerationAttempt.owner_user_id == owner,
            ChatGenerationAttempt.conversation_id == conversation_id,
            ChatGenerationAttempt.state == 'generating',
            ChatGenerationAttempt.lease_expires_at <= now,
        ).values(state='interrupted', finished_at=now, error_code='generation_interrupted'))

    def list(self, owner: str, *, limit=30, cursor=None) -> dict:
        """Return metadata only, ordered by activity and ID with an owner-filtered cursor."""
        if not 1 <= limit <= 100:
            raise ConversationError(422, 'invalid_limit')
        statement = select(ChatConversation).where(ChatConversation.owner_user_id == owner)
        if cursor:
            try:
                stamp, identity = decode_cursor(cursor)
                stamp = datetime.fromisoformat(stamp)
                if not isinstance(identity, str) or stamp.tzinfo is None:
                    raise ValueError
            except (ValueError, TypeError):
                raise ConversationError(422, 'invalid_cursor') from None
            statement = statement.where(or_(ChatConversation.updated_at < stamp, and_(ChatConversation.updated_at == stamp, ChatConversation.id < identity)))
        rows = list(self.db.scalars(statement.order_by(ChatConversation.updated_at.desc(), ChatConversation.id.desc()).limit(limit + 1)))
        page = rows[:limit]
        return dict(items=[self.metadata(chat) for chat in page],
                    next_cursor=encode_cursor([page[-1].updated_at.replace(tzinfo=timezone.utc).isoformat(), page[-1].id]) if len(rows) > limit else None)

    def detail(self, owner: str, conversation_id: str, *, limit=50, before=None) -> dict:
        """Load one page and batch-check source access before exposing assistant content."""
        chat = self.owned(owner, conversation_id, lock=True)
        if not 1 <= limit <= 100:
            raise ConversationError(422, 'invalid_limit')
        self.recover(owner, conversation_id)
        statement = select(ChatTurn).where(ChatTurn.conversation_id == chat.id)
        if before:
            try:
                scope, ordinal = decode_cursor(before)
                if scope != chat.id or type(ordinal) is not int or ordinal < 1:
                    raise ValueError
            except (ValueError, TypeError):
                raise ConversationError(422, 'invalid_cursor') from None
            statement = statement.where(ChatTurn.ordinal < ordinal)
        rows = list(self.db.scalars(statement.order_by(ChatTurn.ordinal.desc()).limit(limit + 1)))
        page = list(reversed(rows[:limit]))
        turn_ids = [turn.id for turn in page]
        latest = select(func.max(ChatGenerationAttempt.ordinal)).where(
            ChatGenerationAttempt.turn_id == ChatTurn.id).correlate(ChatTurn).scalar_subquery()
        attempts = {attempt.turn_id: attempt for attempt in self.db.scalars(
            select(ChatGenerationAttempt).join(ChatTurn, ChatTurn.id == ChatGenerationAttempt.turn_id).where(
                ChatTurn.id.in_(turn_ids), ChatGenerationAttempt.ordinal == latest))}
        sources = list(self.db.scalars(select(ChatAttemptSource).where(
            ChatAttemptSource.attempt_id.in_([attempt.id for attempt in attempts.values()])).order_by(ChatAttemptSource.ordinal)))
        readable = DocumentAccessService.readable_documents_statement(self.db, owner).with_only_columns(Document.id)
        # A retained ID is not proof that a source exists or is still readable.
        verified = set(self.db.execute(select(DocumentChunk.document_id,
                    DocumentChunk.document_revision_id, DocumentChunk.id).join(
                    DocumentRevision, DocumentRevision.id == DocumentChunk.document_revision_id).where(
                    DocumentChunk.id.in_([source.chunk_id for source in sources]),
                    DocumentChunk.document_id.in_(readable),
                    DocumentRevision.document_id == DocumentChunk.document_id)).all()) if sources else set()
        by_attempt = {}
        for source in sources:
            by_attempt.setdefault(source.attempt_id, []).append(source)
        turns = []
        citation_keys = {field.name for field in fields(Citation)}
        for turn in page:
            attempt = attempts.get(turn.id)
            linked = by_attempt.get(attempt.id, []) if attempt else []
            unavailable = any((source.document_id, source.revision_id, source.chunk_id) not in verified for source in linked)
            turns.append(dict(id=turn.id, ordinal=turn.ordinal, question=turn.question,
                created_at=turn.created_at.isoformat(), attempt_id=attempt.id if attempt else None,
                model_id=attempt.model_id if attempt else None, status=attempt.state if attempt else None,
                answer=attempt.answer if attempt and not unavailable else '',
                citations=[{key: value for key, value in source.citation.items() if key in citation_keys} for source in linked] if not unavailable else [],
                content_unavailable=unavailable, error_code=attempt.error_code if attempt else None,
                started_at=attempt.started_at.isoformat() if attempt else None,
                finished_at=attempt.finished_at.isoformat() if attempt and attempt.finished_at else None))
        result = dict(conversation=self.metadata(chat), turns=turns,
                      next_cursor=encode_cursor([chat.id, page[0].ordinal]) if len(rows) > limit else None)
        self.db.commit()
        return result

    def rename(self, owner: str, conversation_id: str, title: str, expected_version: int) -> dict:
        """Compare the version while holding the conversation lock, then commit the name."""
        title = title.strip()
        if not 1 <= len(title) <= 120:
            raise ConversationError(422, 'invalid_title')
        chat = self.owned(owner, conversation_id, lock=True)
        if chat.version != expected_version:
            raise ConversationError(409, 'version_conflict')
        chat.title, chat.version, chat.updated_at = title, chat.version + 1, datetime.now(timezone.utc)
        self.db.flush()
        result = self.metadata(chat)
        self.db.commit()
        return result

    def delete(self, owner: str, conversation_id: str):
        """Delete the owned graph after recovering leases and rejecting live generation."""
        chat = self.owned(owner, conversation_id, lock=True)
        self.recover(owner, chat.id)
        active = self.db.scalar(select(ChatGenerationAttempt.id).where(
            ChatGenerationAttempt.conversation_id == chat.id, ChatGenerationAttempt.state == 'generating'))
        if active:
            raise ConversationError(409, 'generation_active')
        self.db.delete(chat)
        self.db.commit()



    def recorded(self, owner: str, request_id: str, fingerprint: str):
        """Reject duplicate operations without exposing resources owned by another user."""
        attempt = self.db.scalar(select(ChatGenerationAttempt).where(
            ChatGenerationAttempt.owner_user_id == owner, ChatGenerationAttempt.request_id == request_id))
        if attempt:
            if attempt.request_fingerprint != fingerprint:
                raise ConversationError(409, 'request_conflict')
            raise ConversationError(409, 'request_already_recorded', conversation_id=attempt.conversation_id,
                                    turn_id=attempt.turn_id, attempt_id=attempt.id)

    def accept(self, owner: str, request_id: str, message: str | None, model_id: str,
               conversation_id: str | None = None, turn_id: str | None = None, *, fingerprint: str | None = None) -> dict:
        """Atomically admit a question/retry before provider work; never hold this transaction during IO."""
        import hashlib
        from uuid import uuid4
        from datetime import timedelta
        from sqlalchemy import text
        fingerprint = fingerprint or hashlib.sha256(json.dumps([conversation_id, turn_id, message, model_id],
                                                ensure_ascii=False).encode()).hexdigest()
        if self.db.get_bind().dialect.name == 'postgresql':
            # Serialize the same owner's request key across processes, including new-chat requests.
            key = int.from_bytes(hashlib.sha256((owner + ':' + request_id).encode()).digest()[:8], 'big', signed=True)
            self.db.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': key})
        chat = self.owned(owner, conversation_id, lock=True) if conversation_id else None
        self.recorded(owner, request_id, fingerprint)
        now = datetime.now(timezone.utc)
        if chat:
            self.recover(owner, chat.id)
            if self.db.scalar(select(ChatGenerationAttempt.id).where(
                ChatGenerationAttempt.conversation_id == chat.id, ChatGenerationAttempt.state == 'generating')):
                raise ConversationError(409, 'generation_active')
        else:
            if turn_id or not message or not message.strip():
                raise ConversationError(422, 'invalid_chat_request')
            chat = ChatConversation(id=str(uuid4()), owner_user_id=owner,
                                    title=' '.join(message.split())[:80], created_at=now, updated_at=now)
            self.db.add(chat)
            self.db.flush()
        if turn_id:
            turn = self.db.scalar(select(ChatTurn).where(ChatTurn.id == turn_id, ChatTurn.conversation_id == chat.id))
            if turn is None:
                raise ConversationError(404, 'turn_not_found')
        else:
            if not message or not message.strip():
                raise ConversationError(422, 'invalid_chat_request')
            ordinal = (self.db.scalar(select(func.max(ChatTurn.ordinal)).where(ChatTurn.conversation_id == chat.id)) or 0) + 1
            turn = ChatTurn(id=str(uuid4()), conversation_id=chat.id, ordinal=ordinal, question=message.strip(), created_at=now)
            self.db.add(turn)
            self.db.flush()
        ordinal = (self.db.scalar(select(func.max(ChatGenerationAttempt.ordinal)).where(ChatGenerationAttempt.turn_id == turn.id)) or 0) + 1
        attempt = ChatGenerationAttempt(id=str(uuid4()), turn_id=turn.id, conversation_id=chat.id,
                    owner_user_id=owner, request_id=request_id, request_fingerprint=fingerprint,
                    ordinal=ordinal, model_id=model_id, lease_expires_at=now + timedelta(seconds=60))
        self.db.add(attempt)
        chat.updated_at = now
        result = dict(conversation_id=chat.id, turn_id=turn.id, attempt_id=attempt.id)
        self.db.commit()
        return result

    def persist(self, owner: str, attempt_id: str, *, text='', state=None, error_code=None, citations=None) -> bool:
        """Commit a batch only while this exact attempt is live; terminal writes are fenced."""
        from datetime import timedelta
        attempt = self.db.scalar(select(ChatGenerationAttempt).where(
            ChatGenerationAttempt.id == attempt_id, ChatGenerationAttempt.owner_user_id == owner))
        if attempt is None:
            return False
        self.owned(owner, attempt.conversation_id, lock=True)
        self.recover(owner, attempt.conversation_id)
        self.db.refresh(attempt)
        if attempt.state != 'generating':
            self.db.commit()
            return False
        if citations is not None:
            if self.db.scalar(select(ChatAttemptSource.attempt_id).where(ChatAttemptSource.attempt_id == attempt.id).limit(1)):
                raise ConversationError(409, 'sources_already_recorded')
            for ordinal, citation in enumerate(citations, 1):
                self.db.add(ChatAttemptSource(attempt_id=attempt.id, ordinal=ordinal,
                    document_id=citation['document_id'], revision_id=citation['revision_id'],
                    chunk_id=citation['chunk_id'], citation=citation))
        attempt.answer += text
        now = datetime.now(timezone.utc)
        attempt.lease_expires_at = now + timedelta(seconds=60)
        if state:
            if state not in {'completed', 'stopped', 'error', 'interrupted'}:
                raise ValueError('invalid terminal state')
            attempt.state, attempt.finished_at, attempt.error_code = state, now, error_code
        self.db.commit()
        return True

    def stop(self, owner: str, conversation_id: str, turn_id: str, attempt_id: str) -> dict:
        """Stop only the identified attempt; repeated or late stops preserve the terminal result."""
        self.owned(owner, conversation_id, lock=True)
        self.recover(owner, conversation_id)
        attempt = self.db.scalar(select(ChatGenerationAttempt).where(
            ChatGenerationAttempt.id == attempt_id, ChatGenerationAttempt.turn_id == turn_id,
            ChatGenerationAttempt.conversation_id == conversation_id, ChatGenerationAttempt.owner_user_id == owner))
        if attempt is None:
            raise ConversationError(404, 'attempt_not_found')
        if attempt.state == 'generating':
            attempt.state, attempt.finished_at = 'stopped', datetime.now(timezone.utc)
        result = dict(attempt_id=attempt.id, status=attempt.state)
        self.db.commit()
        return result

