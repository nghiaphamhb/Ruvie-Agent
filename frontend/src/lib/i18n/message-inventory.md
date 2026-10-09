# F008 — Inventory chuỗi giao diện

Registry: vi-VN, en-US, ru-RU. Catalog chỉ chứa UI text; dữ liệu ngoài không dùng làm key.

| Khóa | Nội dung hiện tại / dự kiến | Callsite baseline | Nguồn bản dịch |
| --- | --- | --- | --- |
| `language.label` | Ngôn ngữ | Chuỗi mới hoặc tham số hóa; đối chiếu component dùng khóa | vi-VN: legacy translation.json, key `Language`; ru-RU: legacy translation.json, key `Language` |
| `nav.chat` | Chat | frontend/src/App.svelte:21<br>frontend/src/App.svelte:360<br>frontend/src/lib/components/AppNavigation.svelte:12 | ru-RU: legacy translation.json, key `Chat` |
| `nav.documents` | Tải tài liệu | frontend/src/App.svelte:21<br>frontend/src/lib/components/AppNavigation.svelte:13 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `nav.llm` | Kết nối LLM | frontend/src/App.svelte:21<br>frontend/src/App.svelte:362<br>frontend/src/lib/components/AppNavigation.svelte:14<br>frontend/src/lib/components/LlmConnectionForm.svelte:98 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `nav.main` | Điều hướng chính | frontend/src/lib/components/AppNavigation.svelte:20 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `auth.login` | Đăng nhập | frontend/src/lib/components/LoginForm.svelte:22<br>frontend/src/lib/components/LoginForm.svelte:30 | vi-VN: legacy translation.json, key `Sign in`; ru-RU: legacy translation.json, key `Sign in` |
| `auth.logout` | Đăng xuất | frontend/src/lib/components/AppNavigation.svelte:28 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `auth.email` | Email | frontend/src/lib/components/LoginForm.svelte:26 | vi-VN: legacy translation.json, key `Email`; ru-RU: legacy translation.json, key `Email` |
| `auth.password` | Mật khẩu | frontend/src/lib/components/LoginForm.svelte:28 | vi-VN: legacy translation.json, key `Password`; ru-RU: legacy translation.json, key `Password` |
| `auth.description` | Sử dụng tài khoản được cấp để truy cập tài liệu trong project của bạn. | frontend/src/lib/components/LoginForm.svelte:23 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `auth.signingIn` | Đang đăng nhập… | frontend/src/lib/components/LoginForm.svelte:30 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `auth.checking` | Đang kiểm tra phiên đăng nhập… | frontend/src/App.svelte:331 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `auth.errors.credentials` | Email hoặc mật khẩu không đúng. | frontend/src/lib/auth-api.ts:18 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `auth.errors.request` | Không thể xử lý yêu cầu. | frontend/src/lib/auth-api.ts:18 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `auth.errors.logout` | Không thể đăng xuất. Hãy thử lại. | frontend/src/lib/auth-api.ts:35 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `auth.errors.login` | Không thể đăng nhập. | frontend/src/App.svelte:86 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `auth.errors.session` | Không thể kiểm tra phiên đăng nhập. | frontend/src/App.svelte:68 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `common.errors.network` | Không thể kết nối máy chủ. Hãy thử lại. | frontend/src/lib/auth-api.ts:13<br>frontend/src/lib/llm-api.ts:24 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `common.errors.session` | Phiên đăng nhập đã hết hạn. | frontend/src/lib/documents-api.ts:25<br>frontend/src/lib/llm-api.ts:18 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `common.reload` | Tải lại | frontend/src/lib/components/LlmConnectionForm.svelte:116<br>frontend/src/lib/components/ModelSelector.svelte:82 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `common.retry` | Thử lại | frontend/src/lib/components/DocumentUploadPanel.svelte:30 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `page.title` | Ruvie Agent — Tra cứu tài liệu | frontend/src/App.svelte:321 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `page.description` | Đặt câu hỏi và nhận câu trả lời kèm nguồn tài liệu bạn được phép đọc. | frontend/src/App.svelte:322 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `llm.url` | Base URL | frontend/src/lib/components/LlmConnectionForm.svelte:102 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `llm.key` | API key (tùy chọn) | frontend/src/lib/components/LlmConnectionForm.svelte:106 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `llm.keyClearHelp` | Key sẽ được xóa khi bấm Kết nối. | frontend/src/lib/components/LlmConnectionForm.svelte:111 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `llm.keyKeepHelp` | Đã lưu key. Để trống để giữ key hiện tại. | frontend/src/lib/components/LlmConnectionForm.svelte:111 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `llm.keyHelp` | Chỉ nhập key khi dịch vụ yêu cầu. | frontend/src/lib/components/LlmConnectionForm.svelte:111 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `llm.connect` | Kết nối | frontend/src/lib/components/LlmConnectionForm.svelte:113 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `llm.disconnect` | Gỡ kết nối | frontend/src/lib/components/LlmConnectionForm.svelte:114 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `llm.clearKey` | Xóa key đã lưu | frontend/src/lib/components/LlmConnectionForm.svelte:115 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `llm.processing` | Đang xử lý… | frontend/src/lib/components/LlmConnectionForm.svelte:113 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `llm.checking` | Đang kiểm tra kết nối… | frontend/src/lib/components/LlmConnectionForm.svelte:120 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `llm.saved` | Đã lưu kết nối. | frontend/src/lib/components/LlmConnectionForm.svelte:78 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `llm.removed` | Đã gỡ kết nối riêng. | frontend/src/lib/components/LlmConnectionForm.svelte:87 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `llm.source.personal` | Đang dùng kết nối riêng. | frontend/src/lib/components/LlmConnectionForm.svelte:120 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `llm.source.server` | Đang dùng kết nối máy chủ. | frontend/src/lib/components/LlmConnectionForm.svelte:120 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `llm.source.none` | Chưa có kết nối LLM. | frontend/src/lib/components/LlmConnectionForm.svelte:120 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `llm.errors.read` | Không thể đọc kết nối. Hãy thử lại. | frontend/src/lib/components/LlmConnectionForm.svelte:55 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `llm.errors.csrf` | Không thể xác nhận yêu cầu. Hãy tải lại trang. | frontend/src/lib/llm-api.ts:19 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `llm.errors.invalid` | URL hoặc model không hợp lệ. Hãy kiểm tra kết nối. | frontend/src/lib/llm-api.ts:20 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `llm.errors.providerUnavailable` | Không lấy được model. Hãy kiểm tra URL, key và thử lại. | frontend/src/lib/llm-api.ts:21 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `llm.errors.settings` | Chưa có kết nối LLM hoặc không thể lưu cấu hình. | frontend/src/lib/llm-api.ts:22 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `model.choose` | Chọn model | frontend/src/lib/components/ModelSelector.svelte:80<br>frontend/src/lib/components/ModelSelector.svelte:81 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `model.prefix` | Model: {{name}} | Chuỗi mới hoặc tham số hóa; đối chiếu component dùng khóa | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `model.reload` | Tải lại model | frontend/src/lib/components/ModelSelector.svelte:82 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `model.checking` | Đang kiểm tra model… | frontend/src/lib/components/ModelSelector.svelte:84 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `model.missing` | Model đã lưu không còn khả dụng. Hãy chọn lại model. | frontend/src/lib/components/ModelSelector.svelte:85 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `model.connectFirst` | Kết nối LLM để lấy danh sách model. | frontend/src/lib/components/ModelSelector.svelte:86 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `model.search` | Tìm model | frontend/src/lib/components/ModelSelector.svelte:94<br>frontend/src/lib/components/ModelSelector.svelte:96 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `model.list` | Danh sách model | frontend/src/lib/components/ModelSelector.svelte:100 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `model.noMatch` | Không có model phù hợp. | frontend/src/lib/components/ModelSelector.svelte:110 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `model.errors.load` | Không thể tải model. Hãy thử lại. | frontend/src/App.svelte:238 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `model.errors.save` | Không thể lưu model. Hãy thử lại. | frontend/src/App.svelte:259 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `chat.welcome` | Bạn muốn tìm hiểu điều gì? | frontend/src/lib/components/ChatConversation.svelte:37 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `chat.description` | Đặt câu hỏi về tài liệu bạn được phép đọc. Câu trả lời sẽ xuất hiện dần cùng danh sách nguồn tham khảo. | frontend/src/lib/components/ChatConversation.svelte:38 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `chat.conversation` | Hội thoại | frontend/src/lib/components/ChatConversation.svelte:41 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `chat.loading` | Đang tìm câu trả lời… | frontend/src/lib/components/ChatConversation.svelte:55 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `chat.streaming` | Đang trả lời… | frontend/src/lib/components/ChatConversation.svelte:57 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `chat.question` | Câu hỏi của bạn | frontend/src/lib/components/ChatComposer.svelte:17 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `chat.placeholder` | Hỏi về tài liệu của bạn… | frontend/src/lib/components/ChatComposer.svelte:22 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `chat.send` | Gửi câu hỏi | frontend/src/lib/components/ChatComposer.svelte:27 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `chat.hint` | Enter để gửi · Shift+Enter để xuống dòng · Mỗi câu hỏi được xử lý độc lập. Lịch sử chỉ giữ trong trang này. | frontend/src/lib/components/ChatComposer.svelte:32 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `chat.errors.auth_required` | Cần đăng nhập để đặt câu hỏi. | frontend/src/lib/chat-api.ts:31 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `chat.errors.invalid_request` | Câu hỏi không hợp lệ. Vui lòng thử lại. | frontend/src/lib/chat-api.ts:32 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `chat.errors.model_unavailable` | Model đã chọn không còn khả dụng. Hãy chọn lại model. | frontend/src/lib/chat-api.ts:33 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `chat.errors.provider_unavailable` | Dịch vụ trả lời hiện không khả dụng. Vui lòng thử lại sau. | frontend/src/lib/chat-api.ts:34 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `chat.errors.generation_failed` | Không thể tạo câu trả lời. Vui lòng thử lại. | frontend/src/lib/chat-api.ts:35 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `chat.errors.network_error` | Không thể kết nối đến máy chủ. Vui lòng thử lại. | frontend/src/lib/chat-api.ts:36 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `chat.errors.interrupted` | Câu trả lời bị gián đoạn. Vui lòng thử lại. | frontend/src/lib/chat-api.ts:37 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `chat.errors.protocol_error` | Không đọc được câu trả lời từ máy chủ. | frontend/src/lib/chat-api.ts:38 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `chat.errors.complete` | Không thể hoàn tất câu trả lời. | frontend/src/App.svelte:306 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `upload.eyebrow` | TÀI LIỆU PROJECT | frontend/src/lib/components/DocumentUploadPanel.svelte:27 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `upload.heading` | Tải tài liệu lên | frontend/src/lib/components/DocumentUploadPanel.svelte:27 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `upload.support` | Hỗ trợ PDF và văn bản UTF-8, tối đa 25 MiB. | frontend/src/lib/components/DocumentUploadPanel.svelte:28 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `upload.empty` | Bạn chưa tham gia project nào. | frontend/src/lib/components/DocumentUploadPanel.svelte:32 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `upload.project` | Project | frontend/src/lib/components/DocumentUploadPanel.svelte:35<br>frontend/src/lib/components/DocumentUploadPanel.svelte:36 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `upload.loadingProjects` | Đang tải project… | frontend/src/lib/components/DocumentUploadPanel.svelte:37 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `upload.chooseProject` | Chọn project | frontend/src/lib/components/DocumentUploadPanel.svelte:37 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `upload.title` | Tên tài liệu | frontend/src/lib/components/DocumentUploadPanel.svelte:41 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `upload.software` | Phần mềm | frontend/src/lib/components/CitationSources.svelte:21<br>frontend/src/lib/components/DocumentUploadPanel.svelte:42 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `upload.version` | Phiên bản | frontend/src/lib/components/DocumentUploadPanel.svelte:43 | vi-VN: legacy translation.json, key `Version`; ru-RU: legacy translation.json, key `Version` |
| `upload.file` | File | frontend/src/lib/components/DocumentUploadPanel.svelte:44<br>frontend/src/lib/components/DocumentUploadPanel.svelte:54 | ru-RU: legacy translation.json, key `File` |
| `upload.submit` | Tải lên | frontend/src/lib/components/DocumentUploadPanel.svelte:57 | vi-VN: legacy translation.json, key `Upload`; ru-RU: legacy translation.json, key `Upload` |
| `upload.uploading` | Đang tải lên… | frontend/src/lib/components/DocumentUploadPanel.svelte:57 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `upload.status.pending` | Đang chờ xử lý | frontend/src/lib/components/DocumentUploadPanel.svelte:16 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `upload.status.running` | Đang xử lý | frontend/src/lib/components/DocumentUploadPanel.svelte:16 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `upload.status.ready` | Sẵn sàng | frontend/src/lib/components/DocumentUploadPanel.svelte:16 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `upload.status.failed` | Xử lý thất bại | frontend/src/lib/components/DocumentUploadPanel.svelte:16 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `upload.errorCode` | Mã lỗi: {{code}} | Chuỗi mới hoặc tham số hóa; đối chiếu component dùng khóa | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `upload.continuing` | Việc xử lý vẫn tiếp tục ở máy chủ. | frontend/src/lib/components/DocumentUploadPanel.svelte:64 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `upload.refresh` | Làm mới trạng thái | frontend/src/lib/components/DocumentUploadPanel.svelte:64 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `upload.refreshing` | Đang làm mới… | frontend/src/lib/components/DocumentUploadPanel.svelte:64 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `upload.errors.projects` | Không thể tải danh sách project. Hãy thử tải lại trang. | frontend/src/App.svelte:149 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `upload.errors.notFound` | Không tìm thấy project hoặc tài liệu được phép truy cập. | frontend/src/App.svelte:189<br>frontend/src/App.svelte:212 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `upload.errors.upload` | Không thể tải lên hoặc kiểm tra trạng thái tài liệu. | frontend/src/App.svelte:190 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `upload.errors.refresh` | Không thể làm mới trạng thái tài liệu. | frontend/src/App.svelte:213 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `upload.errors.request` | Không thể hoàn tất yêu cầu tài liệu. | frontend/src/lib/documents-api.ts:25 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `citations.citation` | Citation | frontend/src/lib/components/CitationSources.svelte:15 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `citations.document` | Document | frontend/src/lib/components/CitationSources.svelte:16 | ru-RU: legacy translation.json, key `Document` |
| `citations.revision` | Revision | frontend/src/lib/components/CitationSources.svelte:17 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `citations.chunk` | Chunk | frontend/src/lib/components/CitationSources.svelte:18 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `citations.offset` | Vị trí | frontend/src/lib/components/CitationSources.svelte:19 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |
| `citations.hash` | Source hash | frontend/src/lib/components/CitationSources.svelte:20 | Bản dịch active được viết/rà soát theo hợp đồng hiện tại |

## Plural và tham số

- `citations.count`: count (number); formattedCount được tính khi render. Legacy summary được thay bằng plural active.
- `model.prefix`: name là tên model nguyên văn.
- `upload.errorCode`: code là mã backend nguyên văn.

## Dữ liệu và token giữ nguyên

- Ruvie Agent/RUVIE AGENT và ký hiệu R là thương hiệu.
- Tên tài khoản/project/file/tài liệu/model, nội dung câu hỏi/câu trả lời/citation, IDs/hash/offset/ordinal/code/version: dữ liệu ngoài.
- URL example, MIME type, API/LLM/HTTP/PDF/UTF-8, Enter/Shift+Enter và B/KiB/MiB: token kỹ thuật; câu bao quanh vẫn được dịch.
- Không import runtime references. Nguồn kiến trúc: references/src/lib/i18n/index.ts; languages.json; General.svelte; +layout.svelte; bestMatchingLanguage trong utils/index.ts.
- Catalog English legacy có giá trị rỗng: dùng nội dung English tường minh của active project.

Fallback `Không thể đăng xuất.` trong App được hợp nhất với `auth.errors.logout` để dùng thông báo thử lại thống nhất.
