# F005 - Đăng nhập và xử lý tài liệu để chat chạy được

**Trạng thái:** Chưa hoàn tất. F005-001 đến F005-006 đã hoàn thành;
F005-007 còn mở vì lần kiểm tra provider thật hiện tại nhận HTTP 429 từ LLM.
Embedding thật trả vector 1024 chiều; chưa xác minh trọn luồng upload → ready →
chat/citation với provider thật.

## Goal

Người dùng có thể tự đăng nhập, tải tài liệu lên, thấy khi nào tài liệu đã
được xử lý, rồi hỏi chat về tài liệu đó. Backend chạy với PostgreSQL/pgvector
và tự xử lý tài liệu; người phát triển không phải gọi worker bằng tay.

Trong spec này, *job* là việc xử lý tài liệu đang chờ trong database;
*revision* là bản lưu của một lần upload; *chunk* là một đoạn nhỏ lấy từ tài
liệu để tìm kiếm.

## User Story

As a project member, I want to sign in, upload a document, see its processing
status, and ask about it in chat, so that I can use the MVP from the web UI.

## Scope

### In

- Không tạo database riêng cho integration test migration PG-01. Hướng dẫn chủ
  dự án dùng PostgreSQL của môi trường dev, kết nối và tự xác minh migration/
  schema. Agent không tự kết nối hoặc chạy migration trên database dev.
- Cho tài khoản được cấp sẵn đăng nhập, xem phiên và đăng xuất. Backend lấy
  `User.id` từ phiên hợp lệ và đặt `request.state.domain_user_id` cho các API
  đang có. Đề xuất lưu phiên trong PostgreSQL, gửi mã phiên ngẫu nhiên qua
  cookie HttpOnly, giới hạn tuổi phiên và chống request giả mạo từ trang khác;
  mật khẩu chỉ lưu dạng hash. Không tin user ID hoặc role do trình duyệt gửi.
- Có lệnh chạy worker riêng với API. Worker dùng embedding provider đã cấu
  hình trên server để xử lý PDF/text và chuyển revision từ `pending` sang
  `ready` hoặc `failed`. Khi worker dừng giữa chừng, job có thể được chạy lại
  có giới hạn mà không tạo chunk trùng.
- Có form upload tối giản: chọn project mình tham gia, file và metadata cần
  thiết. Mọi member được upload vào project mình tham gia. Đề xuất gửi file bằng
  multipart thay cho `content_base64` hiện tại; sau upload, hiển thị `pending`,
  `running`, `ready` hoặc `failed`. Backend kiểm tra quyền trước khi trả trạng
  thái. `allowed_role_codes` do server đặt theo chính sách mặc định, không nhận
  từ client.
- Ghi audit cho upload được phép/bị từ chối và retrieval được phép/bị từ chối.
  Ứng dụng không được sửa hoặc xóa audit event cũ.
- Kiểm tra cả luồng đăng nhập → upload → worker → chat → citation với
  PostgreSQL tạm và provider HTTP giả trong test tự động. Sau đó hướng dẫn chủ
  dự án tự kết nối database dev thật; không dùng database dev làm database test.
  Thử luồng với embedding/LLM provider thật đã cấu hình trong `.env` cục bộ, ghi
  kết quả và giới hạn nếu môi trường chưa cho phép chạy. Project Alpha không
  được thấy dữ liệu của Project Beta. Cập nhật README cho cách chạy và cấu hình.

### Out

- Tự đăng ký, quên mật khẩu, OAuth/LDAP/SSO và quản trị tài khoản qua UI.
- Lưu/chia sẻ lịch sử chat; mỗi lần reload vẫn bắt đầu hội thoại mới.
- Skills, tools, compatibility, ticket, OCR, hybrid search và đổi dimension
  hoặc distance metric của embedding. Các việc này thuộc feature sau.

**Tham khảo `references/` trước khi code:**

