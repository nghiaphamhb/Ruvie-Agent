# F010 - Thiết kế lại chat workspace và tổ chức frontend Ruvie Agent

## Goal

Thiết kế lại giao diện sau đăng nhập theo ảnh cuối đã được người dùng chọn.
Dùng bố cục và cách tương tác phù hợp từ references.
Giữ các luồng API đang chạy của Ruvie Agent.
Tổ chức mã frontend theo chức năng để dễ tìm và thay đổi.

- Ngày xác nhận plan: 2026-10-13.
- Trạng thái: hoàn tất và kiểm chứng F010-001 đến F010-008.
- Báo cáo triển khai toàn bộ F010: [f010-frontend-validation.md](../../docs/f010-frontend-validation.md).
- Phạm vi chính: frontend Svelte 5/Vite trong repository active.
- Việc viết spec không phải là xác nhận triển khai code.
- Bảo toàn F009 và các thay đổi đang có trong worktree.

### Căn cứ thiết kế

![Giao diện đã chọn](../assets/F010-chat-workspace-approved.png)

Ảnh là mẫu bố cục, không phải asset nền hoặc screenshot để giả lập ứng dụng.
Tên user, model và Project phải lấy từ session/API thực tế.
Dùng logo gốc, không dựng lại biểu tượng R từ ảnh minh họa.

| Nguồn | Vai trò |
|---|---|
| `specs/assets/F010-chat-workspace-approved.png` | Ảnh cuối: navy tối, logo đầy đủ, tab Dự án và sliders góc phải. |
| `output/branding/ruvie-logo-navy-v2.png` | Logo đã chọn, chỉ một R biểu tượng đóng vai trò chữ đầu Ruvie. |
| `specs/feat/F009-auth-pages-registration.md` | Auth, logo/favicon, locale và toast active. |
| `specs/feat/F000-pattern.md` | Thứ tự các phần của spec. |
| `AGENTS.md`, `README.md` | Ranh giới active/reference, kiến trúc và lệnh kiểm tra. |

## User Story

- Là user thường, tôi muốn bố cục chat giống references với thương hiệu Ruvie.
- Là người đọc nội dung dài, tôi muốn nền tối, chữ rõ và không có vòng trang trí.
- Là người dùng, tôi muốn chọn model trong composer và cấu hình LLM từ Cài đặt tài khoản.
- Là thành viên Project, tôi muốn xem dự án được phép truy cập và tải tài liệu từ tab Tài liệu.
- Là người dùng bàn phím/điện thoại, tôi muốn điều hướng, mở menu và modal mà không mất draft.
- Là lập trình viên, tôi muốn component, API client và type của một chức năng nằm trong cùng nhóm thư mục.

## Scope

### In

#### 1. Yêu cầu, code hiện tại và phương án

| Loại | Nội dung |
|---|---|
| **Spec yêu cầu** | Theo ảnh cuối; nền navy tối có ánh xanh login; không ring/curl. |
| **Spec yêu cầu** | Sidebar đủ Chat mới, Tìm kiếm, Ghi chú, Workspace, Dự án, Tài liệu, Thư mục, Cuộc trò chuyện. |
| **Spec yêu cầu** | Logo ở giữa là Ruvie đầy đủ; có sliders góc trên bên phải. |
| **Spec yêu cầu** | Tính năng chưa có API vẫn có menu và khung UI để phát triển sau. |
| **Spec yêu cầu** | Dự án là tab riêng. Tài liệu vẫn có chọn Project và upload. |
| **Spec yêu cầu** | LLM trong avatar → Cài đặt. Khung UI sẽ dùng chung cho admin sau này. |
| **Code hiện tại** | App.svelte điều phối auth/chat/model/upload và ba view chat/documents/llm. |
| **Code hiện tại** | AppNavigation có ba nút, locale và logout trực tiếp. |
| **Code hiện tại** | ChatConversation có lời chào chung và R; composer tách khỏi lời chào; ModelSelector nằm ở header. |
| **Code hiện tại** | LlmConnectionForm khởi tạo metadata/catalog khi mount. |
| **Code hiện tại** | Chat lưu trong RAM. AuthUser chỉ có id/display_name, không có role trong hợp đồng này. |
| **Phương án** | Reuse code active; port UI tương thích của references cho shell/sidebar/menu/settings/composer. |
| **Phương án** | Khung chưa có API không tạo request, dữ liệu hay success giả. |
| **Phương án** | Di chuyển file theo feature, cập nhật callers/tests; không port nguyên subsystem legacy. |

#### 2. Nền, màu và thương hiệu

