"""F019 relational history constraints and migration SQL."""
import os
import subprocess
import sys
import unittest
from datetime import datetime, timezone, timedelta

from sqlalchemy import create_engine, event, select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ruvie.models import Base, User
from ruvie.models.chat import ChatConversation, ChatTurn, ChatGenerationAttempt, ChatAttemptSource


class _HistoryFixture(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        event.listen(self.engine, 'connect', lambda db, _: db.execute('PRAGMA foreign_keys=ON'))
        Base.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)
        self.db = Session(self.engine)
        self.addCleanup(self.db.close)
        self.db.add(User(id='owner', email='owner@test', display_name='Owner'))
        self.db.flush()
        self.db.add(ChatConversation(id='chat', owner_user_id='owner', title='Question', updated_at=datetime.now(timezone.utc)))
        self.db.flush()
        self.db.add(ChatTurn(id='turn', conversation_id='chat', ordinal=1, question='Question'))
        self.db.commit()

    def attempt(self, id='attempt', **overrides):
        values = dict(id=id, turn_id='turn', conversation_id='chat', owner_user_id='owner',
                      request_id=id, request_fingerprint='a' * 64, model_id='model',
                      state='generating', lease_expires_at=datetime.now(timezone.utc) + timedelta(seconds=60))
        return ChatGenerationAttempt(**(values | overrides))

class HistorySchemaTests(_HistoryFixture):
    def test_one_active_generation_per_conversation_and_owner_request_uniqueness(self):
        self.db.add(self.attempt())
        self.db.commit()
        self.db.add(self.attempt('second', ordinal=2))
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()
        first = self.db.get(ChatGenerationAttempt, 'attempt')
        first.state = 'completed'
        first.finished_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.add(self.attempt('second', request_id='attempt', ordinal=2))
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()
        self.db.add(self.attempt('second', ordinal=2))
        self.db.commit()

    def test_turn_order_and_terminal_state_constraints(self):
        self.db.add(ChatTurn(id='duplicate', conversation_id='chat', ordinal=1, question='Duplicate'))
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()
        self.db.add(self.attempt(state='completed'))
        with self.assertRaises(IntegrityError):
            self.db.commit()

    def test_owner_and_turn_cannot_be_forged(self):
        self.db.add(User(id='other', email='other@test', display_name='Other'))
        self.db.commit()
        self.db.add(self.attempt(owner_user_id='other'))
        with self.assertRaises(IntegrityError):
            self.db.commit()

    def test_delete_cascades_history_but_keeps_account(self):
        self.db.add(self.attempt())
        self.db.flush()
        # Provenance survives missing/deleted source objects, so reads can fail closed.
        self.db.add(ChatAttemptSource(attempt_id='attempt', ordinal=1,
                    document_id='missing', revision_id='missing', chunk_id='missing', citation={}))
        self.db.commit()
        self.db.delete(self.db.get(ChatConversation, 'chat'))
        self.db.commit()
        for model in (ChatTurn, ChatGenerationAttempt, ChatAttemptSource):
            self.assertEqual(self.db.scalar(select(func.count()).select_from(model)), 0)
        self.assertIsNotNone(self.db.get(User, 'owner'))

    def test_migration_upgrade_and_downgrade_sql(self):
        environment = {**os.environ, 'DATABASE_URL': 'postgresql+psycopg://offline:offline@localhost/offline'}
        for direction, target in [('upgrade', '0015_ai_network_constraints:head'),
                                  ('downgrade', 'head:0015_ai_network_constraints')]:
            run = subprocess.run([sys.executable, '-B', '-m', 'alembic', '-c',
                    'backend/alembic.ini', direction, target, '--sql'],
                    capture_output=True, text=True, env=environment)
            self.assertEqual(run.returncode, 0, run.stderr)
            for table in ('chat_conversations', 'chat_turns', 'chat_generation_attempts', 'chat_attempt_sources'):
                self.assertIn(('CREATE TABLE ' if direction == 'upgrade' else 'DROP TABLE ') + table, run.stdout)


