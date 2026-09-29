# F001-F003 acceptance gaps reviewed by F004-008

## Review scope

F004-008 reviewed the seven acceptance criteria that remained unchecked in
F001-F003. Existing unit tests and offline Alembic SQL are useful evidence,
but they do not prove behavior against a clean PostgreSQL database with
pgvector. An acceptance criterion remains unchecked when any required behavior
or integration evidence is missing.

## Findings

| Source AC | Evidence available now | Missing before the AC can be completed | Follow-up |
|---|---|---|---|
| F001: migrate a clean PostgreSQL database without manual steps | `test_f001_003_database.py` creates the psycopg engine and generates the complete Alembic upgrade SQL. | No automated run applies `upgrade head` to a clean PostgreSQL instance and verifies the resulting Alembic revision. | **PG-01:** add an ephemeral PostgreSQL + pgvector integration test that applies the full migration chain to an empty database and checks `alembic current`. |
| F002: create all seven domain/ACL entities and constraints on clean PostgreSQL | Migration `0002_domain_acl` defines the seven tables, constraints, and ACL indexes; `test_f002_002_migration.py` checks generated PostgreSQL SQL. | The migration, foreign keys, unique constraints, enum, and indexes have not been exercised on real PostgreSQL. | **PG-01:** inspect the seven tables, constraints, enum, and ACL indexes after the clean-database migration. |
| F002: every allow/deny document retrieval creates an append-only audit event | `DocumentRetrievalAuditWriter.append`, `test_f002_005_audit_events.py`, and `test_f002_006_acceptance.py` cover allow/deny creation and safe deny fields. | Append-only behavior is an application convention; no test or database rule rejects update/delete of an existing event. | **AUDIT-01:** define the required immutability boundary, enforce it in PostgreSQL or its database role, and add update/delete rejection coverage. |
| F003: create revision/job/chunk/pgvector schema on clean PostgreSQL | Migration `0003_ingestion_rag_schema`, ORM metadata tests, and offline migration SQL cover the intended tables, relationships, vector column, and HNSW index. | No real PostgreSQL run proves pgvector extension creation, `vector(1024)`, HNSW index creation, or cross-table constraints. | **PG-01:** verify the F003 schema and pgvector index in the same clean-database integration test. |
| F003: member upload creates a private blob/revision/job and non-member upload leaves no side effects | `test_f003_002_document_upload.py` covers member upload, local path confinement, pending revision/job, and private S3 ACL. `DocumentUploadService._require_membership` denies non-members before blob creation. | There is no explicit non-member test asserting that no blob, document, revision, or job was created. | **UPLOAD-01:** add service/API tests for non-member denial and zero persistent/blob side effects, including cleanup after a database failure. |
| F003: ingestion produces deterministic chunks and retry does not duplicate data | `test_f003_003_ingestion_worker.py` covers the text happy path, deterministic offsets, ready/completed states, and no second pending job. | Only unit invocation exists. Failed jobs are marked `failed` and are not reclaimed; retry semantics, duplicate prevention after partial failure, PDF fixture coverage, and a production runner are absent. | **INGEST-01:** define retry transitions/idempotency and test interrupted attempts. **INGEST-02:** add a production runner that repeatedly invokes `DocumentIngestionWorker.run_next()` with shutdown and polling behavior. |
| F003: upload and retrieval allow/deny create safe audit events | `AuthorizedRetrievalService` and F004 retrieval/chat tests cover safe allow/deny retrieval audit events. | Upload does not write an audit event. Upload allow/deny and blob/database failure paths have no audit coverage. | **AUDIT-02:** add an upload audit writer/service integration and tests for member allow, non-member deny, validation failure, and safe failure fields. |

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
