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


class OrganizationApiTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(hasattr(models, 'OrganizationLlmSettings'))
        from ruvie.api.llm import router
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
                        models.OrganizationLlmSettings(id=1)])
            db.commit()
            self.headers = {}
            for actor in ('admin','user'):
                session = AuthService(db).create_session(actor)
                self.headers[actor] = {'Origin':ORIGIN,'X-CSRF-Token':session.csrf_token,
                                       'Cookie':f'ruvie_session={session.token}'}
        self.client = TestClient(app,base_url=ORIGIN)
        self.addCleanup(self.client.close)
        self.body = dict(base_url='https://provider.test/v1',key_action='replace',api_key='private-key',
                         expected_version=0,allowed_model_ids=['a'],default_model_id='a')

    def test_employee_cannot_access_admin_or_old_mutations(self):
        with patch('ruvie.adapters.llm.OpenAICompatibleLlmAdapter.list_models') as probe:
            for method,path,body in (('get','/admin/llm/connection',None),
                                     ('put','/admin/llm/connection',self.body),
                                     ('post','/admin/llm/connection/verify',self.body),
                                     ('put','/llm/connection',self.body),('delete','/llm/connection',None)):
                kwargs = {'headers':self.headers['user']}
                if body is not None:
                    kwargs['json'] = body
                result = getattr(self.client,method)(path,**kwargs)
                self.assertEqual(result.status_code,403,result.text)
                self.assertEqual(result.headers['cache-control'],'no-store')
            probe.assert_not_called()

    def test_admin_apply_read_filter_and_legacy_gone(self):
        with patch('ruvie.adapters.llm.OpenAICompatibleLlmAdapter.list_models',
                   return_value=[{'id':'a','name':'A'},{'id':'b','name':'B'}]):
            result = self.client.put('/admin/llm/connection',json=self.body,headers=self.headers['admin'])
            self.assertEqual(result.status_code,200,result.text)
            self.assertNotIn('private-key',result.text)
            self.assertEqual(result.json()['version'],1)
            public = self.client.get('/llm/connection',headers=self.headers['user'])
            self.assertEqual(set(public.json()),{'configured','selected_model_id','configuration_version'})
            catalog = self.client.get('/models',headers=self.headers['user'])
            self.assertEqual([m['id'] for m in catalog.json()['models']],['a'])
        for method in ('put','delete'):
            self.assertEqual(getattr(self.client,method)('/llm/connection',headers=self.headers['admin']).status_code,410)

    def test_validation_origin_csrf_and_conflict_are_safe(self):
        with patch('ruvie.adapters.llm.OpenAICompatibleLlmAdapter.list_models',return_value=[{'id':'a','name':'A'}]):
            for headers in ({**self.headers['admin'],'Origin':'https://evil.test'},
                            {**self.headers['admin'],'X-CSRF-Token':'bad'}):
                self.assertEqual(self.client.put('/admin/llm/connection',json=self.body,headers=headers).status_code,403)
            invalid = self.client.put('/admin/llm/connection',json={**self.body,'expected_version':True},headers=self.headers['admin'])
            self.assertEqual(invalid.status_code,422)
            self.assertNotIn('private-key',invalid.text)
            self.assertEqual(self.client.put('/admin/llm/connection',json=self.body,headers=self.headers['admin']).status_code,200)
            self.assertEqual(self.client.put('/admin/llm/connection',json=self.body,headers=self.headers['admin']).status_code,409)