class _PostgresHistoryFixture(_HistoryFixture):
    """Run the same constraints against an Alembic-created disposable PostgreSQL DB."""
    @classmethod
    def setUpClass(cls):
        import test_f005_007_e2e as fixtures
        fixtures.F005007EndToEndTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        import test_f005_007_e2e as fixtures
        fixtures.F005007EndToEndTests.tearDownClass()

    def setUp(self):
        import psycopg
        from uuid import uuid4
        from unittest.mock import patch
        from alembic import command
        from alembic.config import Config
        from sqlalchemy import text
        import test_f005_007_e2e as fixtures
        database = 'f019_' + uuid4().hex[:12]
        admin = psycopg.connect(host='127.0.0.1',
            port=fixtures.F005007EndToEndTests.postgres_port,
            dbname=fixtures.POSTGRES_USER, user=fixtures.POSTGRES_USER,
            password=fixtures.POSTGRES_PASSWORD, autocommit=True)
        admin.execute(f'CREATE DATABASE "{database}"')
        self.addCleanup(admin.close)
        self.addCleanup(lambda: admin.execute(f'DROP DATABASE "{database}" WITH (FORCE)'))
        self.url = (f'postgresql+psycopg://{fixtures.POSTGRES_USER}:{fixtures.POSTGRES_PASSWORD}'
                    f'@127.0.0.1:{fixtures.F005007EndToEndTests.postgres_port}/{database}')
        self.engine = create_engine(self.url)
        self.addCleanup(self.engine.dispose)
        with self.engine.begin() as db:
            db.execute(text('CREATE TABLE alembic_version (version_num VARCHAR(128) PRIMARY KEY)'))
        with patch.dict(os.environ, {'DATABASE_URL': self.url}):
            command.upgrade(Config('backend/alembic.ini'), 'head')
        self.db = Session(self.engine)
        self.addCleanup(self.db.close)
        self.db.add(User(id='owner', email='owner@test', display_name='Owner'))
        self.db.flush()
        self.db.add(ChatConversation(id='chat', owner_user_id='owner', title='Question', updated_at=datetime.now(timezone.utc)))
        self.db.flush()
        self.db.add(ChatTurn(id='turn', conversation_id='chat', ordinal=1, question='Question'))
        self.db.commit()

class HistoryPostgresTests(HistorySchemaTests, _PostgresHistoryFixture):
    def test_rollback_keeps_existing_accounts(self):
        from unittest.mock import patch
        from alembic import command
        from alembic.config import Config
        from sqlalchemy import inspect
        self.db.close()
        with patch.dict(os.environ, {'DATABASE_URL': self.url}):
            command.downgrade(Config('backend/alembic.ini'), '0015_ai_network_constraints')
        self.assertNotIn('chat_conversations', inspect(self.engine).get_table_names())
        with Session(self.engine) as db:
            self.assertIsNotNone(db.get(User, 'owner'))

