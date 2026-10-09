# F004 - Chat cơ bản (MVP)

## Mục tiêu
Tạo màn hình chat đơn giản. Người dùng nhập câu hỏi, backend tìm các đoạn tài
liệu mà người dùng được phép xem, sau đó gọi LLM để tạo câu trả lời. Câu trả
lời hiển thị dần và có danh sách nguồn đã dùng.

## User Story
As an authenticated project user, I want to ask a technical question and see
an answer with sources, so that I can find reliable information in documents
I am allowed to read.

## Giải thích nhanh

| Từ ngữ | Ý nghĩa trong feature này |
|---|---|
| LLM | Dịch vụ tạo câu trả lời từ câu hỏi và tài liệu đã tìm được. |
| Retrieval | Tìm các đoạn tài liệu phù hợp với câu hỏi. |
| Authorized scope | Tập tài liệu mà một người dùng được phép đọc. Backend tự tạo tập này. |
| Citation | Thông tin nguồn của một đoạn tài liệu: document, revision, chunk và vị trí. |
| SSE | Cách backend gửi từng phần câu trả lời về trình duyệt ngay khi có. |

## Phạm vi

### Có làm
- Thay màn hình frontend hiện tại bằng chat UI tối giản: ô nhập câu hỏi, nút
  gửi, trạng thái đang trả lời, câu trả lời đang hiện dần, lỗi và citations.
- Tạo `POST /chat`. Client chỉ gửi `{ "message": "..." }`.
- Backend lấy user ID từ trusted identity đã có ở backend
  (`request.state.domain_user_id`). Client không được gửi user ID, project ID,
  document ID hoặc thông tin quyền truy cập để backend tin.
- Dùng F002/F003 để tìm chunks của các revision `ready` mà người dùng được
  phép đọc.
- Chỉ đưa câu hỏi và các chunks đã được phép vào prompt gửi LLM.
- Gọi embedding provider và LLM OpenAI-compatible bằng cấu hình server-side.
  Client không thể chọn model, URL hoặc API key.
- Gửi answer, citations và trạng thái kết thúc qua SSE.
- Chat chỉ tồn tại trong bộ nhớ của trang hiện tại. Reload trang là mất lịch
  sử chat.
- Rà soát các acceptance criteria chưa hoàn thành của F001–F003.

### Chưa làm
- Login, đăng ký, session UI hoặc cơ chế tạo identity. Nếu backend không có
  trusted identity thì endpoint trả `401`.
- Lưu, xem lại, chia sẻ hoặc đồng bộ lịch sử chat.
- Skills, tools, web search, compatibility lookup, ticket và mọi side effect.
- Upload UI, OCR, reranking, hybrid search hoặc thay đổi ingestion pipeline.
- Để LLM tự quyết định người dùng được xem tài liệu nào.

## Nguyên tắc bắt buộc
1. Backend kiểm tra identity và quyền trước khi tìm tài liệu.
2. Chunk không được phép không được đi vào prompt, answer, citation hoặc API
   response.
3. Frontend chỉ hiển thị dữ liệu backend trả về; frontend không có quyền tự
   quyết định access control.
4. Model ID, API key và URL provider chỉ nằm trong `.env` phía server.
5. Nếu không tìm được tài liệu phù hợp, LLM vẫn có thể trả lời câu hỏi nhưng
   response không được có citation giả.
6. Feature này không tạo ticket, không gọi tool và không lưu message vào
   database.

## Luồng hoạt động
1. Người dùng nhập câu hỏi và bấm gửi.
2. Frontend gọi `POST /chat` với `message`.
3. Backend kiểm tra trusted identity. Nếu thiếu thì trả `401`.
4. Backend biến câu hỏi thành query embedding, sau đó tìm chunks trong phạm vi
   tài liệu đã được phép.
5. Backend tạo prompt từ câu hỏi và chunks vừa tìm được.
6. Backend gọi LLM, rồi gửi từng phần câu trả lời về frontend qua SSE.
7. Backend gửi citations của các chunks đã dùng, sau đó gửi trạng thái hoàn
   tất.
8. Frontend ghép các phần answer, hiển thị citations hoặc lỗi.

## Kế hoạch cấu trúc backend

