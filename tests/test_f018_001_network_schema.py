"""Network draft schema and singleton DB constraints."""
import unittest
from sqlalchemy import create_engine, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ruvie.models import Base, OrganizationLlmSettings, OrganizationEmbeddingSettings
from ruvie.contracts.network import NetworkConfig
from ruvie.contracts.llm import OrganizationConnectionDraft

class NetworkSchemaTests(unittest.TestCase):
    def test_draft_requires_explicit_network(self):
        base = dict(base_url='https://provider.test/v1', key_action='clear', expected_version=0)
        with self.assertRaises(Exception):
            OrganizationConnectionDraft.model_validate(base)
        with self.assertRaises(Exception):
            OrganizationConnectionDraft.model_validate(base | {'network': {'mode':'direct','proxy_url':'socks5://localhost:1080'}})
        self.assertEqual(OrganizationConnectionDraft.model_validate(
            base | {'network': {'mode':'direct','proxy_url':None}}).network.mode, 'direct')

    def test_invalid_pairs_and_normalization(self):
        for value in ({'mode':'proxy','proxy_url':None},
                      {'mode':'direct','proxy_url':'socks5://localhost:80'},
                      {'mode':'automatic','proxy_url':None}):
            with self.assertRaises(Exception):
                NetworkConfig.model_validate(value)
        self.assertEqual(NetworkConfig(mode='proxy',proxy_url='SOCKS5://LOCALHOST:1080/').proxy_url,
                         'socks5://localhost:1080')

    def test_singletons_enforce_network_state(self):
        engine=create_engine('sqlite://')
        self.addCleanup(engine.dispose)
        Base.metadata.create_all(engine)
        for model in (OrganizationLlmSettings,OrganizationEmbeddingSettings):
            for pair in ({'network_mode':'direct','proxy_url':'socks5://localhost:80'},
                         {'network_mode':'proxy','proxy_url':None},
                         {'network_mode':'proxy','proxy_url':' '}):
                with self.subTest(model=model.__name__,pair=pair), Session(engine) as session:
                    session.add(model(id=1,**pair))
                    with self.assertRaises(IntegrityError):
                        session.commit()
            with Session(engine) as session:
                session.add(model(id=1))
                session.commit()
                session.execute(update(model).where(model.id == 1).values(network_mode=None))
                session.commit()
                session.expire_all()
                self.assertIsNone(session.get(model,1).network_mode)