class HistoryServiceTests(_HistoryFixture):
    def service(self):
        from ruvie.services.conversations import ConversationService
        return ConversationService(self.db)

    def test_list_detail_ownership_and_rename_version(self):
        from ruvie.services.conversations import ConversationError
        service = self.service()
        self.assertEqual(service.list('owner')['items'][0]['id'], 'chat')
        self.assertEqual(service.list('other')['items'], [])
        self.assertEqual(service.detail('owner', 'chat')['turns'][0]['question'], 'Question')
        with self.assertRaises(ConversationError) as denied:
            service.detail('other', 'chat')
        self.assertEqual(denied.exception.status, 404)
        result = service.rename('owner', 'chat', '  Renamed  ', 1)
        self.assertEqual((result['title'], result['version']), ('Renamed', 2))
        with self.assertRaises(ConversationError) as conflict:
            service.rename('owner', 'chat', 'Overwrite', 1)
        self.assertEqual(conflict.exception.status, 409)

    def test_sources_fail_closed_for_partial_and_completed_answers(self):
        service = self.service()
        self.db.add(self.attempt(answer='private answer'))
        self.db.flush()
        self.db.add(ChatAttemptSource(attempt_id='attempt', ordinal=1,
                    document_id='missing', revision_id='missing', chunk_id='missing',
                    citation={'title': 'private title'}))
        self.db.commit()
        turn = service.detail('owner', 'chat')['turns'][0]
        self.assertTrue(turn['content_unavailable'])
        self.assertEqual((turn['answer'], turn['citations']), ('', []))

    def test_expired_lease_is_recovered_and_active_delete_is_rejected(self):
        from ruvie.services.conversations import ConversationError
        service = self.service()
        self.db.add(self.attempt())
        self.db.commit()
        with self.assertRaises(ConversationError) as active:
            service.delete('owner', 'chat')
        self.assertEqual(active.exception.status, 409)
        attempt = self.db.get(ChatGenerationAttempt, 'attempt')
        attempt.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        self.db.commit()
        self.assertEqual(service.detail('owner', 'chat')['turns'][0]['status'], 'interrupted')
        service.delete('owner', 'chat')
        self.assertIsNone(self.db.get(ChatConversation, 'chat'))

    def test_list_and_turn_pagination(self):
        service = self.service()
        self.db.add(ChatConversation(id='chat2', owner_user_id='owner', title='Second', updated_at=datetime.now(timezone.utc)))
        self.db.add(ChatTurn(id='turn2', conversation_id='chat', ordinal=2, question='Second'))
        self.db.commit()
        page = service.list('owner', limit=1)
        self.assertIsNotNone(page['next_cursor'])
        following = service.list('owner', limit=1, cursor=page['next_cursor'])
        self.assertNotEqual(page['items'][0]['id'], following['items'][0]['id'])
        newest = service.detail('owner', 'chat', limit=1)
        self.assertEqual(newest['turns'][0]['id'], 'turn2')
        older = service.detail('owner', 'chat', limit=1, before=newest['next_cursor'])
        self.assertEqual(older['turns'][0]['id'], 'turn')


class GenerationLifecycleTests(_HistoryFixture):
    def service(self):
        from ruvie.services.conversations import ConversationService
        return ConversationService(self.db)

    def test_accept_is_idempotent_and_fenced(self):
        from ruvie.services.conversations import ConversationError
        service = self.service()
        accepted = service.accept('owner', 'request', 'Question two', 'model', 'chat')
        with self.assertRaises(ConversationError) as duplicate:
            service.accept('owner', 'request', 'Question two', 'model', 'chat')
        self.assertEqual(duplicate.exception.code, 'request_already_recorded')
        self.assertEqual(duplicate.exception.resources['attempt_id'], accepted['attempt_id'])
        with self.assertRaises(ConversationError) as changed:
            service.accept('owner', 'request', 'Changed', 'model', 'chat')
        self.assertEqual(changed.exception.code, 'request_conflict')
        self.assertTrue(service.persist('owner', accepted['attempt_id'], text='saved'))
        stopped = service.stop('owner', 'chat', accepted['turn_id'], accepted['attempt_id'])
        self.assertEqual(stopped['status'], 'stopped')
        self.assertFalse(service.persist('owner', accepted['attempt_id'], text='late', state='completed'))
        retried = service.accept('owner', 'retry', None, 'model', 'chat', accepted['turn_id'])
        self.assertEqual(retried['turn_id'], accepted['turn_id'])
        self.assertNotEqual(retried['attempt_id'], accepted['attempt_id'])
        self.assertEqual(self.db.scalar(select(func.count()).select_from(ChatTurn)), 2)

    def test_new_chat_title_and_provenance_commit_before_content(self):
        service = self.service()
        accepted = service.accept('owner', 'new', '  First   question  ', 'model')
        self.assertEqual(self.db.get(ChatConversation, accepted['conversation_id']).title, 'First question')
        from ruvie.services.documents.citation import CitationBuilder
        citation = CitationBuilder.build('missing', 'revision', 'chunk', 1, 0, 10, 'Title', 'hash', 'CAD', '1')
        self.assertTrue(service.persist('owner', accepted['attempt_id'], citations=[citation.to_dict()]))
        self.assertTrue(service.persist('owner', accepted['attempt_id'], text='secret', state='completed'))
        turn = service.detail('owner', accepted['conversation_id'])['turns'][0]
        self.assertTrue(turn['content_unavailable'])
        self.assertEqual(turn['answer'], '')
        self.assertEqual(service.stop('owner', accepted['conversation_id'], accepted['turn_id'], accepted['attempt_id'])['status'], 'completed')