```text
Frontend
  -> POST /chat
  -> Chat API
  -> Chat service
       -> Authorized retrieval service -> PostgreSQL/pgvector + audit
       -> LLM adapter
  -> SSE answer + citations
```

- `main.py` sẽ khởi tạo dependency dùng chung một lần: settings, database
  engine, session factory, blob store và model adapters. Điều này tránh việc
  tạo database engine hoặc HTTP client lặp lại cho từng request.
- `Authorized retrieval service` là đường duy nhất để document API và chat API
  tìm chunks. Service này tạo `AuthorizedScope`, gọi repository, tạo citation
  và ghi audit. Nhờ vậy chat không thể quên bước ACL/audit.
- Chat sẽ có `chat_api.py` riêng. Không thêm logic chat vào `document_api.py`,
  vì upload, retrieval và chat là ba luồng khác nhau.
- `QueryEmbedder` chỉ có một contract dùng chung. F004-002 đã có adapter thật
  và fake adapter cho test.
- Có thể tham khảo cách legacy gửi stream ở
  `references/backend/ruvie/routers/openai.py` và chat client ở
  `references/src/lib/apis/chats/`. Active application chỉ học cách tổ chức
  request/stream; không import hoặc chạy code legacy.

## Bố cục file backend dự kiến

Mục tiêu của bố cục này là để một người mới dễ biết mỗi file thuộc phần nào.
Không cần di chuyển tất cả file ngay; chỉ chuyển file khi task hiện tại đang
sửa file đó. Tránh refactor lớn chỉ để đổi đường dẫn.

```text
backend/
├─ ruvie/
│  ├─ main.py                 # Tạo FastAPI app và đăng ký router
│  ├─ config.py               # Đọc và kiểm tra biến môi trường
│  ├─ database.py             # Engine và Session factory
│  ├─ dependencies.py         # Session, identity và adapter cho FastAPI
│  ├─ api/
│  │  ├─ documents.py         # Upload và retrieval endpoint
│  │  └─ chat.py              # Chat endpoint
│  ├─ contracts/
│  │  ├─ documents.py         # Request/response model của document API
│  │  └─ chat.py              # Chat request và SSE event model
│  ├─ domain/
│  │  └─ models.py            # SQLAlchemy models
│  ├─ services/
│  │  ├─ access.py            # ACL và document permission
│  │  ├─ retrieval.py         # Authorized retrieval, citation và audit
│  │  ├─ upload.py            # Tạo revision và ingestion job
│  │  ├─ ingestion.py         # Extract, chunk, embed và index
│  │  ├─ chat.py              # Prompt assembly và chat orchestration
│  │  └─ audit.py             # Ghi audit event
│  └─ adapters/
│     ├─ embedding.py         # Query embedding provider
│     ├─ llm.py               # Streaming LLM provider
│     └─ blob_store.py        # Local và S3 blob storage
├─ migrations/
└─ requirements.txt
```

| File hiện tại | Vị trí sau khi cần chuyển |
|---|---|
| `document_api.py` | `api/documents.py` |
| `chat_contract.py` | `contracts/chat.py` |
| `domain.py` | `domain/models.py` |
| `document_access.py` | `services/access.py` |
| `document_retrieval.py` | `services/retrieval.py` |
| `document_upload.py` | `services/upload.py` và `adapters/blob_store.py` |
| `document_ingestion.py` | `services/ingestion.py` |
| `document_audit.py` | `services/audit.py` |
| `model_adapters.py` | `adapters/embedding.py` và `adapters/llm.py` |

## HTTP và SSE contract

### Request

`POST /chat`

```json
{ "message": "Cách cài plugin X?" }
```

- `message` được trim và không được rỗng.
- Request có field khác `message` trả `422`.
- Identity không nằm trong body.

### Stream trả về

Response dùng `Content-Type: text/event-stream`.

| Event | `data` | Khi nào gửi |
|---|---|---|
| `delta` | `{ "text": "..." }` | Mỗi phần câu trả lời LLM vừa tạo. Có thể gửi nhiều lần. |
| `citations` | `{ "citations": [...] }` | Tối đa một lần, chỉ gồm citation đã authorize. |
| `completed` | `{}` | Sau khi answer và citations đã gửi xong. |
| `error` | `{ "code": "provider_unavailable" \| "generation_failed", "message": "..." }` | Khi provider không cấu hình, không sẵn sàng hoặc tạo answer thất bại. |

