# F010 — Báo cáo triển khai và kiểm chứng

Trạng thái: hoàn tất 8 task và 32 AC; bằng chứng trong bảng audit bên dưới.

Ngày: 2026-10-13. Phạm vi: toàn bộ F010-001 đến F010-008 theo spec đã xác nhận.
Không triển khai backend/migration mới trong F010. Các thay đổi F009 sẵn có trong worktree được giữ nguyên.

## Hành vi đã triển khai

Workspace có nền navy/ánh xanh, logo Ruvie đầy đủ, tên session, sáu mục sidebar,
sections Thư mục/Cuộc trò chuyện, avatar Settings/Logout và sliders Controls.
Chat trống dùng greeting/composer/suggestions; có turns thì dùng hội thoại active.
Gợi ý chỉ điền draft. Plus mở Tài liệu. Chat mới chỉ reset chat/draft và
abort/invalidate stream, không xóa metadata/File/project của form upload.

ProjectsPage dùng ProjectSummary từ GET /projects với loading/error/empty/retry.
Chọn một ID có trong danh sách mở Tài liệu và đặt project upload; đây không phải
scope/authorization cho chat. DocumentsPage giữ form và polling active: 2 giây,
5 phút, refresh sau timeout. Chuyển view/collapse không unmount form hoặc File.
Search có khung nhập chờ; Notes có khung ghi chú chờ; Workspace có năm tab
Models/Knowledge/Prompts/Tools/Skills; Folders/History có heading/trạng thái chờ.
Không fake dữ liệu/persistence/success/endpoint cho các chức năng này.

App sở hữu auth/session/toast. WorkspacePage được keyed theo user/CSRF, sở hữu
chat/model/projects/upload và các operation guards. Khi logout/401, unmount owner
invalidates session/upload requests, aborts chat; LlmConnectionForm cũng invalidates
sequence và xóa draft key. Form LLM luôn mounted trong native dialog đóng,
bootstrap một lần trước khi người dùng mở Settings. Modal reopen không reset
catalog và save chậm vẫn có owner. Key omission/xóa/thay, disconnect/fallback và
confirmed selected_model_id giữ contract active.

## File cuối, migration và vai trò

Đường dẫn dưới `frontend/src/`. Mỗi file có một đích duy nhất; không compatibility copies.
Các file chỉ move/import không đổi API/type/validation hoặc business behavior.

