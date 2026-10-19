# F011 - Refactor frontend và nâng cấp trải nghiệm tương tác Ruvie Agent

## Goal

Nâng cấp các luồng sử dụng frontend Ruvie Agent theo UX của `references`.
Ưu tiên nhập câu hỏi, đọc câu trả lời, tìm tài liệu và kiểm tra nguồn.
Tách trách nhiệm quản lý trạng thái để phát triển các luồng này an toàn.

- Ngày xác nhận plan: 2026-10-13.
- Trạng thái: hoàn tất và kiểm chứng F011-001 đến F011-009.
- Báo cáo: [f011-frontend-ux-validation.md](../../docs/f011-frontend-ux-validation.md).
- Phạm vi triển khai: frontend Svelte 5/Vite và các API backend đã tồn tại.
- Tiếp nối F010; giữ auth, thương hiệu và nền workspace đã được chọn.
- Xác nhận plan cho phép viết spec. Triển khai code cần yêu cầu riêng.
- Bảo toàn các thay đổi F009/F010 và thay đổi khác đang có trong worktree.

Tham khảo tối đa UX có ích trong `references` theo từng luồng hoàn chỉnh.
Ghi rõ nguồn, hành vi tái sử dụng và cách thích nghi với hợp đồng Ruvie Agent.
Các luồng cần backend mới được ghi thành roadmap riêng trong Scope.

## User Story

- Là người dùng, tôi muốn nhập câu hỏi, dừng và thử lại thuận tiện như trong references.
- Là người đọc tài liệu kỹ thuật, tôi muốn câu trả lời có tiêu đề, danh sách, bảng và code dễ đọc.
- Là người đang đọc phía trên, tôi muốn giữ vị trí đọc khi câu trả lời tiếp tục xuất hiện.
- Là thành viên Project, tôi muốn mở upload từ chat mà không mất câu hỏi đang soạn.
- Là người tra cứu, tôi muốn tìm các đoạn tài liệu được phép đọc và xem nguồn đi kèm.
- Là người kiểm chứng, tôi muốn xem tên tài liệu và phiên bản trước các ID kỹ thuật.
- Là người dùng điện thoại hoặc bàn phím, tôi muốn thao tác được mọi nút, menu và panel.
- Là lập trình viên, tôi muốn state, thao tác và API của một feature có trách nhiệm rõ ràng.

## Scope

### In

#### 1. Yêu cầu, code hiện tại và phương án

| Loại | Nội dung |
|---|---|
| **Spec yêu cầu** | Lấy references làm chuẩn tương tác; port các cụm UX tương thích với Ruvie Agent. |
| **Code hiện tại** | F010 đã tổ chức layout/features/shared/i18n/styles và shell/sidebar/Settings. |
| **Code hiện tại** | WorkspacePage giữ điều hướng, chat, model, Project, upload và polling. |
| **Code hiện tại** | LlmConnectionForm giữ bootstrap/save/disconnect; catalog/model còn phối hợp với Workspace qua callbacks. |
| **Code hiện tại** | ChatConversation render text đã escape, status và citation metadata; có auto-scroll và giữ vị trí đọc. |
| **Code hiện tại** | Composer có textarea, IME guard, plus/model/send; plus chuyển tới Tài liệu. |
| **Code hiện tại** | Chat chỉ tồn tại trong RAM. Mỗi POST /chat gửi một câu hỏi độc lập. |
| **Code hiện tại** | POST /documents/retrieve đã tồn tại; frontend chưa có client và giao diện tìm kiếm. |
| **Code hiện tại** | Citation chat không chứa đoạn trích, số trang hoặc URL preview/download. |
| **Phương án đề xuất** | Giữ cấu trúc theo feature; tách bộ quản lý trạng thái theo phiên đăng nhập. |
| **Phương án đề xuất** | Thêm tương tác composer, renderer, nguồn, upload và tìm kiếm bằng API hiện có. |

F011 thay yêu cầu text thuần của F010 bằng renderer Markdown an toàn.
F011 thay khung Search chờ bằng tìm kiếm đoạn tài liệu có API thật.
Các hợp đồng và yêu cầu F009/F010 khác tiếp tục có hiệu lực nếu spec này không thay rõ.

#### 2. Ranh giới quản lý trạng thái

Bộ quản lý trạng thái là module giữ dữ liệu và thao tác của một feature.
Mỗi phiên workspace có bộ quản lý riêng; không dùng singleton dữ liệu user toàn ứng dụng.

| Thành phần | Trách nhiệm sau refactor |
|---|---|
| App.svelte | Auth/session/CSRF/toast; tạo và hủy workspace theo phiên hiện có. |
| WorkspacePage.svelte | Ghép feature; điều hướng, visibility, drawer, Settings, Controls và focus. |
| Chat | Draft, turns, gửi/dừng/thử lại/Chat mới, request và mã thao tác chat. |
| Documents | Projects, metadata/File upload, status/poll/refresh, query và kết quả tìm kiếm. |
| LLM | Metadata kết nối, catalog, confirmed model, draft cấu hình, bootstrap/save/disconnect và locks. |
| View hội thoại | Vị trí đọc, follow output, nút xuống cuối và trạng thái thu gọn nội dung. |

