# Backend readability — 2026-10-07

Đã cập nhật skill implement và 39 file backend: thêm docstring/chú thích ở điểm
quan trọng, tách khai báo hàm và request/cấu hình dài. Phần thực thi giữ nguyên:
đối chiếu AST của 53 file Python sau khi bỏ docstring đều đạt.

Docstring mô tả công dụng và input/output. Chú thích giải thích lý do cần kiểm tra
quyền, giữ key, kiểm tra mạng, rollback hoặc retry. Không thêm lớp/dependency.
Migration versions/ giữ nguyên; package rỗng không cần chú thích.

## Từng file đã thay đổi

Các hàm/class đã có trước; đợt này bổ sung mô tả và trình bày dễ đọc hơn.

| File | Hàm/class và input → output | Điểm đã làm rõ |
|---|---|---|
| [ruvie/config.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/config.py>) | load_settings: env → Settings | Tách cấu hình nhiều dòng; quyền local do server cấp. |
| [ruvie/database.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/database.py>) | create_database_engine/create_session_factory: URL/engine → pool/factory | Tài nguyên dùng chung và session mỗi request. |
| [ruvie/dependencies.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/dependencies.py>) | get_authenticated_user_id/get_session: cookie/request → user/session | Identity từ server; session đóng sau request. |
| [ruvie/main.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/main.py>) | lifespan: app → tài nguyên; service_status → status | Startup/shutdown; health không kiểm tra DB. |
| [ruvie/password_cli.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/password_cli.py>) | main: email/password → hash, exit code | Nhập mật khẩu kín; chỉ cập nhật user đã có. |
| [ruvie/worker_cli.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/worker_cli.py>) | main/run_worker_loop: hàng đợi/stop event → xử lý job | Session mỗi job; poll theo giây và dừng bằng signal. |
| [ruvie/adapters/blob_storage.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/adapters/blob_storage.py>) | LocalBlobStore/S3BlobStore: bytes/URI → blob/bytes | Chống vượt thư mục; private; caller kiểm tra quyền trước đọc. |
| [ruvie/adapters/embedding.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/adapters/embedding.py>) | embed_query/embed: chuỗi/danh sách → vector | JSON, timeout 60 giây, vector đúng thứ tự input. |
| [ruvie/adapters/llm.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/adapters/llm.py>) | list_models/stream/PinnedLlmTransport: request → models/text/response | Bearer tùy chọn, bỏ cookie, IP/Host/TLS, ví dụ API. |
| [ruvie/api/auth.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/api/auth.py>) | login/current_session/logout: credentials/cookie → session/204 | Method/path, cookie HttpOnly, Origin/CSRF. |
| [ruvie/api/chat.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/api/chat.py>) | chat: message/session → SSE | Event trả về và context đã kiểm tra quyền. |
| [ruvie/api/documents.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/api/documents.py>) | upload_document/retrieve_chunks/get_revision_status → IDs/chunks/status | Multipart/JSON, kiểm tra kích thước, MIME từ bytes. |
| [ruvie/api/llm.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/api/llm.py>) | năm API kết nối/model → metadata/catalog/lựa chọn/204 | Request/response, session, lỗi không lặp lại key/body. |
| [ruvie/api/projects.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/api/projects.py>) | list_projects: session → items | Project của user hiện tại. |
| [ruvie/api/security.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/api/security.py>) | check_origin/verify_csrf: request/session → cho phép hoặc lỗi | Điều kiện 401/403 ở biên HTTP. |
| [ruvie/contracts/auth.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/contracts/auth.py>) | LoginRequest/AuthResponse: JSON → dữ liệu parse | Cấu trúc login/session; field thừa ở login bị từ chối. |
| [ruvie/contracts/chat.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/contracts/chat.py>) | ChatRequest/ChatStreamEvent: message/event → JSON/SSE | Chat chỉ nhận message; dòng trống kết thúc SSE event. |
| [ruvie/contracts/documents.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/contracts/documents.py>) | RetrievalBody: query/limit → input retrieval | Quyền và identity do server xác định. |
| [ruvie/contracts/llm.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/contracts/llm.py>) | ConnectionUpdateRequest/ModelsResponse → input/output | Key bỏ field/rỗng khác nhau; SecretStr; chọn lại model. |
| [ruvie/models/access.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/models/access.py>) | AccessGrant: row → quyền đọc trực tiếp | User, tài liệu và thời hạn grant. |
| [ruvie/models/audit.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/models/audit.py>) | AuditEvent: row → quyết định allow/deny | DB bảo vệ event khỏi sửa/xóa. |
| [ruvie/models/auth.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/models/auth.py>) | User/AuthSession: row → tài khoản/phiên | DB lưu hash session token, không lưu token cookie gốc. |
| [ruvie/models/base.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/models/base.py>) | Base → metadata chung | Metadata cho models và Alembic. |
| [ruvie/models/documents.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/models/documents.py>) | Document/Revision/Chunk/Job → dữ liệu tài liệu | Bất biến, URI private, offset ký tự, vector 1024 chiều. |
| [ruvie/models/llm.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/models/llm.py>) | UserLlmSettings → cấu hình/lựa chọn | URL null không sao chép key server; catalog đã kiểm tra. |
| [ruvie/models/projects.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/models/projects.py>) | Project/Role/Membership → user/project/role | Liên kết dùng cho quyền đọc, upload, liệt kê project. |
| [ruvie/models/__init__.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/models/__init__.py>) | Import models → đăng ký metadata | Alembic thấy đủ bảng active. |
| [ruvie/services/access.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/services/access.py>) | readable_documents_statement: user → SQL predicate | Role hoặc grant còn hạn; dialect chưa hỗ trợ phải deny. |
| [ruvie/services/audit.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/services/audit.py>) | append: hành động/quyết định → AuditEvent | Add/flush; caller quyết định commit/rollback. |
| [ruvie/services/auth.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/services/auth.py>) | authenticate/create_session/resolve_session → user/session | Scrypt, hash token, hết hạn, so sánh CSRF. |
| [ruvie/services/chat.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/services/chat.py>) | prepare/stream: user/question → hits/SSE | Context đã được phép; stream rỗng là lỗi. |
| [ruvie/services/llm.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/services/llm.py>) | save_connection/select_model: user/input → catalog/ID | Kiểm tra trước lưu; key theo URL; rollback; model mất. |
| [ruvie/services/projects.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/services/projects.py>) | list_for_user: user → ProjectSummary[] | Membership; bỏ trùng; sắp xếp ổn định. |
| [ruvie/services/retrieval.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/services/retrieval.py>) | retrieve/search: user/vector → RetrievalHit[] | Quyền trước ranking; revision READY; SQLite dùng cho test. |
| [ruvie/services/documents/citation.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/services/documents/citation.py>) | CitationBuilder.build: metadata → Citation | ID gắn document/revision/chunk; không chứa URI private. |
| [ruvie/services/documents/ingestion.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/services/documents/ingestion.py>) | run_next/_ingest/_fail: job → chunks/vectors/status | 64 text chunks mỗi batch, khóa job, heartbeat, retry. |
| [ruvie/services/documents/status.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/services/documents/status.py>) | get_revision_status: user/revision → status hoặc None | Uploader theo dõi job; user khác cần quyền đọc. |
| [ruvie/services/documents/upload.py](<D:/Github Repository/Ruvie-Agent/backend/ruvie/services/documents/upload.py>) | create_revision: request → UploadResult | Hash/key mới; rollback DB và dọn blob khi lỗi. |
| [migrations/env.py](<D:/Github Repository/Ruvie-Agent/backend/migrations/env.py>) | offline/online: cấu hình → SQL hoặc áp dụng migration | Metadata; giữ nguyên migration đã áp dụng. |