| File cuối | Nguồn trước F010-007 | Vai trò, input → output / hàm quan trọng |
| --- | --- | --- |
| `App.svelte` | App.svelte | AuthSession → keyed WorkspacePage. checkSession/login/register/logout dùng cookie/CSRF; clearSession unmount toàn owner; toast host duy nhất giữ thông báo qua auth transition. |
| `lib/pages/WorkspacePage.svelte` | Phần authenticated của App.svelte | User/CSRF/authBusy/error → shell/views. selectView chỉ đổi visibility/focus; newChat abort/invalidate bằng chatSequence; submit giữ sessionSequence và generation ở callback/catch/finally. loadProjects, selectProject, submitUpload, refreshUploadStatus, reloadModels, chooseModel giữ contract active. onDestroy invalidates mọi operation. toggleSidebar/resizeWorkspace/closeSettings/closeControls quản lý focus/surface. |
| `lib/layout/WorkspaceShell.svelte` | lib/components/WorkspaceShell.svelte | State/snippets → shell/toolbar/skip link/sidebar. Mobile main inert, drawer traps Tab; Escape không xử lý lại event đã được menu xử lý. close đợi tick trước trả focus; resize qua WorkspacePage bỏ modal state ở desktop. |
| `lib/layout/AppSidebar.svelte` | lib/components/AppNavigation.svelte | View/name/callback → sáu menu đúng thứ tự, logo/collapse/sections/account. Brand trở lại chat không reset; New Chat reset. Folder/history mở khung riêng, không fake persistence. |
| `lib/layout/AccountMenu.svelte` | lib/components/AccountMenu.svelte | Name/busy/callback → initials/avatar/native popover. toggle tính vị trí, close/Escape/light dismiss trả focus; không cướp focus của control khác khi click; arrow đổi menu item. Chỉ Settings/Logout, không suy diễn role. |
| `lib/features/auth/AuthPage.svelte` | lib/components/AuthPage.svelte | Auth status/callback → glass login/register page, locale/route switching; chỉ cập nhật imports/asset. |
| `lib/features/auth/LoginForm.svelte` | lib/components/LoginForm.svelte | Fields/callback → validation và login action; giữ policy login existing account. |
| `lib/features/auth/RegisterForm.svelte` | lib/components/RegisterForm.svelte | Name/email/password/confirmation → validate + register callback; confirmation không vào API body. |
| `lib/features/auth/PasswordField.svelte` | lib/components/PasswordField.svelte | Value/labels → visibility control; imports đổi vị trí, interaction giữ nguyên. |
| `lib/features/auth/AuthToastLayer.svelte` | lib/components/AuthToastLayer.svelte | Trusted UiMessage/notice ID → Sonner toast localized; một host, không raw server details. |
| `lib/features/auth/auth-api.ts` | lib/auth-api.ts | Credentials/session → cookie API/typed safe errors; chỉ đổi relative import. |
| `lib/features/auth/auth-form.ts` | lib/auth-form.ts | Fields → AuthFieldErrors; Unicode/password exact matching, domain-dot registration và login local-domain giữ nguyên. |
| `lib/features/chat/ChatPage.svelte` | lib/components/ChatPage.svelte | Turns/draft/catalog/callback → welcome hoặc conversation, composer/model/suggestions. suggest điền/focus, không tự submit; plus callback Documents. |
| `lib/features/chat/ChatWelcome.svelte` | lib/components/ChatWelcome.svelte | Session display_name → greeting và logo gốc đầy đủ, giữ aspect ratio. |
| `lib/features/chat/ChatComposer.svelte` | lib/components/ChatComposer.svelte | Draft/locks/model snippet → textarea, plus/model/send. handleInputKeydown giữ Enter/Shift+Enter/IME. Focus ring ở composer, không inner textarea rectangle. |
| `lib/features/chat/ChatConversation.svelte` | lib/components/ChatConversation.svelte | Turns/visible → escaped text/status/citations và reading-position/autoscroll. Bỏ empty greeting cũ không còn caller; ChatWelcome sở hữu empty page. |
| `lib/features/chat/CitationSources.svelte` | lib/components/CitationSources.svelte | Citation metadata → native details/source pill với vùng bấm 44px; không content/blob URL; import locale cập nhật. |
| `lib/features/chat/ChatControlsPanel.svelte` | lib/components/ChatControlsPanel.svelte | Open/model/callback → panel phải, model thật và deferred message. Giới hạn chiều cao/scroll; close/Escape/focus rời panel đóng overlay, tránh che focus; không chat params mới. |
| `lib/features/chat/chat-api.ts` | lib/chat-api.ts | message/model_id → SSE events/safe error; cookie request và parser giữ nguyên. |
| `lib/features/chat/chat-turn.ts` | lib/chat-turn.ts | Type lượt RAM, locale message type; không persistence mới. |
| `lib/features/documents/ProjectsPage.svelte` | Mới | ProjectSummary/loading/error/callback → danh sách/loading/lỗi/rỗng/retry; onselect nhận ID thật trong list. |
| `lib/features/documents/DocumentsPage.svelte` | Mới | Child snippet → heading và form active; state vẫn ở WorkspacePage. |
| `lib/features/documents/DocumentUploadPanel.svelte` | lib/components/DocumentUploadPanel.svelte | Projects/File/status/bindings/callback → metadata upload/status/refresh. Control tối thiểu 44px; chữ nút Upload dùng surface trên accent sáng để đạt contrast. |
| `lib/features/documents/documents-api.ts` | lib/documents-api.ts | GET /projects, multipart upload, status → typed results/safe errors; contract không đổi. |
| `lib/features/llm/LlmConnectionForm.svelte` | lib/components/LlmConnectionForm.svelte | CSRF/locks/callback → connection metadata/catalog và form operations; sequence owner active giữ nguyên. |
| `lib/features/llm/ModelSelector.svelte` | lib/components/ModelSelector.svelte | Catalog/confirmed ID/locks/callback → compact searchable selector/popover trong composer; persistence PATCH active. |
| `lib/features/settings/SettingsModal.svelte` | lib/components/SettingsModal.svelte | Open/tab/children → native dialog General/LLM. tabKey arrow/Home/End; dialogKey traps Tab; cancel xử lý một lần, onclose guard tránh callback lặp làm mất focus. Child form không unmount khi close. |
| `lib/features/llm/llm-api.ts` | lib/llm-api.ts | Connection/key/model → cookie/CSRF API; omission/empty/new key giữ nguyên, errors redacted. |
| `lib/shared/LanguageSelector.svelte` | lib/components/LanguageSelector.svelte | Locale → native selector, persistence locale active; không request nghiệp vụ. |
| `lib/shared/FeaturePlaceholder.svelte` | Mới | View/title → khung Search/Notes/Library/Folders/History; library tabs dùng keyboard/ARIA, chỉ đổi UI state, không API/storage. |
| `lib/shared/WorkspaceIcon.svelte` | lib/components/WorkspaceIcon.svelte | Name/size → outline SVG; sliders Knobs path port tương thích, không dependency. |
| `lib/assets/brand/ruvie-logo.png` | lib/assets/auth/ruvie-logo.png | Move cùng bytes, dùng chung auth/sidebar/welcome; original artwork trong output/branding giữ nguyên. |
| `lib/assets/brand/README.md` | Mới | Ghi nguồn logo, một R, imports/display filter và favicon giữ nguyên. |
| `styles/base.css` | app.css | Reset/font/base tokens/root/hidden/reduced-motion; bỏ selector topbar/workspace-header/connection-prompt cũ không còn caller. Assistant mark dùng surface trên accent sáng. |
| `styles/workspace.css` | workspace.css | Authenticated tokens/gradient/layout/focus/mobile; không đưa navy vào :root phá auth. |
| `main.ts` | main.ts | Import styles mới và init locale trước mount. |
| `lib/i18n/locales/vi-VN/translation.json` | Cùng đường dẫn | Workspace/deferred/project/select/search/notes keys và Documents label tiếng Việt. |
| `lib/i18n/locales/en-US/translation.json` | Cùng đường dẫn | Bộ keys tiếng Anh tương ứng. |
| `lib/i18n/locales/ru-RU/translation.json` | Cùng đường dẫn | Bộ keys tiếng Nga tương ứng, long text được kiểm tra. |