- File đề xuất: `chat-state.svelte.ts`, `documents-state.svelte.ts`, `llm-state.svelte.ts` trong feature tương ứng.
- Tên file/hàm mới là phương án, không phải code đã tồn tại.
- Khởi tạo một lần cho mỗi workspace; hủy và vô hiệu hóa request khi phiên kết thúc.
- Navigation chỉ đổi view; không tạo lại state do đóng modal, đổi locale hoặc collapse sidebar.
- LLM có một nguồn catalog/model đã xác nhận. Form và selector dùng chung nguồn này.
- Bootstrap LLM chạy một lần khi vào workspace, trước khi mở Settings.
- Save chậm vẫn có bộ quản lý sống khi đóng Settings; không gửi trùng hoặc mất kết quả.
- Giữ khóa chat/model/save hiện có; thao tác cũ không được mở khóa thao tác mới.
- Callback/catch/finally đều xác nhận còn thuộc phiên và thao tác hiện tại.
- Request 401 của phiên cũ không được đăng xuất phiên mới.
- Không tạo request framework, event bus hoặc global store chỉ để giảm số dòng component.

#### 3. Composer, dừng và thử lại

- Giữ textarea. Tự tăng chiều cao tới giới hạn; sau giới hạn cuộn bên trong.
- Nội dung dài/nhiều dòng/paste không làm nút gửi hoặc model biến mất.
- Enter gửi một lần. Shift+Enter xuống dòng. Xác nhận IME không gửi.
- Khi stream đang chạy, nút gửi đổi thành Dừng có nhãn truy cập rõ.
- Dừng abort request phía browser và vô hiệu hóa callback/finally cũ trước khi cho gửi tiếp.
- Giữ partial answer; chuyển lượt sang trạng thái đã dừng. Chưa nhận text thì hiện trạng thái dừng rỗng.
- Không công bố citation chưa được xác nhận bằng event completed.
- Dừng nhận output không được mô tả là đã hủy xử lý ở provider/server; chưa có cancellation API.
- Có thử lại cho lượt lỗi/dừng và trả lời lại cho lượt hoàn tất.
- Thử lại dùng question/model snapshot của lượt, không lấy draft mới.
- Chỉ gửi lại khi model đó còn hợp lệ trong catalog đã xác nhận. Nếu không, yêu cầu chọn model và xác nhận gửi lại.
- Dùng lại hàng của lượt; không thêm bản sao câu hỏi chỉ vì retry.
- Khi xác nhận thử lại, xóa answer/citations/lỗi cũ của lượt và hiện loading.
- Lượt gửi lại vẫn là câu hỏi độc lập theo POST /chat; không dựng context nhiều lượt trong browser.
- Không tự retry khi mạng lỗi. Giữ khóa chống double submit.
- Chat mới chỉ reset chat/draft và abort/invalidate stream; không xóa upload hoặc LLM state.
- Phím tắt dừng, nếu có, chỉ xử lý trong composer khi không có modal/popover/drawer nhận Escape.

#### 4. Renderer và thao tác đọc

- Hỗ trợ paragraph, heading, list, quote, table, inline code, code block và link.
- Render được khi Markdown đang nhận dở qua SSE, không đợi toàn bộ answer mới hiển thị.
- Copy toàn answer lấy chuỗi answer gốc. Copy code chỉ lấy nội dung code.
- Copy thành công có feedback; thất bại có thông báo và giữ nội dung để chọn thủ công.
- Code block có collapse/expand và vùng cuộn ngang riêng. Bảng rộng cuộn bên trong vùng bảng.
- Actions dùng được bằng hover, keyboard và touch; không chỉ xuất hiện khi hover.
- Đầu vào model/tài liệu không tin cậy. Raw HTML và event handler không được thực thi.
- Link Markdown chỉ chấp nhận URL tuyệt đối có protocol http: hoặc https: sau khi parse URL.
- Chặn mọi protocol khác; URL bị chặn hiện thành text không bấm được. Handler HTML không được thực thi.
- Link mở tab mới có rel="noopener noreferrer". Không tự mở link khi nhận delta.
- Không tự tải ảnh, iframe hoặc nội dung nhúng từ output của model.
- Không tự biến ID hoặc chuỗi [1] thành citation link nếu API không cung cấp mapping.
- Chỉ thêm thư viện parse/sanitize/highlight cần cho tập renderer này; reuse active code trước.
- Khi triển khai, kiểm tra dependency tương thích với manifest/lockfile; spec không chốt phiên bản.
- Gộp cập nhật renderer khi stream nhanh; không reparse mỗi token hoặc cập nhật sau unmount.
- Copy/collapse giữ vị trí đọc khi người dùng đang đọc phía trên.

#### 5. Auto-scroll và nút xuống cuối