| Việc | Mẫu legacy | Cách dùng trong F005 |
|---|---|---|
| Đăng nhập | `backend/ruvie/routers/auths.py:signin`, `create_session_response`; `backend/ruvie/utils/auth.py:get_current_user`; `src/routes/auth/+page.svelte` | Học luồng login/session và bố cục form. Legacy dùng JWT/SvelteKit; active dùng `User` F002 và Svelte/Vite nên cần contract riêng. |
| Upload và trạng thái | `backend/ruvie/routers/files.py:upload_file`, `get_file_process_status`; `src/lib/apis/files/index.ts:uploadFile`, `getFileProcessStatus` | Học trạng thái và cách hiển thị tiến độ. Legacy gửi multipart, còn API active nhận `content_base64`; đề xuất chuyển route sang multipart nhưng giữ `DocumentUploadService`. |
| Xử lý tài liệu | `backend/ruvie/routers/retrieval.py:process_file`, `save_docs_to_vector_db` | Học thứ tự extract → chunk → embed → index. Dùng `DocumentIngestionWorker` và pgvector active. |
| Chat UI | `src/lib/components/chat/Chat.svelte`; `src/lib/apis/streaming/index.ts:createOpenAITextStream` | Tham khảo cách bố trí và trạng thái. Giữ SSE contract F004; UI có thể custom sau. |

Ưu tiên tái sử dụng `DocumentUploadService`, `DocumentIngestionWorker`,
`AuthorizedRetrievalService`, chat service và model adapters của active project.
Không import code từ `references/`; kiểm tra license trước khi chép source.

## Flow

1. Người dùng nhập email/mật khẩu. Backend xác minh tài khoản được cấp sẵn,
   tạo phiên và trả cookie. Sai thông tin trả lỗi chung.
2. Với request được bảo vệ, backend kiểm tra phiên và tra `User` trong database.
   Nếu phiên hết hạn hoặc user bị khóa, trả `401` trước khi xử lý tài liệu.
3. UI nhận danh sách project mà user là member. User chọn project, PDF/text và
   metadata rồi bấm upload. Backend kiểm tra membership, lưu blob private,
   tạo revision `pending` và job; response chỉ trả các ID cần thiết.
4. Worker lấy job, đọc blob, chia nội dung thành chunks, gọi embedding provider
   và lưu vectors. Thành công chuyển revision sang `ready`; lỗi lưu trạng thái
   an toàn và cho retry theo quy tắc đã định.
5. UI hỏi trạng thái bằng revision ID. Backend chỉ trả trạng thái cho người
   upload hoặc người có quyền đọc document; ngoài quyền trả phản hồi không
   tiết lộ document có tồn tại hay không.
6. User đặt câu hỏi. F004 dùng identity từ phiên, tìm chunks đã được phép rồi
   stream câu trả lời và citations. Chat không nhận scope từ client.

## Acceptance Criteria

- [x] Chủ dự án tự áp dụng migration trên PostgreSQL dev có pgvector sau khi
      rà soát đích và SQL; xác minh revision head, `vector(1024)`, HNSW cosine
      index, khóa ngoại và ràng buộc. Agent chỉ hướng dẫn, không truy cập DB.
- [x] Đăng nhập đúng tạo phiên; đăng xuất, phiên hết hạn, tài khoản bị khóa và
      thiếu phiên đều không vào được các API bảo vệ; request giả mạo từ trang
      khác không thể dùng cookie phiên để upload.
- [x] Client không thể tự đổi user ID, role, project hoặc phạm vi tài liệu để
      đọc tài liệu ngoài quyền.
- [x] Mọi member upload vào project mình tham gia tạo đúng một private blob,
      revision `pending` và job; non-member bị từ chối và không để lại
      blob/bản ghi. Client không thể chọn `allowed_role_codes`; server đặt ACL
      role theo chính sách mặc định.
- [x] Worker chạy bằng lệnh README, xử lý PDF/text thành chunks/vectors đúng
      embedding profile; revision `ready` có thể được chat trích dẫn.
- [x] Worker restart/retry không tạo chunks trùng; lỗi provider hoặc nội dung
      rỗng trả trạng thái/lỗi an toàn, không retry mãi mãi.
- [x] UI có login, upload và trạng thái xử lý; trạng thái ngoài quyền không lộ
      tên file, project, blob URI hoặc nội dung.
- [x] Audit có upload và retrieval allow/deny; ứng dụng không thể sửa/xóa
      audit event cũ; denial không chứa dữ liệu private.
- [x] Test toàn luồng trên PostgreSQL tạm chứng minh user Alpha không thấy
      status, chunk, citation hoặc nội dung private của Project Beta trong
      prompt và API response. Đã xác minh bằng test F005-007 trên container
      PostgreSQL/pgvector tạm.
- [x] Đã thử kiểm tra thủ công với provider thật từ `.env` cục bộ, ghi lại
      kết quả upload → xử lý → chat và lỗi nếu có; không in hoặc lưu API key.