- Workspace dùng navy tối với ánh xanh khuếch tán nhẹ.
- Token khởi đầu: nền `#071a30`, lớp chuyển `#0b2945`, vùng sáng `#123c60`, sidebar `#051426`.
- Có thể điều chỉnh nhẹ để khớp ảnh và đạt tương phản; không dùng azure sáng như login cho toàn trang.
- Không ring/curl, ảnh trang trí, animation nền hoặc neon.
- Sidebar/menu/modal/composer cùng nhóm màu navy; viền mảnh và nhẹ hơn chữ.
- Chữ chính trắng/gần trắng; chữ phụ xanh xám đủ tương phản.
- Theme scope trong workspace shell, không thay thiết kế login/register.
- Logo PNG hiện có, giữ tỉ lệ và filter trắng phù hợp; không thêm R thứ hai.
- Favicon R và font stack active giữ nguyên; không thêm font/dependency chỉ để giống screenshot.

#### 3. Shell và sidebar

- Desktop có sidebar trái full height, rộng tham chiếu 260–280px, logo và nút collapse ở đầu.
- Thứ tự: Chat mới → Tìm kiếm → Ghi chú → Workspace → Dự án → Tài liệu.
- Sau divider là Thư mục/nút cộng và Cuộc trò chuyện/menu phụ.
- Avatar và display_name ở cuối; avatar mặc định dùng chữ viết tắt từ tên user.
- Tên dài truncate/wrap hợp lý, vẫn có tên truy cập đầy đủ.
- Highlight mục chọn nhẹ; icon SVG outline từ active/reference, không emoji.
- Collapse desktop không reset view/draft/request. Mobile dùng drawer có backdrop/close/Escape/focus return.
- Điều hướng trong SPA, không reload toàn trang hoặc thêm router/SvelteKit.
- View state đề xuất: chat/search/notes/workspace/projects/documents, chỉ là tên nội bộ.
- Chuyển view focus heading; có skip link tới nội dung chính.

#### 4. Phân biệt chức năng từng mục

| Mục | Hành vi F010 | Backend phát triển sau |
|---|---|---|
| Chat mới | Reset turns/draft của chat hiện tại; abort/invalidate stream cũ trước chat mới. | Lưu/nạp nhiều chat. |
| Tìm kiếm | Mở khung tìm kiếm theo references, trạng thái chờ; không remote query. | Tìm chat/tài liệu theo feature sau. |
| Ghi chú | Mở trang khung, không giả lập lưu/xóa. | CRUD ghi chú. |
| Workspace | Khung thư viện Models/Knowledge/Prompts/Tools/Skills, không dữ liệu giả. | API thư viện/quyền. |
| Dự án | GET /projects với id/code/name thực; loading/error/empty/retry. | CRUD Project/thành viên/quyền. |
| Tài liệu | Chọn Project, metadata/file, upload, polling/refresh hiện có. | Danh sách/quản lý tài liệu đầy đủ. |
| Thư mục | Section/nút cộng mở khung chờ cho thao tác thiếu API. | CRUD folder/tổ chức chat. |
| Cuộc trò chuyện | Empty state hoặc một hàng chat hiện tại từ RAM; không giả lịch sử đã lưu. | Danh sách/lưu/khôi phục chat. |

- Menu chưa có API vẫn hiển thị và mở khung được; không khóa toàn sidebar.
- Thao tác lưu/CRUD chưa hỗ trợ có thông báo ngắn đã dịch, không fake success hoặc gọi endpoint tự đặt tên.
- Không lưu nghiệp vụ mới bằng localStorage. Không gọi trạng thái RAM là dữ liệu đã lưu lâu dài.
- Project được chọn ở Tài liệu phục vụ upload, không xác định quyền/scope chat hay retrieval.
- User chưa có membership vẫn vào shell và Settings; Dự án/Tài liệu hiện rỗng đúng API.

#### 5. Chat trống và hội thoại

- Empty chat có logo Ruvie đầy đủ và lời chào theo authUser.display_name ở gần giữa vùng nội dung.
- Không hardcode Phạm Nghĩa. Composer rộng tham chiếu 750–900px và luôn giới hạn theo viewport.
- Textarea có label truy cập, placeholder không thay label.
- Composer: plus dưới trái; single ModelSelector và send dưới phải.
- Gợi ý: Tóm tắt tài liệu; Tìm thông tin có nguồn trích dẫn; So sánh nội dung trong dự án.
- Chọn gợi ý chỉ fill draft/focus textarea, không tự gửi hoặc khẳng định đã tìm dữ liệu.
- Plus mở lựa chọn tải tài liệu hoặc chuyển sang Tài liệu, giữ dữ liệu form upload đã nhập.
- Không gửi file/storage URI/document scope trong POST /chat.
- Khi có lượt, lời chào/gợi ý nhường chỗ cho hội thoại; composer nằm dưới vùng nội dung.
- Giữ delta/citations/completed và lỗi SSE, trạng thái loading/streaming/error/completed.
- Chỉ hiện nguồn khi lượt hoàn tất hợp lệ; không public blob URL.
- Nội dung giữ dạng text đã escape, không thêm Markdown HTML renderer.
- Auto-scroll khi user theo dõi output; không kéo khỏi phần đang đọc.
- Enter gửi một lần, Shift+Enter xuống dòng; giữ xử lý IME/paste.
- Chat mới đang stream phải abort/invalidate callback và finally cũ trước reset.
- Nếu cần generation của chat, tách khỏi sessionSequence; không giả logout để reset chat.
- Response/finally cũ không được ghi vào lượt mới hoặc mở khóa request mới.