- Giữ hành vi handleScroll: đang follow output thì cuộn tới cuối.
- Khi người dùng cuộn lên, ngừng tự kéo về cuối; vẫn nhận text mới.
- Hiện nút xuống cuối khi cách cuối đủ xa; bấm nút khôi phục follow output.
- Dùng một ngưỡng nhất quán; ưu tiên ngưỡng 80px active thay vì copy nhiều ngưỡng legacy.
- Đổi view và quay lại giữ vị trí đọc và trạng thái follow output.
- Delta mới và nút xuống cuối không giành focus.
- Tôn trọng reduced motion; viewport thấp và bàn phím mobile vẫn tới được composer.

#### 6. Upload từ chat

- Plus mở bề mặt upload ngay trong chat, giữ câu hỏi đang soạn.
- Reuse DocumentUploadPanel và Documents state; một nguồn form/state cho Chat và Tài liệu.
- Mở từ hai nơi không tạo hai upload request owners hoặc ID form trùng trong DOM.
- Giữ Project/title/software/version/File/status khi đóng bề mặt hoặc đổi view.
- Một lần upload một file PDF hoặc UTF-8 text, tối đa 25 MiB theo hợp đồng hiện có.
- Thẻ file hiện tên/loại/kích thước và pending/running/ready/failed thật.
- Không hiển thị phần trăm tiến độ giả hoặc báo ready khi upload chỉ trả pending.
- Giữ polling 2 giây, tối đa 5 phút; sau deadline có manual refresh.
- Hết deadline không có nghĩa ingestion server đã dừng.
- Hiện lỗi/thử lại phù hợp. Bỏ file chỉ xóa lựa chọn chưa gửi, không giả xóa revision/job server.
- Upload thành công không tự cấp quyền đọc hoặc mở rộng retrieval scope.
- Gọi đây là tải tài liệu lên Project, không khẳng định attachment context riêng cho chat.
- Body /chat vẫn chỉ có message/model ID hợp lệ; không thêm File/document IDs/project scope.

#### 7. Tìm kiếm đoạn tài liệu

- Search ghi rõ đang tìm trong tài liệu được phép đọc.
- POST /documents/retrieve với `{query, limit: 10}` và cookie active.
- Chỉ gửi sau Enter/nút tìm; không gọi embedder theo từng phím gõ.
- Query rỗng hoặc chỉ có khoảng trắng không tạo request.
- Có loading/lỗi/thử lại/rỗng/kết quả và giữ query đã nhập.
- Mỗi kết quả hiện text, title và software/version từ citation API.
- Escape text tài liệu; không chạy HTML. Client kiểm tra response shape trước khi công bố kết quả.
- Mở kết quả để đọc text/metadata đã nhận. Giữ các chunk/revision riêng dù title trùng nhau.
- API tìm trong các chunk READY được phép đọc, không đảm bảo chỉ revision mới nhất.
- Không đổi số chunk trả về thành tổng số tài liệu toàn hệ thống.
- Không tạo score/độ tin cậy/số trang/pagination/total count giả.
- Request cũ không ghi đè query mới; logout không để kết quả rò sang phiên mới.
- Keyboard điều hướng/mở được kết quả; stale success/error/finally không thay trạng thái query mới.
- Không gửi Project/document IDs/ACL từ UI làm ranh giới truy cập.
- Search lịch sử chat vẫn chờ backend, không dùng kết quả tài liệu để giả search chat.
- Search mới không thay thế nguồn đã dùng trong một câu trả lời chat.

#### 8. Nguồn trích dẫn

- Chỉ công bố nguồn chat sau completed hợp lệ.
- Giữ chip tổng số nguồn và thứ tự citation API.
- Tên tài liệu/software/version là thông tin chính.
- Bấm nguồn mở panel/dialog metadata có heading/close/focus return.
- Citation/document/revision/chunk IDs, ordinal/offset/hash nằm trong chi tiết kỹ thuật thu gọn.
- Giữ nguyên citation; không thay revision bằng bản upload mới hoặc lookup không xác định.
- Citation chat hiện tại không hiện đoạn trích/số trang/link tải giả.
- Kết quả Search chỉ hiện text retrieve trả cho chính kết quả đó.
- Không public blob URI, embed URL legacy hoặc file link bỏ qua kiểm tra quyền.
- Mở nguồn không mất vị trí đọc/draft hoặc stream đang chạy của lượt khác.

#### 9. Nhất quán, locale và khả năng truy cập

- Giữ logo, palette navy và auth layout F009/F010.
- Reuse CSS tokens/native primitives trước khi thêm component/dependency.
- Sidebar/account/Settings hoạt động desktop/mobile và giữ state khi collapse.
- Settings chỉ có lựa chọn được hỗ trợ; không đưa advanced provider controls legacy vào chat.
- Lỗi dùng UiMessage/feedback active; không hiện raw server/provider details.
- Lỗi stream hiện gần lượt lỗi; toast dùng cho feedback ngắn như copy.
- Escape đóng bề mặt trên cùng; đóng bề mặt trả focus tới trigger còn nhìn thấy.
- Tab không đi vào nền inert hoặc bề mặt đang đóng; focus luôn nhìn thấy.
- Main targets tối thiểu 44×44px; icon có accessible label; chữ contrast tối thiểu 4.5:1.
- Trạng thái không chỉ truyền đạt bằng màu. Live region không đọc lại toàn answer mỗi delta.
- vi-VN/en-US/ru-RU đủ keys; đổi locale giữ draft/query/File/request và dịch lại lỗi hiện có.
- Giữ locale persistence active; không lưu key/session/chat/tài liệu bằng browser storage mới.
- Upload/nguồn/Settings dùng được ở viewport thấp/mobile/zoom 200%.