- [x] Backend/frontend tests, migration SQL và README đạt; AC cũ ở F001–F004
      chỉ tick nếu có bằng chứng trực tiếp.

Ghi nhận kiểm tra provider thật ngày 2026-10-04: embedding trả HTTP 200 với
vector 1024 chiều; LLM `google/gemma-4-26b-a4b-it:free` trả HTTP 429 khi kiểm
tra trực tiếp. Backend port 8000 khỏe, nhưng chat UI vẫn báo provider unavailable.
Chưa ghi nhận một lần upload thực tế chuyển `ready` rồi được trích dẫn thành công
bằng provider thật.

## F005-001 API and security contract

Các endpoint dưới đây là contract đã chốt cho các task triển khai tiếp theo.
Đây là đặc tả, không khẳng định các endpoint đã tồn tại trong code.

### Authentication and session

| Endpoint | Request | Success | Failure |
|---|---|---|---|
| `POST /auth/login` | JSON `{"email":"...","password":"..."}` | `200`; đặt cookie session; body `{"user":{"id":"…","display_name":"…"},"csrf_token":"…"}` | `401` với cùng thông báo cho email không tồn tại, sai mật khẩu hoặc user inactive; `422` dữ liệu sai định dạng |
| `GET /auth/session` | Cookie tự gửi | `200` cùng user tối thiểu và CSRF token mới/hiện hành | `401` nếu thiếu, hết hạn, thu hồi session hoặc user inactive |
| `POST /auth/logout` | Cookie và header `X-CSRF-Token` | `204`; thu hồi session và xóa cookie | `401` session không hợp lệ; `403` CSRF/Origin không hợp lệ |

- Cookie tên `ruvie_session`, chứa token ngẫu nhiên tối thiểu 256 bit. Database
  chỉ lưu SHA-256 của token, không lưu token thô. Session có tuổi tuyệt đối 12
  giờ, không gia hạn trượt; xóa cookie khi logout với cùng `Path` và flags.
- Cookie có `HttpOnly`, `SameSite=Lax`, `Path=/`; bật `Secure` trên HTTPS và
  môi trường dev dùng HTTPS. Không cho JavaScript đọc cookie.
- CSRF token là token ngẫu nhiên gắn với session, trả trong response body của
  login/session. Các request thay đổi trạng thái dùng cookie phải gửi token đó
  trong `X-CSRF-Token`. Backend so sánh constant-time và kiểm tra `Origin`
  chính xác với origin frontend được cấu hình; thiếu/sai origin bị từ chối.
  Không bật wildcard origin. Login cũng kiểm tra Origin để tránh login CSRF.
- Mật khẩu chỉ lưu dạng hash bằng thuật toán password hashing chuyên dụng có
  salt (không dùng SHA-256 trực tiếp). User inactive không đăng nhập được và
  session đang tồn tại của họ không xác thực được.
- API không nhận user ID/role làm danh tính. Identity được giải ra từ session
  hợp lệ rồi gán vào `request.state.domain_user_id`.

### Projects, upload and status

| Endpoint | Request | Success | Failure |
|---|---|---|---|
| `GET /projects` | Cookie session | `200` `{"items":[{"id":"…","code":"…","name":"…"}]}` chỉ gồm project có membership | `401` session không hợp lệ |
| `POST /documents/upload` | `multipart/form-data`: `project_id`, `title`, `software`, `software_version`, `file`; cookie và `X-CSRF-Token` | `202` `{"document_id":"…","revision_id":"…","job_id":"…","status":"pending"}` | `401` session; `403` CSRF; `404` project không tồn tại/không có membership; `413` file quá lớn; `422` thiếu/sai metadata, file rỗng hoặc loại file không hỗ trợ |
| `GET /documents/revisions/{revision_id}/status` | Cookie session | `200` `{"revision_id":"…","status":"pending|running|ready|failed","error_code":null}` | `401` session; `404` revision không tồn tại hoặc người gọi không được xem |

- File tối đa **25 MiB (25 × 1024 × 1024 bytes)**; kiểm tra kích thước thực tế
  khi đọc upload, không chỉ tin `Content-Length`. File rỗng bị từ chối. MVP hỗ
  trợ PDF và plain text UTF-8; tên file và MIME do client gửi không được xem là
  bằng chứng loại file, backend xác nhận loại hỗ trợ trước khi tạo blob.