class DurableStreamTests(_HistoryFixture):
    def test_accepted_and_completed_are_durable_and_prompt_stays_single_turn(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from sqlalchemy.orm import sessionmaker
        from ruvie.services.chat import ChatService
        captured = []
        class Adapter:
            provider = SimpleNamespace(model='model')
            def stream(self, messages):
                captured.extend(messages)
                yield 'Answer'
        service = ChatService(None, None, sessionmaker(self.engine))
        with patch.object(service, 'resolve_model', return_value=Adapter()), patch.object(service, 'retrieve', return_value=[]):
            events = service.start('owner', 'New question', 'request', 'model', 'chat')
            accepted = next(events)
            self.assertEqual(accepted.event, 'accepted')
            with Session(self.engine) as db:
                self.assertIsNotNone(db.get(ChatGenerationAttempt, accepted.data['attempt_id']))
            remaining = list(events)
        self.assertEqual(remaining[-1].event, 'completed')
        with Session(self.engine) as db:
            attempt = db.get(ChatGenerationAttempt, accepted.data['attempt_id'])
            self.assertEqual((attempt.state, attempt.answer), ('completed', 'Answer'))
        self.assertEqual(len(captured), 2)
        self.assertIn('New question', captured[1]['content'])
        self.assertNotIn('Question\n', captured[1]['content'])

class HistoryHttpTests(unittest.TestCase):
    def test_owner_list_no_store_and_write_security(self):
        from types import SimpleNamespace
        from unittest.mock import patch, MagicMock
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from ruvie.api.conversations import router
        from ruvie.dependencies import get_authenticated_user_id, get_session
        app = FastAPI()
        app.state.settings = SimpleNamespace(auth_allowed_origins=('https://test',))
        app.state.session_factory = MagicMock()
        app.include_router(router)
        app.dependency_overrides[get_authenticated_user_id] = lambda: 'owner'
        app.dependency_overrides[get_session] = lambda: None
        with TestClient(app) as client, patch('ruvie.api.conversations.ConversationService') as service:
            service.return_value.list.return_value = {'items': [], 'next_cursor': None}
            response = client.get('/conversations')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers['cache-control'], 'no-store')
            service.return_value.list.assert_called_once_with('owner', limit=30, cursor=None)
            self.assertEqual(client.delete('/conversations/00000000-0000-0000-0000-000000000001').status_code, 403)
            with patch('ruvie.api.conversations.verify_csrf') as csrf:
                response = client.patch('/conversations/00000000-0000-0000-0000-000000000001',
                    headers={'Origin': 'https://test'}, json={'title': 'Name', 'expected_version': 1})
                csrf.assert_called_once()