#### 10. Nguồn tái sử dụng và thích nghi

Các đường dẫn đã được khảo sát từ source. Không chạy hoặc import runtime references.

| Nguồn | Hành vi/hàm đã xác định | Thích nghi trong F011 |
|---|---|---|
| `frontend/src/App.svelte`; `frontend/src/lib/layout/WorkspacePage.svelte` | Keyed session; newChat/selectView/clearSession/submit/submitUpload/refreshUploadStatus/reloadModels/chooseModel. | Giữ lifecycle/guards; chuyển use cases vào feature owners. |
| `frontend/src/lib/features/llm/LlmConnectionForm.svelte` | reload/run/save/disconnect; bootstrap/invalidation. | Một LLM owner và catalog; đóng Settings không hủy save. |
| `frontend/src/lib/features/chat/ChatComposer.svelte`, `ChatConversation.svelte`, `chat-api.ts` | handleInputKeydown/handleScroll/streamChat và SSE parser. | Giữ IME/cuộn/cookie/safe errors; thêm stopped/retry/renderer. |
| `frontend/src/lib/features/documents/DocumentUploadPanel.svelte`, `documents-api.ts` | Form; listProjects/uploadDocument/getRevisionStatus. | Upload state dùng chung, thêm client retrieve. |
| `backend/ruvie/api/documents.py::retrieve_chunks`; `backend/ruvie/contracts/documents.py::RetrievalBody` | Query/limit → text/citation của readable chunks. | Chỉ thêm frontend consumer, không đổi backend contract/authorization. |
| `references/src/lib/components/chat/MessageInput.svelte` | inOrNearComposition/uploadFileHandler/inputFilesHandler/scrollToBottom/keydown; stop/file cards. | Port tương tác textarea/API active; không kéo rich editor/voice/tools/token storage. |
| `references/src/lib/components/chat/Messages/Markdown.svelte` | parseTokens/updateHandler; cập nhật theo frame khi stream. | Renderer subset và scheduler có cleanup; không artifacts/iframe/tool execution. |
| `references/src/lib/components/chat/Messages/Markdown/MarkdownTokens.svelte`, `MarkdownInlineTokens.svelte` | Table/list/link/code/inline tokens. | Nội dung an toàn; raw HTML vô hiệu hóa; chỉ citation mapping thật. |
| `references/src/lib/components/chat/Messages/CodeBlock.svelte` | copyCode/collapseCodeBlock. | Copy/collapse/scroll; không chạy code/editor/HTML preview. |
| `references/src/lib/components/chat/Messages/ResponseMessage.svelte` | copyToClipboard; regenerateResponse callback; actions. | Copy và gửi lại lượt độc lập; edit/branch/delete persisted thuộc roadmap. |
| `references/src/lib/components/chat/Chat.svelte`, `Messages.svelte` | scrollToBottom/autoScroll. | Một logic cuộn active, giữ ngưỡng nhất quán và vị trí đọc. |
| `references/src/lib/components/layout/SearchModal.svelte` | searchHandler/onKeyDown/results/preview. | Retrieve active, query sau xác nhận; không chat APIs/pagination legacy. |
| `references/src/lib/components/chat/Messages/Citations.svelte`; `Citations/CitationModal.svelte` | showSourceModal/chip/list/details; getTextFragmentUrl. | Chip/panel metadata; không content URL, score→confidence hoặc text fragment chưa có dữ liệu. |
| `references/src/lib/components/layout/Sidebar.svelte`, `Sidebar/UserMenu.svelte` | New Chat/itemClickHandler/mobile/account menu. | Shell active; history/folder requests chờ backend. Resize chưa thuộc F011. |
| `references/src/lib/components/chat/SettingsModal.svelte`; `references/src/lib/components/common/Modal.svelte` | Tabs/save feedback; handleKeyDown/isTopModal/focus trap/restore. | Native dialog/popover active, một thứ tự Escape và cookie/CSRF active. |

Không cần kiểm tra LICENSE riêng cho source được cung cấp trong references theo AGENTS.md hiện hành.
Báo cáo triển khai ghi nguồn thực sự port và phần thay đổi; không gọi khảo sát là đã port.

#### 11. Hợp đồng API và dữ liệu