- Request upload không có `allowed_role_codes`, `user_id` hoặc role. Mọi member
  của project được upload; service vẫn kiểm tra membership từ database. Với
  document mới, server đặt `allowed_role_codes` bằng toàn bộ role code hiện
  hành trong domain policy (hiện là `BIM_CAD_SPECIALIST`, `DEVELOPER`,
  `IT_SUPPORT`). Khi vocabulary/policy đổi, cập nhật mặc định phía server.
- Upload chỉ trả ID và trạng thái; không trả blob URI, nội dung file, API key
  hay thông tin provider. Hệ thống tạo blob private, revision và job; lỗi DB
  sau khi ghi blob phải rollback và dọn blob.
- Status được trả cho người upload hoặc người hiện có quyền `document:read`.
  Không có quyền và ID không tồn tại đều trả `404` cùng cấu trúc phản hồi.
  `error_code` chỉ là mã an toàn do ứng dụng định nghĩa; không serialize lỗi
  upstream, stack trace, URI hoặc nội dung tài liệu. Client poll mỗi 2 giây,
  dừng khi `ready`/`failed`, tối đa 5 phút mỗi lần upload; sau đó hiển thị
  thông báo có thể tải lại trạng thái, không hủy job.
- Upload bị từ chối không tạo document, revision, job hoặc blob. Việc audit
  allow/deny upload được triển khai ở F005-006; contract lỗi không tiết lộ
  resource ngoài quyền.

### Ingestion retry contract

- Tối đa **3 lần chạy tổng cộng** cho mỗi job (lần đầu và tối đa hai lần retry).
  `attempt_count` tăng khi worker claim job. Lỗi provider/network tạm thời và
  worker bị dừng bất thường có thể retry; file rỗng, MIME không hỗ trợ, PDF
  không đọc được hoặc embedding profile không khớp là lỗi terminal.
- Retry có backoff 5 giây rồi 30 giây. Job hết lượt chuyển `failed`, revision
  `failed`, giữ `error_code` an toàn. Không retry vô hạn.
- Nếu worker chết khi job đang `running`, runner phải thu hồi job stale sau
  5 phút và đưa về `pending` khi còn lượt; nếu hết lượt thì đặt failed. Đây là
  hành vi cần triển khai trong F005-004, không phải khả năng của worker hiện tại.
- Tái xử lý cùng revision phải idempotent: không tạo chunk trùng ordinal.
  Worker phải xóa/rollback phần chunk chưa hoàn tất trước khi retry và chỉ
  chuyển revision sang `ready` khi toàn bộ vectors/chunks đã commit.

## Tasks

- [x] F005-001 Chốt contract phiên, project list, upload status, ACL upload và
      quy tắc retry.
  - Viết rõ các request/response sẽ dùng: đăng nhập, xem phiên, đăng xuất,
    liệt kê project của mình, upload file và xem trạng thái revision. Ví dụ
    `POST /auth/login` nhận email/mật khẩu, thành công đặt cookie; sai thông
    tin trả lỗi chung, không tiết lộ tài khoản có tồn tại.
  - Quy định cookie hết hạn khi nào, cách chống request giả mạo từ trang khác,
      giới hạn kích thước file và số lần retry một job. Đây là hợp đồng để các
      task backend/frontend sau cùng triển khai giống nhau.
  - Chốt mọi project member được upload vào project mình tham gia;
      `allowed_role_codes` là giá trị server-side theo chính sách mặc định,
      không có trong request client.
- [x] F005-002 Hướng dẫn chủ dự án kết nối PostgreSQL dev hiện có, áp dụng
      migration và xác minh schema/index (`PG-01`). Không tạo hoặc dùng database
      riêng cho integration test migration; agent không thực hiện kết nối.
  - Hướng dẫn xác định container/port PostgreSQL, xác nhận riêng tư host,
      database và user từ cấu hình local; không gửi `DATABASE_URL` hoặc secret.
  - Trước khi thay đổi dữ liệu, chủ dự án xác nhận đúng database dev, backup,
      pgvector khả dụng và quyền của user. Rà soát `alembic current` và SQL từ
      `alembic upgrade head --sql` trước khi tự chạy `upgrade head`.
  - Sau migration, chủ dự án xác nhận revision `0004_remove_embedding_model_version`,
      các bảng F002/F003, `vector(1024)`, khóa ngoại/unique/check constraints
      và HNSW cosine index bằng truy vấn PostgreSQL. Không reset/drop database.
  - Ghi nhận kết quả hoặc lỗi không kèm credentials. Task chỉ được đánh dấu xong
      sau khi chủ dự án báo đã xác minh database dev; agent không đọc `.env`,
      kết nối, migrate hoặc sửa dữ liệu.