#### 6. Model và kết nối LLM

- Reuse ModelSelector: search/listbox/tick/keyboard/reload/confirmed selected_model_id.
- Chuyển selector từ header vào composer; không hardcode model từ mockup.
- Một model; PATCH thành công mới cập nhật ID xác nhận. Giữ operation locks khi chat/model/save đang chạy.
- Bootstrap metadata/catalog khi vào workspace, không chờ mở Settings.
- Current LlmConnectionForm phụ thuộc onMount. Tách bootstrap hoặc giữ owner lifecycle ổn định duy nhất, tránh double fetch/reset.
- Mở/đóng modal không reset catalog hoặc làm chat bị khóa mỗi lần.
- Source=none có CTA Settings → Kết nối LLM, chưa gửi được cho đến khi model xác nhận.
- Giữ semantics omitted/empty/new key, đổi URL xóa draft key, disconnect và server fallback.
- Key đã lưu không về browser. Draft key chỉ trong RAM và xóa khi logout/account đổi.
- Save chậm có owner sống qua modal close; hoặc khóa close rõ ràng khi save. Không mất kết quả, không save trùng.

#### 7. Cài đặt tài khoản, Controls và admin sau này

**Avatar → Cài đặt**

- User thường có Cài đặt/Đăng xuất. Modal chứa Ngôn ngữ và Kết nối LLM active.
- Các nhóm khác cần giữ UI references có thể là khung chờ, không giả API settings mới.
- Locale đổi giữ form/draft/request, không thêm request nghiệp vụ; cơ chế lưu locale active giữ nguyên.
- Dialog có close/Escape, focus ban đầu/trong modal và focus return.

**Sliders góc phải → Tùy chỉnh cuộc trò chuyện**

- Navbar references gọi showControls, nên đây là Controls của chat, không menu avatar.
- Desktop panel phải; mobile panel/drawer phù hợp, có heading/close.
- Có thể hiện model đang chọn và nhóm tùy chỉnh chờ API.
- Tham số sinh/system prompt/công cụ chưa có API không được thêm vào POST /chat.
- Không che send/focus hoặc làm vùng chat có chiều rộng âm.

**Admin sau này**

- Shell/menu/modal phải dùng lại được. F010 không thêm role API hoặc admin panel.
- User thường không thấy Admin Panel; không giả role bằng tên/email/storage.
- Khi phát triển admin, backend là nguồn role/quyền; client menu không là ranh giới authorization.

#### 8. Hợp đồng và state active cần giữ

| API/cơ chế | Giữ nguyên |
|---|---|
| GET /auth/session; POST /auth/login; POST /auth/register; POST /auth/logout | User/CSRF/cookie và semantics active; cold session 401 chỉ hiện auth form. |
| GET /models; GET/PUT/DELETE /llm/connection; PATCH /llm/connection/model | Catalog/config metadata, safe errors và xử lý key/model thuộc server. |
| POST /chat | message/model_id đã xác nhận và cookie; không thêm project_id/ACL/provider settings. |
| GET /projects | Chỉ ProjectSummary được API trả. |
| POST /documents/upload | FormData project_id/title/software/software_version/file và X-CSRF-Token. |
| GET /documents/revisions/{revision_id}/status | Poll/refresh pending/running/ready/failed, timeout/lỗi hiện có. |
| Locale/Toast | en-US/vi-VN/ru-RU; UiMessage; auth toast host duy nhất không nhân đôi khi chuyển shell. |

- Chuyển tab/collapse/sidebar/settings không reset draft, File object, selectedProjectId hoặc status đang poll.
- Giữ polling 2 giây, giới hạn 5 phút; response cũ không sửa upload mới/user mới.
- Logout/401 xóa state tài khoản/key draft/file/chat và abort stream; user A không rò dữ liệu sang user B.
- Không đổi PostgreSQL, default-deny, private storage hoặc provider boundary của backend.

#### 9. Nguồn reuse và cách thích nghi

Ưu tiên active trước; port UI tương thích từ references; không import runtime legacy.