class SourceAuthorizationTests(_HistoryFixture):
    def test_revoked_grant_redacts_whole_attempt_without_hiding_independent_turn(self):
        from ruvie.models import Project, Document, DocumentRevision, DocumentChunk, AccessGrant
        from ruvie.services.conversations import ConversationService
        self.db.add(Project(id='project', code='history', name='History'))
        self.db.flush()
        self.db.add(Document(id='document', project_id='project', title='Private title', allowed_role_codes=[]))
        self.db.flush()
        self.db.add(DocumentRevision(id='revision', document_id='document', project_id='project',
            revision_number=1, content_hash='a'*64, blob_uri='private://must-not-leak', mime_type='text/plain',
            size_bytes=10, software='CAD', software_version='1', embedding_model_id='baai/bge-m3',
            embedding_dimension=1024, embedding_distance_metric='cosine'))
        self.db.flush()
        self.db.add(DocumentChunk(id='chunk', document_revision_id='revision', document_id='document',
            project_id='project', ordinal=0, text='private source', content_hash='a'*64,
            start_offset=0, end_offset=10, software='CAD', software_version='1', embedding=[0.0]*1024))
        grant=AccessGrant(id='grant', resource_id='document', principal_id='owner')
        self.db.add(grant)
        self.db.add(self.attempt(answer='private answer'))
        self.db.flush()
        self.db.add(ChatAttemptSource(attempt_id='attempt', ordinal=1, document_id='document',
            revision_id='revision', chunk_id='chunk', citation={'title':'Private title'}))
        self.db.add(ChatTurn(id='independent', conversation_id='chat', ordinal=2, question='Independent'))
        self.db.commit()
        service=ConversationService(self.db)
        visible=service.detail('owner','chat')['turns'][0]
        self.assertEqual(visible['answer'],'private answer')
        self.assertFalse(visible['content_unavailable'])
        self.db.delete(grant)
        self.db.commit()
        hidden=service.detail('owner','chat')['turns']
        self.assertEqual(hidden[0]['answer'],'')
        self.assertEqual(hidden[0]['citations'],[])
        self.assertTrue(hidden[0]['content_unavailable'])
        self.assertEqual(hidden[1]['question'],'Independent')
        self.assertNotIn('private://',str(hidden))
        # Membership revocation uses the same database predicate as direct grants.
        from ruvie.models import Role, RoleCode, Membership
        role=self.db.scalar(select(Role).where(Role.code == RoleCode.IT_SUPPORT))
        if role is None:
            role=Role(id='history-role',code=RoleCode.IT_SUPPORT)
            self.db.add(role)
            self.db.flush()
        document=self.db.get(Document,'document')
        document.allowed_role_codes=[RoleCode.IT_SUPPORT.value]
        member=Membership(id='history-membership',user_id='owner',project_id='project',role_id=role.id)
        self.db.add(member)
        self.db.commit()
        self.assertEqual(service.detail('owner','chat')['turns'][0]['answer'],'private answer')
        self.db.delete(member)
        self.db.commit()
        self.assertTrue(service.detail('owner','chat')['turns'][0]['content_unavailable'])
        self.db.delete(document)
        self.db.commit()
        self.assertIsNotNone(self.db.get(ChatAttemptSource,('attempt',1)))
        self.assertTrue(service.detail('owner','chat')['turns'][0]['content_unavailable'])



class SourceAuthorizationPostgresTests(SourceAuthorizationTests, _PostgresHistoryFixture):
    pass


class HistoryServicePostgresTests(HistoryServiceTests, _PostgresHistoryFixture):
    pass


class GenerationPostgresTests(GenerationLifecycleTests, _PostgresHistoryFixture):
    pass