| Luồng | Input/Output được giữ |
|---|---|
| Session/auth | API active; HttpOnly cookie/CSRF; workspace theo user/phiên. |
| Chat | POST /chat: `{message, model_id?}` → SSE delta/citations/completed hoặc safe errors. |
| Models/connection | GET /models; GET/PUT/DELETE /llm/connection; PATCH /llm/connection/model. |
| Projects | GET /projects → authorized ProjectSummary; lựa chọn phục vụ upload. |
| Upload | POST /documents/upload → document/revision/job IDs và pending; FormData và CSRF active. |
| Status | GET /documents/revisions/{revision_id}/status → pending/running/ready/failed, không phần trăm. |
| Search | POST /documents/retrieve: `{query, limit: 10}` → array `{chunk_id, document_id, text, citation}`. |
| Citation | Giữ citation/document/revision/chunk IDs, ordinal, offsets, title, source_hash, software/version; SSE chưa có text/page/blob URL. |

- Backend là nguồn identity/authorization/provider configuration; không thêm endpoint/key/ACL/scope vào chat/retrieval.
- Key omission/empty/new key, đổi URL, disconnect/server fallback giữ semantics active.
- Saved key không quay về browser; draft key chỉ trong RAM và xóa khi phiên kết thúc.
- Failed saves giữ confirmed settings/model; không tự chuyển provider/model.

#### 12. Roadmap và dependency backend riêng

Đây là kế hoạch tiếp nối, không phải task triển khai F011.
Các feature sau cần phân tích và xác nhận hợp đồng trước khi code.

| UX cần đạt tiếp | Backend cần có | Điều kiện trước khi UI hoạt động |
|---|---|---|
| Lưu/mở lại/đổi tên/search chat; pin/archive/delete/folders. | PostgreSQL conversations/messages; account APIs, pagination/ownership. | Không gọi RAM/localStorage là saved history; account isolation. |
| Hội thoại nhiều lượt, edit/branch/regenerate theo conversation. | Service dựng context từ conversation đã xác thực; message/conversation/generation contracts. | Kiểm tra quyền tài liệu lại trước retrieval/context/serialization; không tin client history là dữ liệu có quyền. |
| Library/chọn tài liệu đã có; chat với tài liệu được chọn. | Authorized listing và lựa chọn thu hẹp trong readable set server-side. | Project/document IDs là lựa chọn, không phải ACL boundary. |
| Xem đoạn nguồn của answer, PDF preview/download. | Authorized API theo immutable revision/chunk, private storage và page data nếu được thu thập. | Không reretrieve thay citation gốc hoặc public link bỏ qua quyền. |
| Notes/Workspace library/advanced Controls. | CRUD/quyền/settings/tool contracts tương ứng. | Không fake save/role/parameter/endpoint. |

Thứ tự đề xuất: lịch sử và hội thoại → nguồn/tài liệu → thư viện và chức năng mở rộng.
Chọn số feature và schema khi lập spec tiếp theo.

### Out

- Thay nguyên frontend bằng legacy; chạy/deploy/sửa references hoặc import runtime legacy.
- Chuyển SvelteKit/Tailwind, thay toàn bộ package hoặc thêm rich editor chỉ để giống references.
- Backend production changes/migrations hoặc đổi auth/provider/authorization contracts trong F011.
- Persistent history, context nhiều lượt, edit/branch/delete tin nhắn trên server.
- Exact citation preview/download/PDF page navigation hoặc public blob URL.
- Document-scoped chat hoặc client-selected Project/ACL làm quyền truy cập.
- Voice/TTS, chạy code/terminal, artifact/iframe, dynamic charts, image generation hoặc tool integration mới.
- Resize sidebar, theme/logo/auth layout mới hoặc design-system rewrite toàn ứng dụng.
- Search chat/Notes/Workspace CRUD/folders persistence/advanced Controls chưa có API.

## Flow

### 1. Vào workspace và đổi view

1. App khôi phục session; tạo workspace và feature owners cho phiên đó.
2. LLM bootstrap một lần; Documents tải Projects theo cơ chế active.
3. Workspace render view; đổi view giữ feature state và request.
4. Logout/current 401 vô hiệu hóa owners, abort stream và xóa dữ liệu phiên.

### 2. Gửi, dừng và thử lại

1. Nhập draft; composer auto-grow và bảo vệ IME.
2. Chat kiểm tra message/model/locks, chụp question/model và gửi POST /chat.
3. Delta cập nhật answer/renderer; vị trí đọc quyết định follow output.
4. Dừng abort/invalidate phía browser; giữ partial text, bỏ nguồn chưa xác nhận, hiện đã dừng.
5. Completed công bố nguồn; lỗi giữ partial text và hiện retry.
6. Người dùng xác nhận thử lại; kiểm tra model rồi gửi lại trên cùng lượt.
7. Chat mới reset chat; callback/finally cũ không ghi vào hoặc unlock request mới.

### 3. Upload trong chat

1. Plus mở upload dùng chung state với Tài liệu.
2. Chọn Project API trả, metadata và một file.
3. Upload trả pending; thẻ file hiện status/polling theo deadline active.
4. Đóng bề mặt/đổi view giữ draft/File/kết quả xử lý.
5. Ready/failed/deadline hiện kết quả và hành động đúng; không tự gửi chat với file scope.

### 4. Search và nguồn