| Nguồn đã đối chiếu | Reuse | Thích nghi |
|---|---|---|
| `frontend/src/lib/components/AppNavigation.svelte` | Callback/view/account state. | Sidebar đầy đủ, collapse/drawer, avatar menu. |
| `frontend/src/lib/components/ChatConversation.svelte`, `ChatComposer.svelte`, `CitationSources.svelte` | Turns, SSE status, IME, cuộn, citations. | Empty chat, logo/name, composer ghép model. |
| `frontend/src/lib/components/ModelSelector.svelte` | Popover/search/keyboard/confirmed model. | Composer, navy theme, kích thước. |
| `frontend/src/lib/components/LlmConnectionForm.svelte`, `frontend/src/lib/llm-api.ts` | Kết nối/key/model, safe errors. | Bootstrap không phụ thuộc modal; Settings layout. |
| `frontend/src/lib/components/DocumentUploadPanel.svelte`, `frontend/src/lib/documents-api.ts` | Chọn Project/file/poll/refresh. | Dự án/Tài liệu views. |
| `frontend/src/lib/components/LanguageSelector.svelte`, `AuthToastLayer.svelte`, `frontend/src/lib/i18n/` | Locale/dropdown/toast host. | Settings và keys mới. |
| `references/src/lib/components/layout/Sidebar.svelte` | Brand/menu/folders/chats/account cuối trang. | View state active, khung chờ thay API chats/folders. |
| `references/src/lib/components/layout/Sidebar/UserMenu.svelte` | Avatar/menu/Settings/vị trí mục admin. | Cookie active; user menu; không token storage/socket. |
| `references/src/lib/components/chat/Placeholder.svelte`, `Suggestions.svelte`, `MessageInput.svelte` | Greeting/composer/suggestions/send/plus. | Single model, session active; không voice/tools/attachment-in-chat mới. |
| `references/src/lib/components/chat/Navbar.svelte`, `ChatControls.svelte` | Sliders mở Controls. | Panel gọn, không xyflow/paneforge/terminal/API params mới. |
| `references/src/lib/components/chat/SettingsModal.svelte` | Dialog/tabs/close/focus. | Locale/LLM active; không port tất cả tab/stores/dependencies legacy. |

Báo cáo triển khai phải ghi nguồn thực sự port và phần đã thích nghi.
Thiếu LICENSE riêng trong references không chặn reuse theo quy tắc repository.

#### 10. Tổ chức frontend — nhiệm vụ phụ

Tìm code theo chức năng; không tạo tầng chỉ để đủ convention.
Cấu trúc đề xuất:

```text
frontend/src/
  App.svelte
  main.ts
  lib/
    layout/
      WorkspacePage.svelte
      WorkspaceShell.svelte
      AppSidebar.svelte
      AccountMenu.svelte
    features/
      auth/       # Pages, forms, validation, API, auth toast
      chat/       # Page, welcome, composer, turns, citations, Controls, SSE client
      documents/  # DocumentsPage, ProjectsPage, upload và API chung
      llm/        # Form kết nối, ModelSelector, API, SettingsModal
    shared/
      LanguageSelector.svelte
      FeaturePlaceholder.svelte
    i18n/         # Giữ cấu trúc locale hiện có
    assets/
      brand/      # Logo chung cho auth/workspace
      auth/       # Trang trí chỉ cho auth
  styles/
    base.css
    workspace.css
frontend/public/ # Giữ favicon.svg
frontend/tests/  # Giữ entry points, cập nhật import
```

- App.svelte ghép auth/workspace/toast, giữ session ownership.
- WorkspacePage là container authenticated state; shell chỉ render layout, không sở hữu API key/quyền.
- Chỉ tách controller/module .svelte.ts nếu cần một owner qua nhiều view. Không bắt buộc global store cho từng feature.
- Feature giữ API client/type/component cạnh nhau; không tách type nhỏ chỉ để tạo file.
- Base CSS giữ reset/font. Workspace CSS/scoped CSS giữ theme sau login; không đưa navy vào :root phá auth.
- Không tạo thư mục rỗng cho Notes/Search/Workspace API chưa có; dùng shared placeholder.
- Không di chuyển tests sang cấu trúc khác trong F010. Giữ npm test và browser entry points README.
- Không đổi public URL favicon. Giữ source logo trong output/branding.

Đường dẫn bảng dưới tính từ `frontend/src/`:

