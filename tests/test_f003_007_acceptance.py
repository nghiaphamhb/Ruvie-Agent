import sys
from pathlib import Path
import unittest

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "backend"))
from ruvie.document_retrieval import AuthorizedScope, PgvectorChunkRepository
from ruvie.domain import AccessGrant, Base, Document, DocumentChunk, DocumentRevision, Membership, Project, RevisionIngestionState, Role, RoleCode, User


class F003AcceptanceTests(unittest.TestCase):
    def test_project_scope_and_direct_grant_limit_vector_chunks(self) -> None:
        engine = create_engine("sqlite+pysqlite:///:memory:")
        event.listen(engine, "connect", lambda c, _: c.execute("PRAGMA foreign_keys=ON")); Base.metadata.create_all(engine)
        with Session(engine) as s:
            s.add_all((User(id="u",email="u@example.com",display_name="U"),Role(id="r",code=RoleCode.BIM_CAD_SPECIALIST),Project(id="a",code="a",name="Alpha"),Project(id="b",code="b",name="Beta"))); s.commit()
            s.add(Membership(id="m",user_id="u",project_id="a",role_id="r")); s.add_all((Document(id="da",project_id="a",title="Alpha",allowed_role_codes=["BIM_CAD_SPECIALIST"]),Document(id="bg",project_id="b",title="Granted",allowed_role_codes=[]),Document(id="bp",project_id="b",title="Private",allowed_role_codes=[]))); s.commit()
            s.add(AccessGrant(id="g",resource_type="document",resource_id="bg",principal_type="user",principal_id="u",permission="read"))
            for rid,did,pid in (("ra","da","a"),("rg","bg","b"),("rp","bp","b")):
                s.add(DocumentRevision(id=rid,document_id=did,project_id=pid,revision_number=1,content_hash=rid*32,blob_uri="file:///x",mime_type="text/plain",size_bytes=1,software="x",software_version="1",ingestion_state=RevisionIngestionState.READY,embedding_model_id="m",embedding_model_version="a"*40,embedding_dimension=1024,embedding_distance_metric="cosine"))
            s.commit()
            for cid,rid,did,pid in (("ca","ra","da","a"),("cg","rg","bg","b"),("cp","rp","bp","b")):
                s.add(DocumentChunk(id=cid,document_revision_id=rid,document_id=did,project_id=pid,ordinal=0,text=cid,content_hash=cid*32,start_offset=0,end_offset=2,software="x",software_version="1",embedding=[0.0]*1024))
            s.commit()
            chunks = PgvectorChunkRepository(s).search(AuthorizedScope.for_user("u"), [0.0]*1024)
            self.assertEqual({chunk.id for chunk in chunks}, {"ca", "cg"})
        engine.dispose()


if __name__ == "__main__": unittest.main()
