# F001-F003 acceptance gaps reviewed by F004-008

## Review scope

F004-008 initially reviewed seven unchecked acceptance criteria in F001-F003.
F005 subsequently closed the upload side-effect, ingestion runner/retry, and
audit immutability gaps. The remaining migration and successful-PDF-fixture
gaps are still open; offline SQL and a test database with a manually widened
Alembic bookkeeping column do not prove a zero-setup clean PostgreSQL upgrade.

## Findings

| Source AC | Evidence available now | Missing before the AC can be completed | Follow-up |
|---|---|---|---|
| F001: migrate a clean PostgreSQL database without manual steps | `test_f001_003_database.py` generates complete Alembic SQL; F005-007's E2E suite applies migrations on disposable PostgreSQL after precreating an Alembic version table with `VARCHAR(128)`. | No automated run proves the default Alembic bookkeeping table can be created and upgraded from a truly empty database without manual preparation. | **PG-01:** make the full migration chain work from an empty PostgreSQL database and verify `alembic current`. |
| F002: create all seven domain/ACL entities and constraints on clean PostgreSQL | Migration `0002_domain_acl` and F005-007's disposable PostgreSQL E2E exercise the domain schema; `test_f002_002_migration.py` checks generated PostgreSQL SQL. | The clean-database test still precreates a widened Alembic bookkeeping table, so zero-setup bootstrap remains unverified. | **PG-01:** remove the manual Alembic table preparation and verify schema constraints/indexes on a fresh PostgreSQL database. |
| F002: every allow/deny document retrieval creates an append-only audit event | `DocumentRetrievalAuditWriter.append`, retrieval allow/deny tests, migration `0007_audit_event_immutability`, and owner-confirmed PostgreSQL dev checks for update/delete/truncate rejection. | None known for normal application/database operations; a PostgreSQL superuser can still disable triggers. | Resolved by F005-006; see the migration and manual verification record in `specs/feat/F005-operational-mvp.md`. |
| F003: create revision/job/chunk/pgvector schema on clean PostgreSQL | Migration `0003_ingestion_rag_schema` and F005-007's disposable PostgreSQL E2E exercise the schema; ORM metadata and offline SQL tests cover the vector column and HNSW index. | E2E applies the chain only after manually widening the Alembic bookkeeping table; zero-setup empty-database migration remains unverified. | **PG-01:** verify full F003 schema and pgvector index through the unmodified fresh-database migration path. |
| F003: member upload creates a private blob/revision/job and non-member upload leaves no side effects | `test_f005_006_upload_audit.py` and `test_f005_005_document_upload_api.py` cover member upload, non-member denial without upload records/blob, and cleanup after database failure. | None known for the tested paths. | Resolved by F005-005/F005-006. |
| F003: ingestion produces deterministic chunks and retry does not duplicate data | `test_f005_004_ingestion.py` covers retry/backoff, stale recovery, idempotency, failure cleanup, and the production worker loop; `test_f005_007_e2e.py` covers text upload → worker → ready → chat on temporary PostgreSQL with fake HTTP providers. | No successful PDF ingestion fixture has been verified; only unreadable-PDF rejection is tested. | **PDF-01:** add a small valid PDF fixture and verify extraction through worker to ready/citation if PDF-success coverage remains an acceptance requirement. |
| F003: upload and retrieval allow/deny create safe audit events | Upload allow/deny and blob/database cleanup are covered by `test_f005_006_upload_audit.py`; retrieval allow/deny by F002/F004 tests; migration `0007_audit_event_immutability` and owner-confirmed dev database checks cover update/delete/truncate rejection. | None known for normal application/database operations. | Resolved by F005-006; PostgreSQL superusers can still disable triggers. |

## Shared PostgreSQL integration follow-up (PG-01)

The integration test should create a disposable empty database with pgvector,
run `alembic upgrade head`, and verify:

1. Alembic reaches the current head without manual SQL.
2. All F002 domain/ACL tables, foreign keys, unique constraints, enums, and
   query indexes exist.
3. All F003 revision/job/chunk tables and their cross-table constraints exist.
4. `document_chunks.embedding` is `vector(1024)` and its HNSW index uses
   `vector_cosine_ops`.
5. A downgrade/upgrade cycle for the latest migration is valid on PostgreSQL.

The test must use a disposable database. It must not run destructive migration
checks against a developer's configured database.

## Worker deployment boundary

`DocumentIngestionWorker` is currently a synchronous service object with unit
coverage. The FastAPI lifecycle does not start it, and there is no CLI,
scheduled process, container command, or queue consumer that calls
`run_next()` in production. Upload therefore creates a pending job, but a
deployed API process alone will not ingest it. INGEST-02 must be completed
before documentation can claim end-to-end production ingestion.