## PinnedLlmTransport

Transport là phần gửi request ra mạng. Class nhận httpx.Request, kiểm tra đích
kết nối, rồi trả httpx.Response. Nó không lưu model/key hay kiểm tra quyền tài liệu.

URL do người dùng nhập có thể trỏ tới nội bộ hoặc metadata của máy/cloud.
SSRF là việc dùng server để gửi request tới nơi không được phép.
DNS còn có thể đổi IP giữa lúc kiểm tra và lúc kết nối (DNS rebinding).

~~~mermaid
flowchart LR
    A[HTTP request] --> B[Kiểm tra URL]
    B --> C[DNS trả IP]
    C --> D{Mọi IP đều được phép?}
    D -->|Không| E[Từ chối]
    D -->|Có| F[Kết nối tới IP đã kiểm tra]
    F --> G[Giữ Host và tên TLS gốc]
    G --> H[HTTP response]
~~~

Ví dụ giả định: https://llm.example/v1/models phân giải tới 93.184.216.34.
Request dùng IP này để kết nối, nhưng Host và tên TLS vẫn là llm.example.
Nếu DNS sau đó đổi sang 127.0.0.1, request này không bị chuyển đích.

| Cú pháp/biến | Ý nghĩa |
|---|---|
| class PinnedLlmTransport(httpx.HTTPTransport) | Kế thừa transport HTTP có sẵn, thêm kiểm tra trước khi gửi. |
| __init__ / self | Hàm khởi tạo; self là đối tượng hiện tại. |
| tuple[str, ...] = () | Tuple chứa số lượng chuỗi bất kỳ; mặc định rỗng. Một origin: ("http://localhost:11434",). |
| super().__init__(trust_env=False) | Khởi tạo lớp cha, bỏ TLS settings từ env; Client sở hữu cũng tắt trust_env để bỏ proxy env. |
| handle_request(request: httpx.Request) -> httpx.Response | Ghi đè hàm gửi request; type hints mô tả input/output, không tự validate dữ liệu. |
| origin | Scheme + host + port, không gồm path. |
| origin in self.allowed_local_origins | Local/LAN chỉ được phép qua allowlist của server. |
| raw_host.decode("ascii") | Đổi hostname dạng bytes đã chuẩn hóa thành chuỗi. |
| port or (443 if ... else 80) | Có port thì dùng; thiếu thì HTTPS dùng 443, HTTP dùng 80. |
| socket.getaddrinfo(..., type=socket.SOCK_STREAM) | Lấy địa chỉ IPv4/IPv6 phù hợp để kết nối TCP. |
| answer[4][0] | Phần tử thứ 5 là sockaddr; phần tử đầu của sockaddr là IP. |
| ipaddress.ip_address(...) | Tạo đối tượng có thuộc tính is_private, is_global, is_link_local... |
| getattr(address, "ipv4_mapped", None) or address | IPv6 bọc IPv4 thì lấy IPv4 để kiểm tra; không có thì giữ gốc. |
| forbidden / permitted | Áp dụng danh sách cấm và điều kiện cho phép; metadata/link-local luôn bị chặn. |
| headers.copy() | Sao chép header để không sửa request gốc. |
| request.url.copy_with(host=addresses[0]) | Tạo URL kết nối tới IP đầu tiên đã kiểm tra. |
| **request.extensions | Sao chép các tùy chọn có sẵn, như timeout, vào dict mới. |
| "sni_hostname": hostname | TLS SNI và kiểm tra chứng chỉ dùng tên gốc. |
| stream=request.stream | Giữ body/luồng bytes khi tạo request mới. |
| super().handle_request(pinned) | Transport cha gửi request đã kiểm tra ra mạng. |
| raise ... from None | Không nối traceback lỗi gốc; API còn trả thông báo lỗi an toàn. |