Khi thành công, thứ tự là nhiều `delta` -> có thể một `citations` -> một
`completed`. Khi có lỗi trong lúc stream, backend gửi một `error` rồi kết thúc.
Không trả API key, base URL, raw upstream body hay nội dung private trong lỗi.

## Acceptance Criteria
- [x] Người dùng có thể gửi câu hỏi, thấy answer hiện dần, citations, loading
      state và error state trên chat UI.
- [x] `POST /chat` chỉ nhận `message`; thiếu trusted identity trả `401` và
      không có fallback identity lấy từ client.
- [x] Embedding provider và LLM provider đọc từ cấu hình server-side. Client
      không thể thay model, API key, embedding profile, project, document ID
      hay authorized scope.
- [x] Backend luôn làm authorization trước retrieval. Chunk không được phép
      không xuất hiện trong prompt, answer context, citations hoặc response.
- [x] Không có chunk phù hợp vẫn tạo được answer nhưng không có citation.
- [x] SSE tuân theo contract `delta`, `citations`, `completed`, `error`; lỗi
      provider không làm lộ secret hoặc dữ liệu private.
- [x] Citation trên UI giữ document ID, revision ID, chunk ID, offsets, title
      và source hash từ F003.
- [x] Request path F004 không lưu chat/message, không chạy skill/tool và không
      tạo ticket.
- [x] Tests dùng fake embedding/LLM adapter; gồm stream success/error, thiếu
      identity, client-scope injection và Project Alpha/Beta isolation; không
      gọi provider bên ngoài.
- [x] Mỗi acceptance criterion chưa hoàn thành của F001–F003 có evidence rõ
      ràng hoặc task follow-up cụ thể trước khi đánh dấu hoàn thành. Kết quả
      rà soát nằm tại `specs/to-be/f001-f003-acceptance-gaps.md`; các AC gốc
      vẫn chưa tick khi còn thiếu implementation hoặc integration evidence.

## Tasks
- [x] F004-001 Chốt request body, SSE events, error contract và cấu hình LLM
      OpenAI-compatible phía server.
- [x] F004-002 Tạo query embedding adapter dùng embedding profile F003; tạo
      LLM adapter/factory và fake adapters cho tests.
- [x] F004-003 Gom dependency backend dùng chung: tạo engine/session factory
      một lần, quản lý HTTP client, blob store, settings và adapter qua app
      lifecycle. Dùng chung một `QueryEmbedder` contract. Đã tạo và dùng
      `api/`, `contracts/` và `adapters/`; chưa chuyển các service chưa cần sửa.
- [x] F004-004 Tạo authorized retrieval service dùng cho document API và chat:
      tạo `services/`, chuyển phần retrieval/access/audit cần thiết, tạo scope
      server-side, tìm chunks, tạo citations và ghi audit allow/deny an toàn.
- [x] F004-005 Tạo `api/chat.py` và chat service: kiểm tra identity, gọi
      retrieval service, tạo prompt từ chunks đã authorize, gọi LLM và stream
      SSE. Không thêm persistence, skills hoặc tools.
- [x] F004-006 Tạo chat UI/API client: submit message, đọc SSE, ghép answer,
      render citations, loading state và error state.
- [x] F004-007 Viết tests cho dependency lifecycle, provider error, SSE,
      authorization/isolation, citation provenance và client-scope injection.
- [x] F004-008 Rà soát bảy AC chưa đánh dấu hoàn thành ở F001–F003: F001
      migration trên PostgreSQL trống; F002 migration và audit; F003 migration,
      upload/private blob/revision/job, ingestion worker/retry, upload/retrieval
      audit. Xác nhận rõ rằng `DocumentIngestionWorker` hiện chỉ có unit test,
      chưa có production runner; với mỗi AC, ghi evidence, phần còn thiếu và
      follow-up trong `specs/to-be/f001-f003-acceptance-gaps.md`.
- [x] F004-009 Chạy backend suite theo README, kiểm tra migration SQL và cập
      nhật README cho cấu hình LLM/embedding/chat cùng các integration seams.