| Hiện tại | Đích đề xuất |
|---|---|
| lib/components/AuthPage.svelte | lib/features/auth/AuthPage.svelte |
| lib/components/LoginForm.svelte | lib/features/auth/LoginForm.svelte |
| lib/components/RegisterForm.svelte | lib/features/auth/RegisterForm.svelte |
| lib/components/PasswordField.svelte | lib/features/auth/PasswordField.svelte |
| lib/components/AuthToastLayer.svelte | lib/features/auth/AuthToastLayer.svelte |
| lib/auth-api.ts; lib/auth-form.ts | lib/features/auth/auth-api.ts; auth-form.ts |
| lib/components/AppNavigation.svelte | lib/layout/AppSidebar.svelte; thay phần UI bằng sidebar mới |
| Phần authenticated của App.svelte | lib/layout/WorkspacePage.svelte; App giữ session/root orchestration |
| lib/components/ChatConversation.svelte | lib/features/chat/ChatConversation.svelte |
| lib/components/ChatComposer.svelte | lib/features/chat/ChatComposer.svelte |
| lib/components/CitationSources.svelte | lib/features/chat/CitationSources.svelte |
| lib/chat-api.ts; lib/chat-turn.ts | lib/features/chat/chat-api.ts; chat-turn.ts |
| lib/components/DocumentUploadPanel.svelte | lib/features/documents/DocumentUploadPanel.svelte |
| lib/documents-api.ts | lib/features/documents/documents-api.ts |
| lib/components/LlmConnectionForm.svelte | lib/features/llm/LlmConnectionForm.svelte |
| lib/components/ModelSelector.svelte | lib/features/llm/ModelSelector.svelte |
| lib/llm-api.ts | lib/features/llm/llm-api.ts |
| lib/components/LanguageSelector.svelte | lib/shared/LanguageSelector.svelte |
| lib/assets/auth/ruvie-logo.png | lib/assets/brand/ruvie-logo.png |
| app.css | styles/base.css và styles/workspace.css theo trách nhiệm |
| main.ts và test imports | Cập nhật import; giữ bootstrap i18n/mount và test entry point |

File mới dự kiến: WorkspaceShell, AccountMenu, ChatPage, ChatWelcome, ChatControlsPanel,
SettingsModal, ProjectsPage, DocumentsPage, FeaturePlaceholder.
Tên cuối có thể chỉnh nhẹ khi triển khai; phải cập nhật bảng và báo cáo.

### Out

- Backend endpoint/migration mới; CRUD Project/notes/folders/workspace hoặc lưu chat lâu dài.
- Thêm role API, admin panel hoặc tự cấp quyền account.
- Multi-model, voice, image generation, tools/agents/web search hoặc Markdown HTML renderer.
- Thêm provider/key/model parameters/ACL vào chat/retrieval client.
- Đổi thiết kế login/register/favicon/logo ngoài cập nhật import theo vị trí mới.
- Di chuyển/chạy references; đọc/sửa/chạy directory archive không phân biệt hoa thường.
- Router/design system/state framework/dependency không cần thiết.

## Flow

### 1. Vào workspace

1. App khôi phục session hoặc nhận AuthSession sau login/register.
2. Tạo owner của user hiện tại và render shell.
3. Tải Projects và bootstrap LLM metadata/catalog độc lập với mở Settings.
4. Source=none có CTA Settings; loading/selection_required khóa gửi với status rõ.
5. Catalog/model xác nhận xong thì composer sẵn sàng theo operation locks active.
6. Projects error không làm shell mất; model error có reload/cấu hình.
7. Toast auth thành công tiếp tục hiển thị khi chuyển shell.

### 2. Gửi chat và Chat mới

1. Nhập câu hỏi/chọn gợi ý điền draft.
2. Chỉ gửi draft hợp lệ khi model xác nhận, không có operation khóa.
3. streamChat gửi message/model_id theo contract active.
4. Hiện lượt mới, nhận SSE và chuyển composer xuống dưới hội thoại.
5. Hoàn tất mới hiện citations; lỗi dùng safe message và không giữ nguồn chưa xác nhận.
6. Chat mới abort/invalidate stream cũ, reset turns/draft, focus textarea.
7. Chat mới không xóa Project/upload state; request cũ không sửa request mới.

### 3. Sidebar và tài liệu

1. Dự án hiện GET /projects với loading/error/empty/retry.
2. Chọn Project được trả có thể mở Tài liệu và đặt selectedProjectId.
3. Tài liệu giữ form metadata/file/upload active.
4. Chuyển tab giữ form/status/polling; trở lại thấy trạng thái hiện tại.
5. Collapse/drawer không reset operation.
6. Mục chưa có API mở khung chờ, không giả request/data/mutation.

### 4. Avatar và Controls

1. Avatar mở menu; click ngoài/Escape đóng và trả focus.
2. Cài đặt mở modal locale/LLM.
3. Save/disconnect/reload dùng API active và cập nhật catalog cùng owner, không mount-dependent reset.
4. Đóng modal giữ chat/model/upload và ownership save chậm.
5. Sliders mở Controls; tùy chọn chưa hỗ trợ không làm đổi request chat.
6. Logout/401 xóa state, đóng menu/modal/panel và abort stream.
7. Bỏ response cũ; user mới nhận owner/state mới.

## Edge Cases