Ví dụ kết quả DNS:

~~~python
(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))
# answer[4]    = ("93.184.216.34", 443)
# answer[4][0] = "93.184.216.34"
~~~

Host là header HTTP giúp chọn đúng website/API khi một IP phục vụ nhiều domain.
SNI là tên gửi lúc bắt tay TLS; tên gốc cũng dùng kiểm tra chứng chỉ.
Khi URL đổi sang IP, cần giữ cả hai.

Giới hạn: kiểm tra toàn bộ IP DNS rồi dùng IP đầu tiên, chưa thử IP tiếp theo
nếu kết nối lỗi. API kết nối/model tạo client có transport này; chat server
hiện dùng client được inject. Nối lựa chọn cá nhân vào /chat thuộc F006-005.

Tài liệu chính thức:

- [HTTPX transports](https://www.python-httpx.org/advanced/transports/): transport và handle_request.
- [Python getaddrinfo](https://docs.python.org/3/library/socket.html#socket.getaddrinfo): cấu trúc tuple DNS.
- [HTTPCore sni_hostname](https://www.encode.io/httpcore/extensions/#sni_hostname): kết nối IP với hostname TLS.

## Kiểm tra

- Backend: 128 pass, 0 fail, 0 skip; có PostgreSQL/pgvector dùng một lần.
- Frontend: 10 pass, 0 fail, 0 skip; xác thực, SSE và API tài liệu.
- Skill: quick_validate báo Skill is valid! với chế độ UTF-8.
- AST: 53 file giữ nguyên phần thực thi; migration versions/ không đổi.
- git diff --check: đạt.

Lệnh backend:

~~~powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
~~~

Shell không tìm thấy npm nên chạy test script bằng Node có sẵn:

~~~powershell
# Chạy từ frontend/
$testFiles = @(rg --files tests -g '*.test.mjs' -g '!**/[aA][rR][cC][hH][iI][vV][eE]/**')
& 'C:/Users/phamd/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' --experimental-strip-types --test @testFiles
~~~

Lệnh kiểm tra skill:

~~~powershell
.\.venv\Scripts\python.exe -X utf8 'E:/Apps/Codex/skills/.system/skill-creator/scripts/quick_validate.py' .agents/skills/ruvie-feature-workflow
~~~

