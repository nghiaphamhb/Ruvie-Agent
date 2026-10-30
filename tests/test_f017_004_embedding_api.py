"""Actual cookie/Origin/CSRF boundaries for the organization LLM APIs."""
import unittest
from unittest.mock import patch
from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from ruvie import models
from ruvie.config import Settings, EmbeddingProfile
from ruvie.services.auth import AuthService

ORIGIN = 'https://ruvie.test'


class EmbeddingApiTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(hasattr(models, 'OrganizationEmbeddingSettings'))
        from ruvie.api.embedding import router
        engine = create_engine('sqlite://', connect_args={'check_same_thread':False}, poolclass=StaticPool)
        self.addCleanup(engine.dispose)
        models.Base.metadata.create_all(engine)
        self.factory = sessionmaker(engine)
        app = FastAPI()
        app.state.settings = Settings('sqlite://', EmbeddingProfile('test',1024,'cosine'),None,None,
                                     auth_allowed_origins=(ORIGIN,),
                                     llm_settings_encryption_key=Fernet.generate_key().decode())
        app.state.session_factory = self.factory
        app.include_router(router)
        with self.factory() as db:
            db.add_all([models.User(id='admin',email='admin@test',display_name='Admin',system_role='admin'),
                        models.User(id='user',email='user@test',display_name='User'),
                        models.OrganizationEmbeddingSettings(id=1)])
            db.commit()
            self.headers = {}
            for actor in ('admin','user'):
                session = AuthService(db).create_session(actor)
                self.headers[actor] = {'Origin':ORIGIN,'X-CSRF-Token':session.csrf_token,
                                       'Cookie':f'ruvie_session={session.token}'}
        self.client = TestClient(app,base_url=ORIGIN)
        self.addCleanup(self.client.close)
        self.body = dict(base_url='https://provider.test/v1',key_action='replace',api_key='private-key',
                         expected_version=0,model_id='baai/bge-m3')

    def test_admin_boundary_csrf_safe_validation_and_apply(self):
        from ruvie.adapters.embedding import OpenAICompatibleQueryEmbedder
        with patch.object(OpenAICompatibleQueryEmbedder, 'embed_query', return_value=[0.1]*1024):
            for method, path in [('get','/admin/embedding/connection'),
                                 ('post','/admin/embedding/connection/catalog'),
                                 ('post','/admin/embedding/connection/verify'),
                                 ('put','/admin/embedding/connection')]:
                kwargs = dict(headers=self.headers['user'])
                if method != 'get':
                    kwargs['json'] = self.body
                response = getattr(self.client,method)(path,**kwargs)
                self.assertEqual(response.status_code,403,response.text)
                self.assertEqual(response.headers['cache-control'],'no-store')
            for changes in ({'Origin':'https://evil.test'},{'X-CSRF-Token':'bad'}):
                response = self.client.put('/admin/embedding/connection',json=self.body,
                    headers=self.headers['admin'] | changes)
                self.assertEqual(response.status_code,403,response.text)
            invalid = self.client.put('/admin/embedding/connection',json=self.body | {'expected_version':True}, headers=self.headers['admin'])
            self.assertEqual(invalid.status_code,422,invalid.text)
            self.assertNotIn('private-key',invalid.text)
            response = self.client.put('/admin/embedding/connection',json=self.body,headers=self.headers['admin'])
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.json()['version'],1)
            self.assertNotIn('private-key',response.text)
            conflict = self.client.put('/admin/embedding/connection',json=self.body,headers=self.headers['admin'])
            self.assertEqual(conflict.status_code,409,conflict.text)

    def test_provider_authentication_and_timeout_have_safe_step_errors(self):
        import httpx
        request=httpx.Request('POST','https://provider.test/v1/embeddings')
        errors=[(httpx.HTTPStatusError('private upstream body',request=request,response=httpx.Response(401,request=request)),'embedding_authentication_failed'),
                (httpx.ReadTimeout('private endpoint',request=request),'embedding_timeout')]
        for error,expected in errors:
            with self.subTest(expected=expected), patch('ruvie.adapters.embedding.OpenAICompatibleQueryEmbedder.embed_query',side_effect=error):
                response=self.client.post('/admin/embedding/connection/verify',json=self.body,headers=self.headers['admin'])
                self.assertEqual(response.status_code,503,response.text)
                self.assertEqual(response.json()['detail']['code'],expected)
                self.assertNotIn('private',response.text)