`frontend/public/favicon.svg` và auth decorations không đổi. `README.md` mô tả
cấu trúc cuối và lệnh chạy. Tests giữ entry points, cập nhật imports; i18n scan
đọc recursive toàn src và loại archive ở mọi độ sâu. Không lib/components cũ,
không empty feature directories, runtime imports references hay dependency mới.

## Nguồn reuse thực tế

Chỉ đọc/adapt, không chạy/import runtime `references/`:

- `references/src/lib/components/layout/Sidebar.svelte`: brand/menu/sections/account.
- `references/src/lib/components/layout/Sidebar/UserMenu.svelte`: menu Settings/Logout; không JWT/token storage/role.
- `references/src/lib/components/chat/Navbar.svelte`, `icons/Knobs.svelte`: sliders/showControls/SVG.
- `references/src/lib/components/chat/Placeholder.svelte`, `MessageInput.svelte`: greeting/composer/suggestions/arrow; giữ active IME/textarea/API.
- `references/src/lib/components/chat/SettingsModal.svelte`, `ChatControls.svelte`: dialog/tabs/panel; không xyflow/paneforge/legacy settings backend.
- `references/src/lib/components/layout/SearchModal.svelte`, `layout/Sidebar/SearchInput.svelte`: search box hierarchy; không port query/filter/search chat API.
- `references/src/routes/(app)/workspace/+layout.svelte`: thư viện Models/Knowledge/Prompts/Tools/Skills; không role/permissions stores hoặc endpoints legacy.
- Active ChatConversation/CitationSources/DocumentUploadPanel/LlmConnectionForm/LanguageSelector/API clients: giữ use cases và contracts; không backend authorization client-side mới.