- [x] F005-003 Thêm auth service/API và login UI; tạo tài khoản mẫu bằng cách
      cấp sẵn, không có signup công khai.
  - Thêm migration cho thông tin xác thực/phiên cần lưu. Tạo cách cấp một user
    đã có trong bảng `users` mật khẩu ban đầu; database chỉ lưu password hash.
  - Auth service kiểm tra email/mật khẩu, tạo phiên, xác minh phiên cho mỗi
    request và hủy phiên khi đăng xuất. Các API cũ lấy `domain_user_id` từ
    phiên này, không lấy từ body/header do client tự khai.
  - UI có form đăng nhập và nút đăng xuất. Tham khảo form/cookie flow trong
    `references/`, nhưng dùng Svelte/Vite và model `User` của active project.
  - Unit/API tests frontend/backend và migration SQL đạt. Chủ dự án đã xác nhận
    áp dụng chuỗi migration đến `0006_revision_uploader` trên PostgreSQL dev.
- [x] F005-004 Dùng embedding adapter active cho nhiều chunks; thêm lệnh chạy
      worker, phục hồi job và retry không trùng (`INGEST-01`, `INGEST-02`).
  - Mở rộng adapter embedding hiện có để nhận danh sách đoạn text và trả về
    danh sách vector cùng thứ tự, mỗi vector dài `1024`. Dùng model ID, URL
    và key trên server; không nhận các giá trị này từ tài liệu hoặc client.
  - Thêm lệnh worker chạy riêng: lấy job `pending`, đọc blob private, gọi
    `DocumentIngestionWorker`, chờ job tiếp theo và dừng gọn khi có lệnh dừng.
  - Khi provider lỗi hoặc worker bị ngắt, job có thể thử lại theo giới hạn đã
    chốt. Test chứng minh một revision không có hai chunk cùng ordinal dù job
    được chạy lại; file rỗng/PDF không đọc được có trạng thái lỗi an toàn.
  - Đã kiểm tra 19 test tập trung và toàn bộ backend suite (76 test). Runner
    heartbeat, retry/backoff, stale recovery, giới hạn 3 lượt, batch order,
    dọn chunks dở dang, vector sai và lỗi nội dung được kiểm tra. Không cần
    migration mới; worker dùng `attempt_count` và `updated_at` sẵn có.
- [x] F005-005 Thêm API project list/upload status và form upload/trạng thái;
      kiểm tra quyền ở database trước khi trả dữ liệu.
  - API project list chỉ trả project mà user là member. API status nhận
    revision ID, kiểm tra người gọi là uploader hoặc được đọc document rồi
    mới trả `pending`/`running`/`ready`/`failed`. Revision hiện chưa lưu người
    upload: thêm `uploaded_by_user_id` qua migration cho revision mới; với
    revision cũ, dùng quyền đọc document để quyết định có trả status hay không.
  - Chuyển upload route sang multipart theo quyết định trong F005-001, giữ
    `DocumentUploadService` để kiểm tra membership, lưu blob và tạo revision.
    Bỏ `allowed_role_codes` khỏi input client; service/API áp dụng ACL role
    mặc định phía server.
    UI cho chọn file, project và metadata; sau upload thì hỏi trạng thái định
    kỳ cho đến khi `ready` hoặc `failed`. Trạng thái `running` lấy từ job đang
    chạy; `ready`/`failed` lấy từ revision.
  - Với ID ngoài quyền, API trả phản hồi không tiết lộ document, file hay
    project. UI chỉ hiển thị thông báo an toàn do API trả về.
  - Unit/API tests và frontend build đạt. Chủ dự án đã xác nhận áp dụng
    `0006_revision_uploader` trên PostgreSQL dev.