1. Mở Search, nhập query và xác nhận tìm.
2. Client gửi query/limit; backend dùng trusted identity/readable predicate.
3. Hiện text/citation của kết quả hiện tại; response cũ không ghi đè query mới.
4. Mở kết quả để đọc text/metadata đã nhận.
5. Trong chat, mở nguồn completed để xem metadata citation gốc.
6. Không lấy Search mới để điền đoạn nguồn chưa được API chat cung cấp.

## Edge Cases

- IME/paste/double click: không gửi nhầm hoặc trùng request.
- Stop trước delta/đồng thời completed hoặc gửi tiếp ngay: chỉ thao tác hiện tại được sửa state.
- Retry model biến mất: yêu cầu chọn lại, không tự đổi model.
- Stream ngắt/protocol/provider error: giữ partial answer, bỏ nguồn chưa completed.
- Markdown fence/table/link nhận dở: vẫn đọc được, không thực thi HTML/URL nguy hiểm.
- Clipboard bị từ chối: feedback lỗi, không mất nội dung hoặc fake copied.
- Cuộn lên/collapse/đổi view khi stream nhanh: giữ vị trí và không giành focus.
- Bootstrap/save chậm và modal reopen: một owner/catalog, không double fetch/save.
- Ingestion vượt deadline: refresh, không báo server đã dừng.
- Không có Project/readable documents: trạng thái rỗng; không cấp quyền ngầm.
- Có quyền upload nhưng không có quyền đọc: không suy quyền đọc từ upload thành công.
- Search rỗng/lỗi/query mới trước query cũ: giữ query và nhận đúng response hiện tại.
- Account nối tiếp/stale 401/success/error/finally: không rò dữ liệu hoặc tác động phiên mới.
- Title/query/filename chứa HTML hoặc rất dài: escape/wrap/truncate với tên truy cập đầy đủ.
- Nhiều bề mặt/Escape/resize: đóng đúng thứ tự, focus không vào hidden/inert.
- Chữ Nga dài/viewport thấp/zoom: tới được actions/composer/close, không root horizontal overflow.

## Acceptance Criteria

- [x] **AC-01:** Giữ cấu trúc feature F010; Workspace không trực tiếp điều phối stream/upload polling/LLM use cases.
- [x] **AC-02:** Owners tạo một lần theo phiên, invalidate khi unmount; không singleton dữ liệu user.
- [x] **AC-03:** Đổi view/collapse/locale/đóng Settings giữ draft/File/query/catalog và requests.
- [x] **AC-04:** LLM bootstrap trước mở Settings; reopen không fetch/reset; save qua modal close có một owner.
- [x] **AC-05:** Key/model/save/disconnect/fallback giữ semantics; failed save giữ confirmed settings/model.
- [x] **AC-06:** Enter gửi một lần, Shift+Enter xuống dòng, IME không gửi; composer auto-grow có giới hạn.
- [x] **AC-07:** Stop giữ partial text hoặc trạng thái dừng rỗng; callback cũ không đổi lượt mới; không nguồn chưa completed.
- [x] **AC-08:** Retry dùng question/model snapshot, có guard/model validation; không auto retry hoặc duplicate question.
- [x] **AC-09:** Chat mới chỉ reset chat; old callback/catch/finally không ghi vào hoặc unlock request mới.
- [x] **AC-10:** Markdown heading/list/quote/table/link/inline code/code block render khi stream và completed.
- [x] **AC-11:** HTML/handler/URL nguy hiểm không thực thi; output không tự tải ảnh/iframe hoặc tạo citation mapping giả.
- [x] **AC-12:** Copy answer/code đúng nội dung và feedback; code collapse/expand không mất answer.
- [x] **AC-13:** Code/table rộng cuộn cục bộ; answer dài không gây root horizontal overflow.
- [x] **AC-14:** Đọc phía trên không bị kéo xuống; nút xuống cuối khôi phục follow; đổi view giữ reading position.
- [x] **AC-15:** Plus mở upload trong chat; một form/state, không duplicate owner hoặc DOM ID.
- [x] **AC-16:** Upload giữ Project/PDF/UTF-8/25 MiB/CSRF contract; status thật, không phần trăm giả.
- [x] **AC-17:** Poll 2 giây/5 phút/manual refresh đúng qua close/navigation; stale request không sửa upload mới.
- [x] **AC-18:** UI không gọi upload là attachment context; /chat vẫn chỉ có message/model ID hợp lệ.
- [x] **AC-19:** Search gửi query/limit 10 sau xác nhận; query rỗng không gọi API, không request từng phím gõ.
- [x] **AC-20:** Search có loading/rỗng/lỗi/retry/results; payload text/citation được validate/escape; không total/score/page/pagination giả.
- [x] **AC-21:** Query cũ không ghi đè query mới; keyboard mở kết quả; logout xóa và stale request không khôi phục results.
- [x] **AC-22:** Retrieval không nhận client ACL/Project/document scope; integration fixture xác nhận quyền backend và body query/limit.
- [x] **AC-23:** Nguồn chat chỉ sau completed; ưu tiên title/software/version, technical IDs/hash/offset thu gọn.
- [x] **AC-24:** Source panel có close/focus return; giữ revision/chunk/reading position/draft; không preview/download/excerpt giả.
- [x] **AC-25:** Search text không thay nguồn chat; không blob URI hoặc legacy content URL mới.
- [x] **AC-26:** Auth/logo/theme F009/F010 giữ nguyên; sidebar/account/Settings/Controls và chức năng chờ có trạng thái trung thực.
- [x] **AC-27:** Current 401/logout xóa account state; stale 401/success/error/finally không tác động account mới.
- [x] **AC-28:** Không browser persistence key/model/session mới; raw server/provider details không xuất hiện trong feedback.
- [x] **AC-29:** Escape đóng bề mặt trên cùng; Tab/focus-visible/focus return/inert đúng.
- [x] **AC-30:** Main targets ≥44×44px, chữ contrast ≥4.5:1; keyboard/touch và reduced motion hoạt động.
- [x] **AC-31:** Ba locale đủ keys; đổi locale giữ state/request và dịch lại UiMessage; không đọc toàn answer mỗi delta.
- [x] **AC-32:** Viewports F010/zoom 200% tới được composer/actions/close; nội dung dài không root horizontal overflow.
- [x] **AC-33:** Không legacy runtime import/framework migration/global user singleton/backend migration mới trong F011.
- [x] **AC-34:** Tests/build/browser regression theo README có kết quả thật và QA screenshots; ma trận UX reuse ghi rõ bằng chứng.
- [x] **AC-35:** History/multiturn/library/exact preview/advanced Controls có dependency backend riêng; không fake API/saved data.

