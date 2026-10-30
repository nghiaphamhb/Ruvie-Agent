"""F017 singleton schema rejects unsupported profiles and incomplete states."""
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ruvie import models


class EmbeddingSchemaTests(unittest.TestCase):
    def test_embedding_settings_enforce_singleton_and_profile(self):
        self.assertTrue(hasattr(models, 'OrganizationEmbeddingSettings'), 'embedding settings missing')
        engine = create_engine('sqlite://')
        self.addCleanup(engine.dispose)
        models.Base.metadata.create_all(engine)
        valid = dict(id=1, version=1, base_url='https://example.test/v1',
                     model_id='baai/bge-m3', dimension=1024, distance_metric='cosine')
        for changes in ({'id': 2}, {'version': -1}, {'model_id': 'other'},
                        {'dimension': 768}, {'distance_metric': 'l2'}, {'model_id': None},
                        {'dimension': None}, {'distance_metric': None}, {'base_url': None}):
            with self.subTest(changes=changes), Session(engine) as db:
                db.add(models.OrganizationEmbeddingSettings(**(valid | changes)))
                with self.assertRaises(IntegrityError):
                    db.commit()
        with Session(engine) as db:
            db.add(models.OrganizationEmbeddingSettings(id=1))
            db.commit()
            row = db.get(models.OrganizationEmbeddingSettings, 1)
            self.assertEqual((row.version, row.base_url, row.api_key_ciphertext), (0, None, None))
            db.delete(row)
            db.commit()
            db.add(models.OrganizationEmbeddingSettings(**valid))
            db.commit()

    def test_offline_migration_sql_does_not_rewrite_document_content(self):
        import os,subprocess,sys
        environment={**os.environ,'DATABASE_URL':'postgresql+psycopg://offline:offline@localhost/offline'}
        result=subprocess.run([sys.executable,'-B','-m','alembic','-c','backend/alembic.ini',
            'upgrade','0012_organization_llm_settings:head','--sql'],env=environment,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('CREATE TABLE organization_embedding_settings',result.stdout)
        self.assertIn('INSERT INTO organization_embedding_settings (id) VALUES (1)',result.stdout)
        self.assertNotIn('UPDATE document',result.stdout)
        self.assertNotIn('UPDATE organization_llm_settings',result.stdout)