| Tình huống | Kết quả |
|---|---|
| Không có Project | Dự án/Tài liệu rỗng; chat/menu/Settings vẫn truy cập được. |
| Source=none/catalog loading | Gửi khóa, CTA/status rõ; cấu hình đã có được load không cần mở modal. |
| PATCH thất bại/model biến mất | Giữ ID xác nhận hoặc chặn/reload theo lỗi active; không gửi ID chưa xác nhận. |
| Chat mới khi streaming | Abort/invalidate; callback/finally cũ không ghi hoặc mở khóa lượt mới. |
| Đổi view khi streaming/upload | Operation đúng owner còn hoạt động; state giữ; model/key locks active. |
| Close modal khi save chậm | Owner giữ kết quả hoặc close bị khóa rõ; không save trùng. |
| Logout rồi user khác login khi request chậm | Không lộ text/key/file/project/catalog của user cũ. |
| Mobile/viewport thấp/200% zoom | Không cuộn ngang; send/close/focus tới được; drawer/panel không che thao tác. |
| Tên dài/chữ Nga | Wrap/truncate phù hợp, không kéo viewport; tên truy cập đầy đủ. |
| Locale đổi khi modal/menu/lỗi đang mở | Text đổi, form/request ownership và số request nghiệp vụ không đổi. |
| Suggestion/plus/model trong form | Không submit ngoài ý muốn; nút phụ type=button. |
| Không có history API | Chỉ RAM hiện tại/empty; không giả persistence. |
| Backend trả HTML/secret trong lỗi | Safe UiMessage, text/metadata escape; không raw detail. |
| Không hỗ trợ blur | Navy surface đủ đậm, nội dung rõ. |
| Refactor làm scan/import test sai | Cập nhật scan recursive/import, không bỏ test hoặc giảm coverage. |

## Acceptance Criteria

- [x] **AC-01:** Workspace khớp ảnh cuối: navy tối, ánh xanh nhẹ, không asset vòng trang trí.
- [x] **AC-02:** Sidebar đủ sáu mục đúng thứ tự, Thư mục/Cuộc trò chuyện và account cuối trang.
- [x] **AC-03:** Dự án/Tài liệu là hai view; Tài liệu vẫn chọn Project từ API.
- [x] **AC-04:** Collapse desktop không reset view/draft/request/status.
- [x] **AC-05:** Drawer mobile mở/đóng được bằng pointer/keyboard, không cuộn ngang.
- [x] **AC-06:** Empty chat có logo Ruvie đầy đủ và tên từ session, không hardcode tên.
- [x] **AC-07:** Empty chat có composer/gợi ý giữa trang; có turns thì composer xuống dưới và tới được trên viewport thấp.
- [x] **AC-08:** Composer có plus/model/send; Enter/Shift+Enter/IME đúng, nút phụ không submit.
- [x] **AC-09:** ModelSelector dùng catalog thật/single model/confirmed ID và giữ operation locks.
- [x] **AC-10:** Reload với connection/model đã có dùng chat được trước mở Settings; không phụ thuộc mount modal hoặc double initialization.
- [x] **AC-11:** Settings có locale/LLM active, giữ key omission/deletion/disconnect/fallback và safe errors.
- [x] **AC-12:** Modal open/close không reset catalog/chat/upload; save chậm cập nhật đúng user, không trùng request.
- [x] **AC-13:** Sliders góc phải mở/đóng Controls; tùy chọn chưa có API không thêm body fields vào chat.
- [x] **AC-14:** Dự án hiển thị ProjectSummary thật với loading/error/empty/retry; không CRUD giả.
- [x] **AC-15:** Upload/status/timeout/refresh giữ contract/polling khi đổi tab.
- [x] **AC-16:** Menu chưa có API hiện và mở khung chờ được; không endpoint giả/fake success.
- [x] **AC-17:** Chat mới reset RAM chat/draft, abort/invalidate; callback/finally cũ không đổi chat mới.
- [x] **AC-18:** Chuyển view/collapse giữ draft/File/selectedProjectId và operation status.
- [x] **AC-19:** Logout/401/user khác login không rò state/key/file/catalog/response cũ.
- [x] **AC-20:** Menu/modal/panel đóng khi phiên kết thúc; logout failure còn safe feedback active.
- [x] **AC-21:** Ba locale đủ keys; đổi locale không reset form hoặc thêm request nghiệp vụ.
- [x] **AC-22:** Keyboard/focus/Escape/focus return cho menu/modal/drawer hoạt động; có skip link.
- [x] **AC-23:** Chữ thường contrast ≥4.5:1, icon trạng thái ≥3:1, vùng bấm chính ≥44×44px; 200% zoom không che hành động.
- [x] **AC-24:** SSE/citations/error/text rendering giữ hành vi active; HTML không thực thi.
- [x] **AC-25:** UI không truyền provider/key/Project/ACL vào chat; không lưu key/session trong browser storage; không public blob URL mới.
- [x] **AC-26:** Login/register/toast/logo/favicon giữ F009 sau khi cập nhật import.
- [x] **AC-27:** Production code theo nhóm chức năng, không legacy runtime import, empty feature folders hoặc abstraction generic thừa.
- [x] **AC-28:** Unit/build/browser/regression/integration phù hợp pass; báo cáo pass/fail/skip thật và ảnh QA.
- [x] **AC-29:** Không endpoint backend/role API/migration mới; contract dữ liệu active giữ nguyên.
- [x] **AC-30:** Plus dẫn tới upload active, không gửi file/document scope vào chat.
- [x] **AC-31:** Suggestion chỉ fill draft/focus, không tự gọi chat.
- [x] **AC-32:** User thường không thấy Admin Panel; không giả nguồn xác nhận quyền dù cấu trúc UI cho phép mở rộng sau.