## Tasks

Các task dưới đây đã triển khai và kiểm chứng. Bằng chứng nằm trong báo cáo F011.

### F011-001 — Tách quản lý trạng thái theo feature

- [x] **F011-001**

**Work**
1. Đối chiếu callers/guards của Workspace/App/LlmConnectionForm; ghi baseline trước refactor.
2. Tách Chat/Documents/LLM owners theo keyed workspace; chuyển stream/poll/upload/model/connection operations.
3. Giữ view/focus ở Workspace và vị trí đọc ở view chat.
4. Gom catalog/model/bootstrap vào một LLM owner; form/selector dùng chung state.
5. Kiểm tra navigation/modal/logout/stale responses/locks/key cleanup trước UX mới.

**Where**: WorkspacePage.svelte và feature callers; LlmConnectionForm.svelte; đề xuất mới `features/chat/chat-state.svelte.ts`, `features/documents/documents-state.svelte.ts`, `features/llm/llm-state.svelte.ts` dưới frontend/src/lib. App.svelte chỉ đổi wiring nếu cần.

**Done**: AC-01 đến AC-05, AC-27/28/33; state/request ownership regression pass.

### F011-002 — Composer, dừng và thử lại

- [x] **F011-002**

**Work**
1. Reuse handleInputKeydown và MessageInput UX cho auto-grow/stop.
2. Thêm stopped và question/model snapshot; giữ SSE contract.
3. Thêm Stop/retry/resubmit cùng guards abort/late event/finally/double submit.
4. Xác định replace cùng lượt và model-unavailable feedback.
5. Kiểm tra IME/paste/Enter, Stop trước delta/đồng thời completed, retry và New Chat.

**Where**: frontend/src/lib/features/chat/ChatComposer.svelte, ChatPage.svelte, chat-turn.ts và chat owner; chat-api.ts chỉ đổi cancellation/cleanup cần thiết, giữ payload/events.

**Done**: AC-06 đến AC-09, AC-18; stopped/retry đúng và stream cũ không ảnh hưởng request mới.

### F011-003 — Markdown và actions

- [x] **F011-003**

**Work**
1. Đối chiếu Markdown/MarkdownTokens/CodeBlock/ResponseMessage legacy và dependencies active.
2. Chọn renderer subset/thư viện cần thiết; policy HTML/link rõ.
3. Render partial Markdown, gộp cập nhật và cleanup scheduler.
4. Thêm copy/feedback/collapse và overflow cục bộ.
5. Kiểm tra stream split tokens, bảng/code dài, clipboard failure và HTML/unsafe URLs.

**Where**: features/chat/ChatConversation.svelte; đề xuất AnswerContent.svelte, CodeBlock.svelte, MessageActions.svelte trong chat; manifest/lockfile chỉ thêm dependency cần thiết; i18n/CSS liên quan.

**Done**: AC-10 đến AC-13, AC-28; copy đúng và output không kích hoạt HTML/embeds.

### F011-004 — Vị trí đọc và nút xuống cuối

- [x] **F011-004**

**Work**
1. Reuse handleScroll/readingPosition và đối chiếu autoScroll legacy.
2. Thêm nút xuống cuối và ngưỡng nhất quán.
3. Tích hợp renderer/collapse không giành focus hoặc kéo khỏi vị trí đọc.
4. Kiểm tra streaming dài, đổi view, viewport thấp và reduced motion.