- [x] F005-006 Thêm test upload deny/cleanup, audit upload và bảo vệ audit cũ
      (`UPLOAD-01`, `AUDIT-01`, `AUDIT-02`).
  - Test project member upload thành công và non-member bị từ chối; request
    không thể tự chọn `allowed_role_codes`. Trường hợp bị từ chối không tạo
    blob, document, revision hoặc job. Test cả lỗi database sau
    khi ghi blob để chắc chắn blob được dọn.
  - Ghi audit upload `allow`/`deny` với actor, action, outcome và lý do an
    toàn. Bảo đảm audit retrieval F002/F004 vẫn hoạt động.
  - Thêm ràng buộc ở PostgreSQL để ứng dụng không sửa/xóa audit event cũ, rồi
    kiểm tra update/delete bị từ chối trên PostgreSQL dev theo hướng dẫn README.
    Unit tests và SQL migration offline đạt. Chủ dự án xác nhận đã áp dụng
    `0007_audit_event_immutability` trên PostgreSQL dev và kiểm tra update/delete/
    truncate đều bị từ chối; agent không truy cập database.
- [ ] F005-007 Test luồng toàn phần với provider HTTP giả, user Alpha/Beta,
      lỗi provider và citations; cập nhật README và rà lại AC F001–F004.
  - Tự động chạy luồng với PostgreSQL tạm và provider HTTP giả: login Alpha,
      upload tài liệu Alpha, worker xử lý, chat nhận citation đúng; tài liệu
      Beta không xuất hiện trong kết quả hoặc prompt của Alpha.
  - Việc kiểm tra migration trên database dev thuộc F005-002 và do chủ dự án
      tự thực hiện. Integration test PostgreSQL tạm ở task này chỉ kiểm tra
      luồng end-to-end, không thay thế bước xác minh database dev.
  - Trên môi trường thủ công, dùng endpoint/model/key đã đặt trong `.env` để
    thử embedding và LLM thật. Ghi trạng thái từng bước và lỗi nếu có; không
    ghi giá trị key vào test output, log hoặc tài liệu.
  - Chạy backend/frontend suite và kiểm tra migration SQL theo README. Cập
    nhật README với lệnh khởi động worker/login; chỉ tick AC F001–F005 có
    bằng chứng kiểm tra đạt, ghi rõ phần nào còn bị chặn.
  - [x] E2E với PostgreSQL/pgvector tạm và HTTP provider giả: login Alpha/Beta,
    upload, worker, status, retrieval, chat/citation và loại trừ dữ liệu Beta;
    3 test đạt trên container tạm.
  - [x] README có lệnh chạy E2E và checklist provider thật an toàn.
  - [x] Backend suite (93 tests), frontend suite (10 tests) và migration SQL
    offline đều đạt.
  - [x] Đã kiểm tra provider thật và ghi lại kết quả: embedding trả vector 1024
    chiều; LLM trả HTTP 429; chat chưa hoàn tất. Không ghi secret hoặc response
    body của provider.
  - [ ] Hoàn tất kiểm tra thật theo README từ upload đến revision `ready`, chat
    thành công và citation; hiện bị chặn bởi HTTP 429 và chưa có bằng chứng
    upload/processing thực tế trong lần kiểm tra này.
  - Ghi chú kiểm thử: PostgreSQL tạm dùng `alembic_version.version_num`
    `VARCHAR(128)` vì migration ID `0004_remove_embedding_model_version` dài
    hơn giới hạn mặc định `VARCHAR(32)`. E2E không xác minh tạo bảng tracking
    Alembic mặc định từ database trắng; cần rà soát riêng nếu yêu cầu cài mới
    hoàn toàn bằng migration.

**Đã chốt:** Mọi member được upload vào project mình tham gia;
`allowed_role_codes` do server đặt theo chính sách mặc định, không nhận từ
client. Bỏ kiểm thử migration PG-01 trên database riêng; chủ dự án tự kết nối
và xác minh migration/schema trên PostgreSQL dev theo hướng dẫn. F005-007 vẫn
có integration test PostgreSQL tạm cho luồng end-to-end; agent không dùng DB dev.

**Bằng chứng F005-002:** Chủ dự án xác nhận quy trình migration trên PostgreSQL
dev đã thành công. Chủ dự án cũng xác nhận đã áp dụng migration đến
`0007_audit_event_immutability` và các kiểm tra trigger đạt; agent không truy cập
database.

**Giả định triển khai:** Tài khoản được cấp sẵn, phiên lưu trong PostgreSQL
và upload dùng multipart. Cookie, CSRF, giới hạn file và retry được chốt trong
F005-001 trước khi viết code tương ứng.