## Tasks

### F010-001 — Token và nền workspace

- [x] **F010-001**

**Work**
1. Đối chiếu ảnh đã lưu, logo gốc và palette Scope.
2. Đặt token bg/text/surface/border/hover/selected/error của workspace.
3. Scope theme sau login, giữ auth CSS.
4. Dùng logo gốc ở sidebar/welcome, giữ tỉ lệ và một R.
5. Không gắn ảnh minh họa/vòng trang trí vào workspace DOM.

**Where**: app.css hoặc scoped workspace CSS ở giai đoạn đầu; sau F010-007 là styles/workspace.css; asset brand dùng chung.

**Done**: AC-01, AC-06, AC-23, AC-26; UI render/contrast khớp mẫu và có bằng chứng đối chiếu.

### F010-002 — Shell, sidebar, avatar và sliders

- [x] **F010-002**

**Work**
1. Reuse AppNavigation active và Sidebar/UserMenu/Navbar theo bảng nguồn.
2. Tạo shell/sidebar/account menu đủ mục; không copy APIs/stores legacy.
3. Collapse desktop/drawer mobile, account cuối trang.
4. Menu avatar mở Cài đặt/Đăng xuất dùng callback active.
5. Sliders mở Controls; nhóm chưa hỗ trợ là khung chờ.
6. View state SPA đơn giản, không router/auth role mới.

**Where**: App.svelte/AppNavigation.svelte; mới WorkspaceShell/AppSidebar/AccountMenu/ChatControlsPanel; đích cuối layout/chat.

**Done**: AC-02, AC-04, AC-05, AC-13, AC-20, AC-22, AC-32; mọi trigger mở/đóng/focus được, không fake backend.

### F010-003 — Chat page, composer và hội thoại

- [x] **F010-003**

**Work**
1. Reuse ChatConversation/ChatComposer/CitationSources/chat-api/chat-turn.
2. Tạo ChatPage/ChatWelcome với display_name thật và logo đầy đủ.
3. Ghép composer/model/suggestions; gợi ý chỉ fill draft; plus dẫn tới Tài liệu.
4. Empty → conversation layout; giữ auto-scroll/text an toàn.
5. Chat mới abort và có ownership riêng để callback/finally cũ không ảnh hưởng lượt mới.
6. Giữ body/event/error/citations active; không persistence hoặc chat params mới.

**Where**: phần chat App.svelte; các component/client active; mới ChatPage/ChatWelcome; đích lib/features/chat/ và ModelSelector trong llm/.

**Done**: AC-06 đến AC-09, AC-17, AC-24, AC-25, AC-30, AC-31; browser checks cho stream chậm/new chat, IME, suggestion/plus/citations.

### F010-004 — Settings và lifecycle LLM

- [x] **F010-004**

**Work**
1. Reuse SettingsModal reference cho layout dialog/tabs; active LlmConnectionForm/LanguageSelector cho behavior.
2. Bố trí Ngôn ngữ/Kết nối LLM.
3. Chuyển bootstrap ra khỏi mount-dependent form hoặc dùng owner ổn định duy nhất.
4. Modal reopen không reset/double fetch; giữ none/server fallback/confirmed model.
5. Giữ semantics giữ/xóa/thay key, disconnect và safe errors.
6. Giữ ownership save/reload chậm/account đổi; không key trong storage/log/toast.
7. Giữ focus/Escape/close, không port settings backend legacy.

**Where**: App.svelte/WorkspacePage, LlmConnectionForm, ModelSelector, llm-api, LanguageSelector; SettingsModal mới trong llm/.

**Done**: AC-10, AC-11, AC-12, AC-19, AC-21, AC-25; reload có connection phải chat được trước mở Settings.

### F010-005 — Dự án, Tài liệu và view chờ API

- [x] **F010-005**

