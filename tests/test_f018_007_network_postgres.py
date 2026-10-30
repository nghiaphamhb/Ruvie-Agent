"""F018 offline PostgreSQL migration SQL check. Never touches app database."""
import os
import subprocess
import sys
import unittest

class MigrationSqlTests(unittest.TestCase):
    def test_alembic_sql(self):
        env={**os.environ,'DATABASE_URL':'postgresql+psycopg://offline:offline@localhost/offline'}
        run=subprocess.run([sys.executable,'-B','-m','alembic','-c','backend/alembic.ini',
            'upgrade','0013_org_embedding_settings:head','--sql'],
            capture_output=True,text=True,env=env)
        self.assertEqual(run.returncode,0,run.stderr)
        for value in ('network_mode','ck_org_llm_network','ck_org_embedding_network'):
            self.assertIn(value,run.stdout)
        self.assertNotIn('LLM_PROXY_URL',run.stdout)
