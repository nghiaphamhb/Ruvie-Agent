import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from ruvie.api.documents import router as documents_router
from ruvie.api.projects import router as projects_router
from ruvie.dependencies import get_session
from ruvie.models import (
    Base, Document, DocumentRevision, IngestionJob, IngestionJobState,
    Membership, Project, RevisionIngestionState, Role, RoleCode, User,
)
from ruvie.adapters.blob_storage import LocalBlobStore
from ruvie.services.auth import AuthService


class F005005ApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        event.listen(self.engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(self.engine)
        self.temp = TemporaryDirectory()
        app = FastAPI()
        app.include_router(documents_router)
        app.include_router(projects_router)
        app.state.session_factory = self.factory
        app.state.settings = type("Settings", (), {
            "auth_allowed_origins": ("http://localhost:5173",),
            "embedding_profile": type("Profile", (), {"model_id": "test-model", "dimension": 1024, "distance_metric": "cosine"})(),
        })()
        app.state.blob_store = LocalBlobStore(Path(self.temp.name))
        app.dependency_overrides[get_session] = self.session_dependency
        self.client = TestClient(app, raise_server_exceptions=False)
        with self.factory() as db:
            db.add_all((
                User(id="uploader", email="uploader@example.test", display_name="Uploader"),
                User(id="reader", email="reader@example.test", display_name="Reader"),
                User(id="outsider", email="outsider@example.test", display_name="Outsider"),
                Role(id="role-bim", code=RoleCode.BIM_CAD_SPECIALIST),
                Project(id="project-a", code="alpha", name="Alpha"),
                Project(id="project-b", code="beta", name="Beta"),
            ))
            db.commit()
            db.add_all((
                Membership(id="member-uploader", user_id="uploader", project_id="project-a", role_id="role-bim"),
                Membership(id="member-reader", user_id="reader", project_id="project-a", role_id="role-bim"),
            ))
            db.commit()
            self.tokens = {
                user: AuthService(db).create_session(user).token
                for user in ("uploader", "reader", "outsider")
            }

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()
        self.engine.dispose()

    def session_dependency(self):
        with self.factory() as db:
            yield db

    def headers(self, user="uploader", *, csrf=True, origin=True):
        headers = {"Cookie": f"ruvie_session={self.tokens[user]}"}
        if csrf:
            with self.factory() as db:
                headers["X-CSRF-Token"] = AuthService(db).resolve_session(self.tokens[user]).csrf_token
        if origin:
            headers["Origin"] = "http://localhost:5173"
        return headers

    def upload(self, **overrides):
        data = {"project_id": "project-a", "title": "Alpha manual", "software": "Revit", "software_version": "2026"}
        data.update(overrides.pop("data", {}))
        files = overrides.pop("files", {"file": ("manual.txt", b"Project Alpha guide", "text/plain")})
        return self.client.post("/documents/upload", headers=self.headers(**overrides), data=data, files=files)

    def test_project_list_contains_only_projects_the_user_belongs_to(self):
        response = self.client.get("/projects", headers=self.headers())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"items": [{"id": "project-a", "code": "alpha", "name": "Alpha"}]})

    def test_upload_is_multipart_and_server_sets_uploader_and_default_acl(self):
        response = self.upload(data={"allowed_role_codes": "[]"})

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["status"], "pending")
        with self.factory() as db:
            revision = db.get(DocumentRevision, response.json()["revision_id"])
            document = db.get(Document, response.json()["document_id"])
            self.assertEqual(revision.uploaded_by_user_id, "uploader")
            self.assertEqual(document.allowed_role_codes, [role.value for role in RoleCode])

    def test_server_detects_pdf_from_bytes_instead_of_client_mime_type(self):
        response = self.upload(files={"file": ("manual.txt", b"%PDF-1.7\nbody", "text/plain")})

        self.assertEqual(response.status_code, 202)
        with self.factory() as db:
            self.assertEqual(db.get(DocumentRevision, response.json()["revision_id"]).mime_type, "application/pdf")

    def test_upload_requires_csrf_and_allowed_origin(self):
        self.assertEqual(self.upload(csrf=False).status_code, 403)
        self.assertEqual(self.upload(origin=False).status_code, 403)

    def test_status_is_available_to_uploader_and_member_reader_but_hidden_from_others(self):
        uploaded = self.upload().json()
        reader = self.client.get(f"/documents/revisions/{uploaded['revision_id']}/status", headers=self.headers("reader"))
        outsider = self.client.get(f"/documents/revisions/{uploaded['revision_id']}/status", headers=self.headers("outsider"))
        missing = self.client.get("/documents/revisions/missing/status", headers=self.headers("outsider"))

        self.assertEqual((reader.status_code, reader.json()["status"]), (200, "pending"))
        self.assertEqual(outsider.status_code, 404)
        self.assertEqual(outsider.json(), missing.json())

    def test_running_status_comes_from_job_state(self):
        uploaded = self.upload().json()
        with self.factory() as db:
            job = db.get(IngestionJob, uploaded["job_id"])
            job.state = IngestionJobState.RUNNING
            db.commit()

        response = self.client.get(f"/documents/revisions/{uploaded['revision_id']}/status", headers=self.headers())

        self.assertEqual(response.json()["status"], "running")

    def test_invalid_file_bytes_are_rejected(self):
        response = self.upload(files={"file": ("bad.txt", b"\xff\x00", "text/plain")})

        self.assertEqual(response.status_code, 422)

    def test_upload_over_25_mib_is_rejected(self):
        response = self.upload(files={"file": ("large.txt", b"a" * (25 * 1024 * 1024 + 1), "text/plain")})

        self.assertEqual(response.status_code, 413)

    def test_nonmember_upload_is_not_found(self):
        response = self.upload(data={"project_id": "project-b"})

        self.assertEqual(response.status_code, 404)

    def test_ready_and_failed_statuses_come_from_revision(self):
        uploaded = self.upload().json()
        with self.factory() as db:
            revision = db.get(DocumentRevision, uploaded["revision_id"])
            revision.ingestion_state = RevisionIngestionState.READY
            db.commit()
        ready = self.client.get(f"/documents/revisions/{uploaded['revision_id']}/status", headers=self.headers())
        self.assertEqual(ready.json()["status"], "ready")

        with self.factory() as db:
            revision = db.get(DocumentRevision, uploaded["revision_id"])
            job = db.get(IngestionJob, uploaded["job_id"])
            revision.ingestion_state = RevisionIngestionState.FAILED
            job.state = IngestionJobState.FAILED
            job.error_code = "provider_unavailable"
            db.commit()
        failed = self.client.get(f"/documents/revisions/{uploaded['revision_id']}/status", headers=self.headers())
        self.assertEqual(failed.json(), {
            "revision_id": uploaded["revision_id"], "status": "failed", "error_code": "provider_unavailable"
        })


if __name__ == "__main__":
    unittest.main()