## Lệnh và kết quả kiểm thử cuối

PowerShell từ root; build trước browser. PATH có Node, browser env theo README:

```powershell
$env:RUVIE_PLAYWRIGHT_PATH='C:/Users/phamd/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'
$env:RUVIE_BROWSER_PATH='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
```

| Lệnh | Kết quả cuối |
| --- | --- |
| `npm.cmd --prefix frontend run build` | Pass, không warning Svelte |
| `npm.cmd --prefix frontend test` | 34 pass, 0 fail, 0 skip |
| `node frontend/tests/auth-browser.mjs` | 62 checks pass, 0 fail/skip |
| `node frontend/tests/workspace-browser.mjs` | 29 checks pass, 0 fail/skip (gồm 8 viewport) |
| `node frontend/tests/llm-browser.mjs` | 66 checks pass, 0 fail/skip (locale/upload/layout/SSE/locks) |
| `.venv\Scripts\python.exe -m unittest test_f006_008_browser_e2e test_f009_006_registration_e2e.RegistrationPostgresTests.test_browser_register_reload_logout_and_login_against_active_backend` | 2 pass, 0 fail, 0 skip; PYTHONPATH=backend;tests |

Mock browser không dùng dữ liệu dev. Hai tích hợp dùng API active và disposable
PostgreSQL/pgvector + fake provider, không DB dev/provider .env. Không chạy full
backend suite trong F010 vì không sửa backend. Không tuyên bố full backend pass.
Fixture có warning Starlette/httpx đã có sẵn; không thay dependency ngoài scope.

Kiểm thử Projects chạy đỏ trước code (thiếu projects page). Settings trap,
menu/drawer Escape, outside-click focus-return, focus-return khi drawer đóng, upload/citation hit targets, contrast và
Controls geometry đều có assertion đỏ trước fix. Trong migration, unit tests
phát hiện literal dấu chấm email bị rewrite nhầm; đã khôi phục cùng validation
active, không nới/chặt policy. Regression selector được scope theo Documents vì
Projects cũng dùng cùng empty text; assertions nghiệp vụ không bị bỏ hoặc giảm.
Lượt tích hợp đầu lỗi setup do Docker tắt (0 tests, 2 setup errors); đã khởi động
Docker đã cài, xác minh engine rồi chạy lại. Không biến lỗi thành skip.

Tích hợp đã chạy trên WorkspacePage/auth ownership cuối. Sau đó chỉ hoàn thiện
vùng bấm CSS citation và focus-return light dismiss của menu; đã build và chạy
lại unit/workspace/LLM browser. Hai thay đổi này không đổi client/API/session
hoặc server authorization. Contrast text/icon trên vùng navy sáng nhất: ink
#f0f6fc trên #123c60 đạt 10.48:1; muted #b1c5da đạt 6.45:1. Các test còn đo
màu thực của Upload, focus geometry và vùng bấm primary/upload/citation.

## Audit Acceptance Criteria

Mỗi AC cần cả implementation và evidence; bảng này không suy ra hoàn tất chỉ từ checkbox.

