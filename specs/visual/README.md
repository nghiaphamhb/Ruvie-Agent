# Visual specifications — Ruvie Agent

Cập nhật: **2026-10-10**. Nguồn chuẩn để đọc visual specs hiện tại.
Các file `.drawio` mở và chỉnh sửa bằng diagrams.net/draw.io.

## Danh sách sơ đồ

| Tài liệu | Nội dung | Trạng thái |
| --- | --- | --- |
| [Runtime Architecture v1.1.0](<Ruvie-Agent Runtime Architecture.version1.1.0.drawio>) | runtime active |
| [ER Diagram v1.1.0](<Ruvie-Agent ER Diagram.version1.1.0.drawio>) | 12 bảng, 14 FK theo models và migrations 0001–0008 | Schema active |

Runtime v1.1.0 thay v1.0.0; ER v1.1.0 thay v1.0.1. Các phiên bản cũ có thể
xem trong Git history. Không giữ hai tên file cùng đại diện cho runtime hiện tại.

## Cách đọc

- Màu xanh dương: browser, API, services và LLM đã tích hợp.
- Màu xanh lá: dữ liệu, private storage, ingestion và embedding.
- Màu tím: cấu hình server/proxy.
- Màu cam cùng nhãn **TO-BE/ĐỀ XUẤT**: chưa triển khai. Không suy ra rằng endpoint,
  bảng settings hoặc trang quản trị đã tồn tại.
- Mũi tên runtime là tương tác logic. Cùng đường LLM guarded adapter được dùng
  cho lấy model và chat. LLM_PROXY_URL không điều khiển embedding adapter.
- ERD dùng crow’s foot theo constraint DB. Mỗi composite FK chỉ có một đường.
  Một user có 0..1 settings row; một revision có 0..1 job theo DB uniqueness.
  Các service upload luôn tạo job cho revision mới, nhưng DB không buộc mọi
  revision phải có job. Các FK nullable được thể hiện là optional.

## Đối chiếu với mã active

| Phần | Nguồn được đọc |
| --- | --- |
| Lifecycle/routers/identity | `backend/ruvie/main.py`, `dependencies.py`, `api/{auth,llm,documents,chat,projects,security}.py` |
| Auth/session | `backend/ruvie/services/auth.py`, `models/auth.py`, migration `0005_auth_sessions.py` |
| LLM/settings/transport | `backend/ruvie/services/llm.py`, `adapters/llm.py`, `config.py`, `models/llm.py`, migration `0008_user_llm_settings.py` |
| Upload/worker/status | `backend/ruvie/services/documents/{upload,ingestion,status}.py`, `worker_cli.py`, `models/documents.py`, migration `0006_revision_uploader.py` |
| Authorization/retrieval/citation | `backend/ruvie/services/{access,retrieval,chat}.py`, `services/documents/citation.py`, `models/{access,projects}.py` |
| Audit immutability | `backend/ruvie/models/audit.py`, migration `0007_audit_event_immutability.py` |
| Locale/UI state | `frontend/src/main.ts`, `App.svelte`, `lib/i18n/{locale,index,messages}.ts`, `lib/components/LanguageSelector.svelte` |
| To-be quản trị/locale | [Locale backlog](../to-be/ui-localization-evolution.md), [Admin settings backlog](../to-be/llm-proxy-admin-settings.md) |

Các sơ đồ mô tả active project. `references/` không phải runtime dependency.
Các tài liệu định hướng rộng hơn như `specs/02-architecture.md` có thể chứa
thành phần tương lai; không coi ticket/tool adapter là đã triển khai.

## Những điểm được sửa so với sơ đồ cũ

- Frontend đã nối auth, project, upload/status, model/LLM và chat APIs; không còn
  nhãn “not API-integrated yet”.
- Auth hiện là password/cookie session với PostgreSQL; không phải IdP bắt buộc
  hoặc identity do client khai.
- Embedding providers được nối vào API lifecycle và worker process. Retrieval
  và upload ghi audit; không còn nhãn “production providers not wired” hoặc
  “audit not wired”.
- Thêm LLMConnectionService, guarded adapter, personal settings/server fallback,
  model verification và SOCKS5 tùy chọn; không có direct fallback khi proxy lỗi.
- Thêm locale F008 trong browser. Locale chưa lưu theo tài khoản/tổ chức trên DB.
- ERD thêm password_hash, auth_sessions, user_llm_settings, uploaded_by_user_id
  và append-only audit theo migrations 0005–0008.
- Blob store hiện tại là LocalBlobStore. S3 adapter không được vẽ như thành phần
  đã triển khai. HTTP upload tạo document mới; khả năng thêm revision vào cùng
  document hiện có ở service, chưa có document_id trong multipart route.

## Giới hạn cần đọc đúng

- Revision content và chunk text/vector bất biến; ingestion lifecycle có thể
  đổi. Worker cleanup/retry chỉ áp dụng partial chunks của revision chưa ready.
- ACL là membership + allowed role hoặc direct read grant còn hạn. Project ID
  trong upload chỉ là resource cần kiểm tra; không phải phạm vi quyền do client cấp.
- Status endpoint cho uploader theo dõi job hoặc người có document-read access;
  không đưa blob_uri ra browser. Trường running lấy từ job state.
- API encode structured chat events thành SSE. `/documents/retrieve` hiện vẫn
  gọi query embedder trực tiếp ở route; đây là ngoại lệ hiện có, không phải layer
  mới hoặc pattern đề xuất cho endpoint khác.
- Chat request đóng DB session trước stream; câu hỏi độc lập. History/draft chỉ
  ở trang, không có bảng chat history. Locale UI không gửi vào payload và không
  quyết định ngôn ngữ trả lời LLM.
- `/health` và `/ready` trả status ok; hiện không phải DB readiness probe.
- Org default, admin settings, URL override, date/time locale và lazy catalogs
  thuộc backlog. Nguồn lưu/table/API mới chưa được chốt; ERD không thêm bảng giả.

## Kiểm tra tài liệu

Các kiểm tra cho lần cập nhật này:

- Parse XML, cell IDs, parent/source/target references và page bounds.
- Đối chiếu ERD với `Base.metadata`: đủ 12 bảng, cột/nullable và 14 FK.
- Render offline cả 9 trang bằng SVG từ cùng geometry, xem hình và kiểm tra
  text overflow. Preview QA nằm dưới `logs/dev/visual-preview`, không phải source
  runtime hoặc dữ liệu người dùng.
- Kiểm tra liên kết tài liệu và whitespace. Không thay production code/schema;
  không chạy lại suite ứng dụng chỉ cho thay đổi tài liệu này.

Không có API key, nội dung tài liệu thực tế hoặc dữ liệu tài khoản trong sơ đồ.
