# F003 - Ingestion + Authorized RAG

## Goal
Cho phép đưa tài liệu thuộc một project vào hệ thống, trích xuất và lập chỉ
mục nội dung của tài liệu đó, rồi retrieval chỉ trả các chunks mà caller đã
được cấp quyền đọc. Mỗi kết quả phải có citation ổn định, truy về đúng phiên
bản tài liệu và vị trí nguồn.

## User Story
As a project member, I want to upload and search the technical documents that
I am allowed to use, so that RAG answers contain useful, traceable citations
without exposing documents from another project.

## Scope
### In
- Dùng PostgreSQL làm database chính và extension `pgvector` để lưu/search
  embedding; metadata domain, ACL predicate, chunks và vectors ở cùng một
  database.
- Lưu file gốc qua `BlobStore` abstraction: local filesystem trong development
  và S3-compatible object storage trong production. Object không được public;
  app chỉ đọc object sau khi authorization thành công.
- Upload yêu cầu caller đã xác thực và là member của project đích. Upload
  nhận `project_id`, title, file và metadata `software`/`software_version`;
  `allowed_role_codes` tiếp tục dùng semantics read của F002.
- Tạo `DocumentRevision` bất biến cho mỗi upload, lưu content hash, MIME type,
  kích thước, URI blob, metadata project/software/version và trạng thái
  ingestion. Re-upload tạo revision mới, không ghi đè revision cũ.
- Xử lý nền theo các bước extract text -> normalize -> chunk -> embed -> index.
  Job state nằm trong PostgreSQL để có thể retry an toàn; không cần Redis hay
  broker ngoài ở F003.
- Dùng embedding adapter với model self-hosted. Embedding profile là cấu hình
  server-side duy nhất, gồm `EMBEDDING_MODEL_ID`, `EMBEDDING_MODEL_VERSION`,
  `EMBEDDING_DIMENSION` và `EMBEDDING_DISTANCE_METRIC`; giá trị khởi đầu là
  `BAAI/bge-m3`, dimension `1024`, metric `cosine`. Version phải là model
  revision cụ thể, không được là `unspecified`; client không được gửi hoặc
  chọn profile. Test inject deterministic fake profile/embedder, không tải
  model hoặc gọi dịch vụ bên ngoài.
- Tạo `DocumentChunk` bất biến với ordinal, text, start/end character offsets,
  content hash và embedding. Metadata `project_id`, `software`,
  `software_version`, `document_id`, `revision_id` phải hiện diện ở đường
  index/filter.
- Expose retrieval qua service/API chỉ nhận query và **server-built**
  `AuthorizedScope`. Public HTTP request không được truyền `project_id`, danh
  sách document IDs, ACL filter, hoặc `AuthorizedScope` để hệ thống tin cậy.
  Identity dependency xây scope bằng F002 authorization service trước query.
- Vector query phải áp dụng authorized predicate trong PostgreSQL trước/trong
  truy vấn top-k; không vector-search toàn bộ rồi lọc chunks ở memory, LLM,
  hay client.
- Trả mỗi hit với citation ổn định gồm `document_id`, `revision_id`,
  `chunk_id`, ordinal, offsets, title, source hash và metadata
  project/software/version. Citation ID được dẫn xuất từ các ID bất biến của
  revision/chunk, không từ rank hay nội dung response.
- Append audit event cho upload và mỗi retrieval allow/deny, nhưng event deny
  không tiết lộ title, metadata hoặc chunk của resource bị từ chối.

### Out
- Chat UI, prompt assembly, answer generation, reranking, hybrid/BM25 search,
  OCR cho ảnh/scanned PDF, và connector đồng bộ từ nguồn ngoài.
- Chia sẻ public, group grants, admin bypass, generic `document:write` policy
  hoặc quản trị project/role mới. F003 chỉ yêu cầu uploader là member project;
  policy write chi tiết là feature sau.
- Xoá/garbage-collect revision/blob, vector database độc lập, distributed queue
  (Redis/RabbitMQ), hoặc copy/chạy source trong `references/`.

## Architecture Decisions
- Tham khảo legacy flow tại `references/backend/ruvie/routers/files.py`,
  `routers/retrieval.py`, `retrieval/` và `storage/`; chỉ kế thừa ý tưởng
  upload -> loader -> chunk/embed/index -> sources. Active application không
  import, chạy, hay phụ thuộc runtime legacy.
- Legacy mặc định dùng local upload, Chroma và MiniLM. F003 chủ động thay bằng
  PostgreSQL + pgvector để predicate ACL F002 và vector retrieval cùng nằm ở
  database authority, giảm nguy cơ lệch metadata/ACL giữa hai datastore.
- `AuthorizedScope` là object typed nội bộ, chứa actor và predicate/subquery
  documents được phép đọc. Nó được dựng từ authenticated identity qua
  F002 `document:read` policy; endpoint public không deserialize scope từ body
  hoặc query string.
- Chỉ index revision có trạng thái `ready`. Retry cùng revision phải idempotent:
  không sinh chunks/vectors duplicate. Revision thất bại không được retrieve.
- `EmbeddingProfile` được parse/validate một lần khi application khởi động và
  inject vào upload service/ingestion worker; production code không gọi
  `os.getenv()` trực tiếp tại request/job path. `model_id` và `model_version`
  phải non-empty; dimension phải đúng `1024` của `Vector(1024)` hiện tại; metric
  phải là `cosine`. Nếu cần model khác dimension, phải có migration/schema
  embedding mới, không chỉ thay đổi `.env`.
- Mỗi model embedding có `model_id`, pinned `model_version`, dimension và
  distance metric được snapshot cùng revision/index. Không trộn vector từ
  model/dimension khác trong một truy vấn.