class ConcurrentGenerationPostgresTests(_PostgresHistoryFixture):
    def test_two_transactions_admit_only_one_generation(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from ruvie.services.conversations import ConversationService, ConversationError
        barrier=Barrier(2)
        def accept(request):
            with Session(self.engine) as db:
                barrier.wait(timeout=10)
                try:
                    return ConversationService(db).accept('owner', request, 'Concurrent', 'model', 'chat')
                except ConversationError as error:
                    return error.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes=list(pool.map(accept, ['one','two']))
        self.assertEqual(sum(isinstance(result,dict) for result in outcomes),1)
        self.assertIn('generation_active',outcomes)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(ChatGenerationAttempt)),1)

    def test_duplicate_new_chat_requests_create_one_graph(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from ruvie.services.conversations import ConversationService, ConversationError
        barrier=Barrier(2)
        def accept(_):
            with Session(self.engine) as db:
                barrier.wait(timeout=10)
                try:
                    return ConversationService(db).accept('owner', 'same', 'Concurrent new chat', 'model')
                except ConversationError as error:
                    return error.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes=list(pool.map(accept, range(2)))
        self.assertEqual(sum(isinstance(result,dict) for result in outcomes),1)
        self.assertIn('request_already_recorded',outcomes)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(ChatConversation)),2)


    def test_stop_racing_completed_keeps_the_first_terminal_result(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from ruvie.services.conversations import ConversationService
        ids=ConversationService(self.db).accept('owner','race','Question','model','chat')
        barrier=Barrier(2)
        def operation(stop):
            with Session(self.engine) as db:
                barrier.wait(timeout=10)
                service=ConversationService(db)
                if stop:
                    return service.stop('owner','chat',ids['turn_id'],ids['attempt_id'])
                return service.persist('owner',ids['attempt_id'],text='final',state='completed')
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(operation,[False,True]))
        self.db.expire_all()
        attempt=self.db.get(ChatGenerationAttempt,ids['attempt_id'])
        self.assertIn(attempt.state,('completed','stopped'))
        self.assertEqual(attempt.answer,'final' if attempt.state == 'completed' else '')
        self.assertFalse(ConversationService(self.db).persist('owner',attempt.id,text='late',state='error'))


class DurableFailureTests(_HistoryFixture):
    def configured(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from sqlalchemy.orm import sessionmaker
        from ruvie.services.chat import ChatService
        class Adapter:
            provider=SimpleNamespace(model='model')
            def stream(self, messages):
                yield 'partial'
        service=ChatService(None,None,sessionmaker(self.engine))
        model=patch.object(service,'resolve_model',return_value=Adapter())
        retrieval=patch.object(service,'retrieve',return_value=[])
        model.start();retrieval.start()
        self.addCleanup(model.stop);self.addCleanup(retrieval.stop)
        return service

    def test_disconnect_marks_interrupted_and_replay_never_resolves_provider(self):
        from unittest.mock import patch
        from ruvie.services.conversations import ConversationError
        service=self.configured()
        events=service.start('owner','Current','same','model','chat')
        accepted=next(events)
        events.close()
        self.db.expire_all()
        self.assertEqual(self.db.get(ChatGenerationAttempt,accepted.data['attempt_id']).state,'interrupted')
        with patch.object(service,'resolve_model',side_effect=AssertionError('provider called twice')):
            with self.assertRaises(ConversationError) as duplicate:
                service.start('owner','Current','same','model','chat')
        self.assertEqual(duplicate.exception.code,'request_already_recorded')

    def test_database_fault_never_emits_completed(self):
        from unittest.mock import patch
        from sqlalchemy.exc import SQLAlchemyError
        service=self.configured()
        events=service.start('owner','Current','request','model','chat')
        next(events)
        with patch('sqlalchemy.orm.Session.commit',side_effect=SQLAlchemyError('private database error')):
            remaining=list(events)
        self.assertNotIn('completed',[event.event for event in remaining])
        self.assertEqual(remaining[-1].data['code'],'history_unavailable')
        self.assertNotIn('private database error',str(remaining))

    def test_close_after_committed_delta_does_not_append_it_twice(self):
        service=self.configured()
        events=service.start('owner','Current','disconnect','model','chat')
        accepted=next(events)
        delta=next(events)
        self.assertEqual(delta.event,'delta')
        events.close()
        self.db.expire_all()
        attempt=self.db.get(ChatGenerationAttempt,accepted.data['attempt_id'])
        self.assertEqual(attempt.answer,'partial')
        self.assertEqual(attempt.state,'interrupted')


    def test_expired_lease_discards_late_output(self):
        from unittest.mock import patch
        from ruvie.contracts.chat import ChatStreamEvent
        service=self.configured()
        ids={}
        def late_stream(*_):
            with Session(self.engine) as db:
                attempt=db.get(ChatGenerationAttempt,ids['attempt_id'])
                attempt.lease_expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)
                db.commit()
            yield ChatStreamEvent('delta',{'text':'late'})
            yield ChatStreamEvent('completed',{})
        with patch.object(service,'stream',late_stream):
            events=service.start('owner','Question','lease','model','chat')
            ids.update(next(events).data)
            self.assertEqual(list(events),[])
        self.db.expire_all()
        attempt=self.db.get(ChatGenerationAttempt,ids['attempt_id'])
        self.assertEqual((attempt.state,attempt.answer),('interrupted',''))