**Where**: features/chat/ChatConversation.svelte, view/render callbacks và scoped styles.

**Done**: AC-14 và phần scroll/layout của AC-30/32; giữ position, bấm xuống cuối khôi phục follow.

### F011-005 — Upload ngay trong chat

- [x] **F011-005**

**Work**
1. Plus mở upload dùng chung form/state với Tài liệu.
2. Reuse upload panel/file-card UX; tránh ID/owners trùng.
3. Hiện metadata/status/lỗi/retry/refresh thật; giữ polling/deadline/CSRF/Project contract.
4. Kiểm tra PDF/text/oversize/double submit/pending/ready/failed/deadline/logout/stale polling.

**Where**: features/chat/ChatPage.svelte/ChatComposer.svelte; features/documents/DocumentUploadPanel.svelte/DocumentsPage.svelte/Documents owner; workspace wiring; đề xuất upload dialog dùng native primitive active.

**Done**: AC-15 đến AC-18; mở từ chat, giữ draft và không thêm document scope vào chat request.

### F011-006 — Search đoạn tài liệu có quyền

- [x] **F011-006**

**Work**
1. Thêm type/client retrieve và response validation theo backend hiện có; query/limit cố định/safe errors.
2. Thay Search placeholder bằng UX đoạn tài liệu, tham khảo SearchModal.
3. Thêm confirm/loading/rỗng/lỗi/retry/keyboard results và text/metadata details.
4. Invalidate response theo query/phiên; không đổi backend hoặc nhận client scope.
5. Kiểm tra body/cookie/query rỗng/out-of-order/401/escaping/authorized results bằng fixture phù hợp.

**Where**: features/documents/documents-api.ts và Documents owner; đề xuất DocumentSearchPage.svelte/result components trong documents; Workspace view wiring; i18n/tests.

**Done**: AC-19 đến AC-22, AC-25; chunks/citations thật, không history search/score/pagination giả.

### F011-007 — Nguồn dễ đọc và metadata panel

- [x] **F011-007**

**Work**
1. Reuse CitationSources/citation type và Citations/CitationModal UX.
2. Giữ chip/count/order; ưu tiên title/software/version, technical details thu gọn.
3. Thêm panel/close/focus return; Search chỉ dùng text của chính kết quả đó.
4. Kiểm tra completed gate/partial/error/stopped/revision IDs/title dài/HTML.
5. Không gọi preview/content URL hoặc retrieve mới để thay nguồn chat.

**Where**: features/chat/CitationSources.svelte; đề xuất SourcesPanel.svelte trong chat hoặc metadata component dùng chung nếu Search có caller thực; wiring/i18n.

**Done**: AC-23 đến AC-25; nguồn dễ quét, metadata nguyên vẹn, không fake preview/download.

### F011-008 — Nhất quán, locale và responsive

- [x] **F011-008**

**Work**
1. Hoàn thiện sidebar/account/Settings/upload/source/search surfaces theo UX references/token active.
2. Thống nhất feedback/labels/tooltip/loading/error; một toast host.
3. Kiểm tra Escape/focus trap/return/inert/keyboard/touch.
4. Thêm ba locale, giữ state/request/live-region behavior.
5. Kiểm tra contrast/targets/overflow/reduced motion/viewports F010/zoom.

**Where**: layout/chat/documents/llm/shared components liên quan; styles/base.css/workspace.css khi cần; lib/i18n/locales/{vi-VN,en-US,ru-RU}/translation.json; browser/a11y checks.

**Done**: AC-26 đến AC-32; surfaces mới dùng được bằng keyboard/mobile; giữ auth/theme đã chọn.

### F011-009 — Kiểm chứng, ma trận UX và tài liệu

- [x] **F011-009**

**Work**
1. Tổng hợp checks của từng task; giữ assertions lifecycle/auth/key/upload/SSE có ý nghĩa.
2. Chạy frontend tests/build/browser theo README, fake APIs/disposable fixtures, không provider thật.
3. Check 1920×1080, 1366×768, 1280×605, 1024×600, 768×1024, 375×812, 320×568, 640×360 CSS px ở scale 2.
4. Check keyboard/locale dài/reduced motion; chụp stream/Markdown/Stop/retry/Search/upload/sources/Settings/mobile.
5. Ghi ma trận references: đã port/đã thích nghi/chờ dependency, lý do và bằng chứng.
6. README ghi cấu trúc/state và lệnh browser mới nếu có; chỉ đặt lệnh run/test ở README.
7. Báo cáo pass/fail/skip thật, dependencies và roadmap; chỉ tick task/AC đã implement và kiểm chứng.
8. Nếu cần backend changes, cập nhật và xác nhận phạm vi rồi chạy backend suite theo repository rules.

**Where**: frontend/tests hiện có và đề xuất frontend-ux-browser.mjs; README.md; đề xuất docs/f011-frontend-ux-validation.md; screenshots logs/f011/ không commit output test.

**Done**: AC-33 đến AC-35 và bằng chứng AC-01 đến AC-32; không giảm checks để che lỗi, tasks unfinished vẫn unchecked.