- Citation ổn định trong vòng đời một retained revision. Nếu nội dung thay đổi,
  tạo revision mới và citation mới; citation revision cũ vẫn resolve được khi
  revision còn giữ lại.

## Data Model

| Entity | Trách nhiệm tối thiểu | Constraints chính |
|---|---|---|
| `DocumentRevision` | Snapshot bất biến của một upload | FK `document_id`; revision number unique theo document; content hash, blob URI, MIME type, size, software/version, ingestion state, embedding model metadata |
| `IngestionJob` | Theo dõi/retry pipeline nền | FK revision; state, attempt count, error code an toàn; một job active cho một revision |
| `DocumentChunk` | Đơn vị retrieve và citation | FK revision/document; ordinal unique theo revision; offsets hợp lệ; text/content hash; metadata filter; embedding vector đúng dimension/model |

`Document.project_id` vẫn là authority cho tenant boundary. Project metadata được
copy có chủ đích vào chunk/index để filter hiệu quả, nhưng phải khớp với
`Document.project_id`; không được xem metadata copy là source of truth ACL.

## Flow
1. Authenticated caller upload file cùng `project_id`, title, software và
   software version. Service xác minh caller là membership của project và xác
   minh role codes hợp lệ.
2. Service dùng `EmbeddingProfile` server-side để snapshot metadata embedding,
   lưu blob private, tạo/ghi `Document`, `DocumentRevision` và `IngestionJob`,
   rồi audit upload. Request trả revision ở trạng thái pending; không chờ
   embedding hoàn tất.
3. Worker claim job, lấy blob, extract text, tạo chunks có offsets xác định,
   embed bằng model pinned, rồi insert chunks/vectors vào pgvector trong một
   trạng thái nhất quán. Thành công chuyển revision sang `ready`; thất bại lưu
   lỗi an toàn và không publish chunks.
4. Caller gửi retrieval query. Identity layer tạo `AuthorizedScope` bằng
   F002; public request không có field scope hoặc ACL filter.
5. Retriever chạy top-k cosine search chỉ trên chunks của `ready` revisions
   nằm trong predicate scope và filters metadata server-approved, sau đó tạo
   citations từ immutable revision/chunk fields.
6. Service trả hits/citations và append audit allow; empty/denied result append
   audit phù hợp mà không làm lộ resource ngoài scope.

## Acceptance Criteria
- [ ] Migration trên PostgreSQL trống tạo được revision, ingestion job, chunk
      và pgvector schema/index cần thiết; schema liên kết đúng `Document` và
      `Project` của F002.
- [ ] Upload của member tạo private blob, revision pending và job; upload bởi
      non-member bị deny và không tạo blob/document/revision.
- [x] Metadata project/software/version được persist ở revision và hiện diện
      trên chunk/index; chunk metadata project luôn khớp project của document.
- [ ] Worker xử lý PDF/text fixture thành chunks có ordinal/offset xác định,
      embeddings model metadata, và revision `ready`; retry không duplicate.
- [x] Application từ chối khởi động khi embedding profile thiếu model ID/model
      revision, dùng dimension khác `1024`, hoặc metric khác `cosine`; upload
      snapshot đúng profile server-side, không dùng hard-code hay input client.
- [x] Revision failed hoặc pending không xuất hiện trong retrieval.
- [x] Public retrieval API không nhận client-controlled `AuthorizedScope`,
      project ID, document IDs hay ACL predicate; scope chỉ được dựng server
      side từ authenticated identity và F002 policy.
- [x] User chỉ thuộc Project Alpha không thể retrieve chunk/citation/nội dung
      từ document hay revision Project Beta, kể cả khi query khớp mạnh hơn với
      Beta hoặc client cố đưa Beta ID vào request.
- [x] Direct, non-expired `AccessGrant` F002 cho một document cho phép search
      chunks của đúng document đó, không mở chunks khác trong cùng project.
- [x] Citation trả về có ID ổn định qua các retrieval lặp lại của cùng revision
      và chứa document/revision/chunk IDs, ordinal, offsets, title, source hash
      và software/version; rank thay đổi không đổi citation ID.
- [ ] Upload và retrieval allow/deny tạo audit event an toàn; deny không lộ
      metadata hoặc content ngoài authorized scope.
- [x] Test suite chạy bằng lệnh documented trong README, dùng fake embedder và
      gồm Project Alpha/Project Beta isolation test.

## Tasks
- [x] F003-001 Chốt ORM schema, enums, constraints, migrations và pgvector
      indexes cho `DocumentRevision`, `IngestionJob`, `DocumentChunk`.
- [x] F003-002 Implement private `BlobStore` ports/adapters local và
      S3-compatible, validation upload, content hashing và revision creation.
- [x] F003-003 Implement PostgreSQL-backed ingestion worker: extraction,
      deterministic chunking/offsets, idempotent job lifecycle và model-pinned
      embedding adapter; thêm `EmbeddingProfile` server-side, config validation,
      injection vào upload/worker, và thay hard-code embedding metadata F003-002.
- [x] F003-004 Implement pgvector chunk repository/search nhận typed
      `AuthorizedScope`, áp ACL predicate trong database và chỉ search revision
      `ready`.
- [x] F003-005 Expose upload và retrieval API seams: identity xây server-side
      scope, metadata validation, safe error contract và audit integration.
- [x] F003-006 Implement stable citation builder/resolver cho revision/chunk
      provenance và retrieval response contract.
- [x] F003-007 Viết fixtures/tests cho migration, upload deny, idempotent
      ingestion, pending/failed exclusion, Alpha/Beta isolation, direct grant,
      anti-client-scope injection và citation stability.