class HistoryHttpPostgresTests(_PostgresHistoryFixture):
    def client(self):
        import hashlib
        from types import SimpleNamespace
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from sqlalchemy.orm import sessionmaker
        from ruvie.models import AuthSession
        from ruvie.api.conversations import router
        from ruvie.api.chat import router as chat_router
        from ruvie.services.conversations import ConversationService
        self.db.add(User(id='admin',email='admin@test',display_name='Admin',system_role='admin'))
        self.db.flush()
        for owner in ('owner','admin'):
            self.db.add(AuthSession(id=owner,user_id=owner,token_hash=hashlib.sha256(owner.encode()).hexdigest(),
                csrf_token='csrf-'+owner,expires_at=datetime.now(timezone.utc)+timedelta(hours=1)))
        self.db.commit()
        accepted=ConversationService(self.db).accept('owner','http','Http question','model')
        app=FastAPI()
        app.include_router(router);app.include_router(chat_router)
        app.state.settings=SimpleNamespace(auth_allowed_origins=('https://history.test',))
        app.state.session_factory=sessionmaker(self.engine)
        app.state.query_embedder=None
        client=TestClient(app)
        self.addCleanup(client.close)
        return client,accepted

    def test_other_admin_cannot_read_write_retry_or_stop_owned_chat(self):
        from uuid import uuid4
        client,ids=self.client()
        client.cookies.set('ruvie_session','admin')
        headers={'Origin':'https://history.test','X-CSRF-Token':'csrf-admin'}
        path='/conversations/'+ids['conversation_id']
        calls=[('GET',path,None),('PATCH',path,{'title':'Stolen','expected_version':1}),('DELETE',path,None),
            ('POST','/chat',{'message':'Attack','conversation_id':ids['conversation_id'],'request_id':str(uuid4())}),
            ('POST',path+'/turns/'+ids['turn_id']+'/retry',{'request_id':str(uuid4())}),
            ('POST',path+'/turns/'+ids['turn_id']+'/stop',{'attempt_id':ids['attempt_id']})]
        for method,url,body in calls:
            with self.subTest(method=method,url=url):
                response=client.request(method,url,json=body,headers=headers)
                self.assertEqual(response.status_code,404,response.text)
                self.assertEqual(response.headers['cache-control'],'no-store')
                self.assertNotIn('Http question',response.text)
        self.assertEqual(client.get('/conversations').json()['items'],[])

    def test_real_session_origin_csrf_validation_and_safe_errors(self):
        from uuid import uuid4
        client,ids=self.client()
        client.cookies.set('ruvie_session','owner')
        path='/conversations/'+ids['conversation_id']
        body={'title':'Renamed','expected_version':1}
        self.assertEqual(client.patch(path,json=body).status_code,403)
        self.assertEqual(client.patch(path,json=body,headers={'Origin':'https://history.test'}).status_code,403)
        self.assertEqual(client.patch(path,json=body,headers={'Origin':'https://attacker.test','X-CSRF-Token':'csrf-owner'}).status_code,403)
        good=client.patch(path,json=body,headers={'Origin':'https://history.test','X-CSRF-Token':'csrf-owner'})
        self.assertEqual(good.status_code,200,good.text)
        self.assertEqual(good.json()['title'],'Renamed')
        invalid=client.post('/chat',json={'message':'private-input-marker'},headers={'Origin':'https://history.test'})
        self.assertEqual(invalid.status_code,422)
        self.assertNotIn('private-input-marker',invalid.text)
        client.cookies.clear()
        self.assertEqual(client.get(path).status_code,401)
        self.assertEqual(client.post('/chat',json={'message':'Q','request_id':str(uuid4())}).status_code,401)