| AC | Bằng chứng |
| --- | --- |
| 01 | workspace.css + screenshot chat-desktop đối chiếu mock; không auth ring/curl DOM sau login. |
| 02 | AppSidebar thứ tự sáu mục/sections/footer; workspace-browser nav assertion/ảnh. |
| 03 | ProjectsPage/DocumentsPage riêng; Project list chọn p1/p2, upload select dùng chính ID API trả. |
| 04 | Collapse giữ draft, catalog không re-fetch; workspace + llm-browser state checks. |
| 05 | Eight-viewport drawer backdrop/keyboard/Escape/nested menu/focus-return, không overflow. |
| 06 | Full logo/name session assertions; brand asset bytes không đổi. |
| 07 | Empty greeting/suggestions; turn layout composer bottom/scroll; viewport checks và layout-browser long conversation. |
| 08 | Plus/model/send; llm-browser Enter/ShiftEnter/IME single submit, workspace plus preserves File. |
| 09 | llm-browser confirmed selection/PATCH failures/search/long list/locks; integration two accounts. |
| 10 | Models read trước Settings, reopen no double GET; source=none CTA trong upload-browser. |
| 11 | Unit API key omission/empty/new + llm-browser save/disconnect/fallback/safe errors. |
| 12 | Closed mounted dialog save gate/reopen request count; workspace/locale checks giữ form/catalog/requests. |
| 13 | Controls trigger/close/model/deferred; chat body assertion chỉ message/model_id. |
| 14 | Projects empty/error/safe detail/retry/loading delayed response/select; workspace-browser. |
| 15 | upload-browser pending/failed/ready/2s deadline/5min timeout/refresh/404/session guards; đổi view giữ polling. |
| 16 | Search box/Notes/Library tabs/Folders/History có khung chờ; unsupported actions không thêm request/storage/mutation. |
| 17 | Old stream finish sau New Chat không restore answer/unlock new request; workspace-browser ownership check. |
| 18 | Draft/File/project/metadata qua đổi view/collapse/New Chat/Settings; browser regressions. |
| 19 | Component session guard/unmount + delayed LLM/model/project/upload/account tests và backend browser isolation hai account. |
| 20 | Logout 503 vẫn giữ workspace/safe feedback; 401 khi Settings mở unmount surfaces; auth/LLM/upload regressions. |
| 21 | Catalog parity/recursive key scan unit; locale-browser đổi locale trong delayed login/model/save/SSE/upload giữ state/request count. |
| 22 | Skip link focuses main; native modal/tab arrows/trap; menu/drawer Escape/focus-return trên eight viewports; layout-browser focus outlines. |
| 23 | Actual 44px primary actions/upload controls; actual Upload color contrast >=4.5; six token text pairs ở layout-browser; icon ink trên navy >=3. Zoom 640x360 @2 có focus/model/send/close tới được. |
| 24 | SSE unit/parser + llm-browser partial/completed/error/citations/plain text/autoscroll; no HTML execution/content fetch. |
| 25 | API/unit/body only message/model_id; no provider/key/project/ACL, safe errors, no business/key/session browser persistence/blob links. Integration preserves server authorization. |
| 26 | auth-browser + real register/reload/login/logout integration; logo/favicon/toast unchanged assets/host. |
| 27 | Source inventory/import scan, lib/components removed; canonical migration table, no legacy runtime import/empty features. |
| 28 | Final unit/build/browser/integration outputs below; QA screenshots; truthful setup failure and unrun full suite recorded. |
| 29 | Frontend-only F010 diff; same API clients/contracts, no F010 backend/role/migration. |
| 30 | Plus opens existing Documents with retained File/project; /chat body still only message/model_id. |
| 31 | Suggestion fills/focuses draft with chat POST count zero. |
| 32 | Menu chỉ Settings/Logout; AuthUser.id/display_name unchanged, không Admin Panel/role inference. |

## Ảnh QA và giới hạn

Mock: `specs/assets/F010-chat-workspace-approved.png`.
Ảnh thực tế dưới `logs/f010/` (gitignored, không commit test output):
chat-desktop, chat-streaming, chat-completed, chat-citations, projects-desktop,
documents-desktop, settings-desktop, controls-desktop, sidebar-collapsed,
chat-375/chat-1024 và viewport-W-H cho 1920×1080, 1366×768, 1280×605,
1024×600, 768×1024, 375×812, 320×568, 640×360 @2.

Tên/model/project trong ảnh là test fixtures; runtime lấy từ API/session thực.
Ảnh chỉ là bằng chứng QA, không ảnh nền giả lập ứng dụng. Accessibility kiểm tra
focus/keyboard/geometry/contrast/reduced-motion; chưa có chứng nhận screen reader.
Scope feature chủ đích để deferred: Notes/Search/Library/Folders/saved history,
Project CRUD/membership và chat Controls params thiếu API. Không fake success;
các mục này không phải task F010 chưa làm. Không deploy/commit tự động.
