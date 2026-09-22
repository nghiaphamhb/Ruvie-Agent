import sys
from pathlib import Path
import unittest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "backend"))
from ruvie.document_retrieval import AuthorizedScope, PgvectorChunkRepository
from ruvie.domain import Base, Document, DocumentChunk, DocumentRevision, Membership, Project, RevisionIngestionState, Role, RoleCode, User

class VectorSearchTests(unittest.TestCase):
    def test_scope_excludes_ready_chunks_from_another_project(self) -> None:
        engine = create_engine("sqlite+pysqlite:///:memory:"); event.listen(engine, "connect", lambda c, _: c.execute("PRAGMA foreign_keys=ON")); Base.metadata.create_all(engine)
        with Session(engine) as s:
            s.add_all((User(id="u",email="u@x",display_name="U"),Role(id="r",code=RoleCode.BIM_CAD_SPECIALIST),Project(id="a",code="a",name="A"),Project(id="b",code="b",name="B"))); s.commit(); s.add(Membership(id="m",user_id="u",project_id="a",role_id="r")); s.add_all((Document(id="da",project_id="a",title="A",allowed_role_codes=["BIM_CAD_SPECIALIST"]),Document(id="db",project_id="b",title="B",allowed_role_codes=["BIM_CAD_SPECIALIST"]))); s.commit()
            for rid,did,pid in (("ra","da","a"),("rb","db","b")):
                s.add(DocumentRevision(id=rid,document_id=did,project_id=pid,revision_number=1,content_hash=rid*32,blob_uri="file:///x",mime_type="text/plain",size_bytes=1,software="x",software_version="1",ingestion_state=RevisionIngestionState.READY,embedding_model_id="m",embedding_model_version="a"*40,embedding_dimension=1024,embedding_distance_metric="cosine"))
            s.commit()
            for cid,rid,did,pid in (("ca","ra","da","a"),("cb","rb","db","b")):
                s.add(DocumentChunk(id=cid,document_revision_id=rid,document_id=did,project_id=pid,ordinal=0,text=cid,content_hash=cid*32,start_offset=0,end_offset=2,software="x",software_version="1",embedding=[0.0]*1024))
            s.commit(); self.assertEqual([c.id for c in PgvectorChunkRepository(s).search(AuthorizedScope.for_user("u"),[0.0]*1024)],["ca"])
        engine.dispose()