**Work**
1. ProjectsPage đọc listProjects với trạng thái đầy đủ, không CRUD mới.
2. Chọn Project API trả chuyển tới Tài liệu/selectedProjectId hợp lệ.
3. DocumentsPage chứa upload panel active, giữ metadata/file/poll/timeout/refresh.
4. Giữ owner khi đổi view, không unmount mất File hoặc nhận response cũ.
5. FeaturePlaceholder cho Search/Notes/Workspace/Folders/history chưa có API.
6. Menu vẫn mở được, trạng thái chờ rõ, không fake data/localStorage nghiệp vụ.
7. Chat section chỉ phản ánh RAM hiện tại/empty, không giả saved history.

**Where**: App.svelte/WorkspacePage, DocumentUploadPanel/documents-api; ProjectsPage/DocumentsPage trong documents/; shared/FeaturePlaceholder.

**Done**: AC-03, AC-14, AC-15, AC-16, AC-18, AC-29; browser checks cho đổi tab khi upload/poll và Projects empty/error.

### F010-006 — Responsive, locale và accessibility

- [x] **F010-006**

**Work**
1. Hoàn thiện desktop collapse/mobile drawer và modal/panel không tràn viewport.
2. Bổ sung keys đủ ba locale, giữ form/request khi đổi locale.
3. Tab order/focus-visible/Escape/focus return/skip link.
4. Tên dài/chữ Nga, vùng bấm/contrast phù hợp.
5. Viewport thấp/zoom không che composer/model popover/toast/close.
6. Không animation nền; transition tôn trọng reduced motion.

**Where**: layout/chat/settings/shared components; workspace styles; lib/i18n/locales/{en-US,vi-VN,ru-RU}/translation.json.

**Done**: AC-05, AC-07, AC-21 đến AC-23. Kiểm tra 1920×1080, 1366×768, 1280×605, 1024×600, 768×1024, 375×812, 320×568; thêm 640×360 CSS px với scale=2.

### F010-007 — Tổ chức frontend theo chức năng (nhiệm vụ phụ)

- [x] **F010-007**

**Work**
1. Đối chiếu bảng di chuyển với component tạo ở F010-001 đến F010-006.
2. Move theo feature/layout/shared; giữ tên hàm/API contract nếu không cần đổi.
3. Tách authenticated container khỏi App vừa đủ để session/operation ownership rõ.
4. Logo chung vào assets/brand; giữ auth decoration/public favicon.
5. Tách base/workspace CSS; bỏ selector/import cũ chỉ khi không còn caller.
6. Cập nhật main.ts, import production/test và scan key recursive.
7. Giữ tests entry points; cập nhật sơ đồ frontend trong README; lệnh chạy vẫn ở README.
8. Ghi bảng đường dẫn cuối; không để bản copy/compatibility export song song hoặc generic layer để tránh sửa callers.
9. Chạy lại kiểm tra sau move; không skip/giảm test để che lỗi import.

**Where**: frontend/src/, imports frontend/tests/, README.md, bảng migration cuối trong báo cáo F010.

**Done**: AC-26, AC-27, AC-28; không old imports, locale scan đọc đủ components, auth/API/browser regression pass.

### F010-008 — Kiểm chứng và tài liệu

- [x] **F010-008**

**Work**
1. Behavior changes của từng task có test trước khi implement; task này tổng hợp kiểm chứng cuối.
2. Giữ unit tests, cập nhật browser selectors; giữ assertions key/model ownership/request count/cookie/CSRF/upload/isolation.
3. Thêm workspace checks: sidebar/Settings/Controls/placeholder/new chat/suggestions/đổi view khi operation chậm.
4. Check catalog bootstrap trước mở Settings, modal reopen, source=none và PATCH thất bại.
5. Chạy unit/build/browser theo README; entry point workspace-browser.mjs mới nếu cần phải được ghi cách chạy rõ trong README.
6. Chạy browser→backend auth/LLM hiện có với PostgreSQL/provider fixture tạm khi môi trường sẵn sàng, không .env/provider thật.
7. Chụp empty chat, streaming/completed/citations, Projects/Documents/Settings/Controls/collapse/mobile.
8. Báo cáo pass/fail/skip thật, nguồn legacy reuse, phần deferred và bảng file trong docs/f010-frontend-validation.md. Ảnh QA ở logs/f010/, không commit output test.
9. Chỉ tick task/AC đã implement và kiểm chứng; không tick vì viết xong spec.

**Where**: các unit/browser tests hiện có trong frontend/tests/ và workspace checks mới; README.md; docs/f010-frontend-validation.md; logs/f010/.

**Done**: AC-01 đến AC-32 có bằng chứng hoặc ghi rõ chưa đạt. Không che skip; không tuyên bố full backend suite nếu chỉ chạy targeted integration. Nếu phát sinh backend change ngoài Scope, cần tách/được xác nhận và chạy suite backend theo repository rules.
