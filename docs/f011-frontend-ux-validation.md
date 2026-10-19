# F011 — Báo cáo triển khai và kiểm chứng

Ngày: 2026-10-13. Trạng thái: hoàn tất F011-001 đến F011-009.
Phạm vi: frontend và consumer của API hiện hữu. Không sửa production backend,
migration, auth contracts hoặc dữ liệu phát triển. Giữ các thay đổi F009/F010
đang có trong worktree. Không chạy, sửa hoặc import runtime từ references.

## Kết quả sử dụng

- Workspace ghép ba bộ quản lý Chat/Documents/LLM theo phiên đăng nhập.
- Composer tự tăng chiều cao, giữ Enter/Shift+Enter/IME; Stop giữ partial text.
- Retry thay thế cùng lượt bằng question/model snapshot; đổi model cần xác nhận.
- Markdown render khi stream: heading/list/quote/table/link/code, copy/collapse.
- Raw HTML/images/embeds là text đã escape. Link chỉ absolute HTTP/HTTPS.
- Người đọc phía trên giữ vị trí; xuống cuối khôi phục follow output.
- Plus mở upload trong Chat. Một form/File input được giữ giữa dialog và Documents.
- Search xác nhận query rồi tìm readable passages qua API thật; có safe errors.
- Nguồn completed mở metadata panel; technical IDs/hash/offset thu gọn.
- Ba locale, native dialog/focus return, keyboard/touch và responsive được giữ.

Stop chỉ kết thúc nhận output phía browser. Không hứa hủy job provider.
Mỗi câu hỏi/retry vẫn độc lập; reload xóa chat trong RAM. Upload không tạo riêng
attachment context. Citation chat chưa có đoạn trích/page/preview/download;
Search không thay nguồn gốc và không giả score/latest revision/pagination.

## File production/configuration và trách nhiệm

Các đường dẫn dưới frontend/src/ trừ khi ghi rõ.

| File | Hàm/thành phần chính, input → output | Mục đích và lý do |
| --- | --- | --- |
| lib/pages/WorkspacePage.svelte | User/CSRF → session-local owners/views; clearSession/dispose/selectView/newChat. | Chỉ giữ phối hợp/view/focus. Invalidate owners trước khi App unmount. CSRF snapshot dùng untrack vì workspace keyed theo user/CSRF. |
| lib/features/chat/chat-state.svelte.ts | createChatState; submit/stop/retry/reset/dispose; draft/model → SSE turns. | Mỗi request có sequence và AbortController. Stop/retry/New Chat không để callback/finally cũ ghi đè hoặc unlock thao tác mới. Retry snapshot và model validation, không dựng multi-turn history. |
| lib/features/chat/chat-turn.ts | ChatTurn thêm modelId và stopped. | Ghi model của lượt và phân biệt user Stop với lỗi mạng. |
| lib/features/chat/chat-api.ts | Export isCitation; streamChat giữ input/events. | Reuse validator thật cho retrieval DTO, không copy logic hoặc đổi chat payload/provider boundary. |
| lib/features/chat/ChatPage.svelte | Turns/locks/callbacks → welcome/conversation/composer. | Nối Stop/retry và model locks vào view hiện hữu. |
| lib/features/chat/ChatComposer.svelte | Draft → auto-grow; handleInputKeydown; send/stop/plus. | Giữ plain textarea/IME; giới hạn 180px, overflow bên trong; Stop luôn là button riêng, không submit. |
| lib/features/chat/ChatConversation.svelte | Turns/visible → answer/status/actions/sources; handleScroll/toBottom. | Reading position ở view. ResizeObserver xử lý chiều cao đổi sau Markdown frame; follow output không kéo user đang đọc phía trên. |
| lib/features/chat/markdown.ts | tokenize/safeLink; model text → tokens/allowed URL. | marked lexer và HTTP(S) allowlist; không sinh HTML. Cấm relative/protocol-relative/data/file/javascript/blob links. |
| lib/features/chat/AnswerContent.svelte | Content → escaped token components, cập nhật theo animation frame. | Renderer subset có partial fences/tables, cleanup scheduler. Không HTML insertion, ảnh từ model hoặc citation mapping suy đoán. |
| lib/features/chat/CodeBlock.svelte | Code/language → copy/collapse/scroll region. | Copy đúng code; keyboard cuộn nội dung dài. Local compiler-ignore chỉ cho tabindex của vùng cuộn có accessible label. |
| lib/features/chat/copy.ts | copyText → clipboard và success/error toast. | Dùng Toaster active duy nhất; phản hồi copy đổi theo locale, unsubscribe khi dismiss/replacement; không fake copied khi clipboard bị từ chối. |
| lib/features/chat/CitationSources.svelte | Completed citations → count/list/source dialog. | Giữ thứ tự, escaped title và source selectors; metadata gốc, không fetch blob/content. |
| lib/shared/SurfaceDialog.svelte | Open/title/snippet → native modal, key trap/focus return. | Dùng chung cho upload/source; Escape dừng ở bề mặt trên cùng và trả focus về trigger. |
| lib/shared/SourceDetails.svelte | Citation/text optional → source/version/excerpt/technical details. | Hai caller thực: chat metadata và Search result. Chỉ Search có text API trả; không suy excerpt chat. |
| lib/features/documents/documents-state.svelte.ts | createDocumentsState; loadProjects/submitUpload/refreshUploadStatus/search/dispose. | Giữ File/metadata/poll qua navigation; sequence/disposed guards; poll 2s/5min; Search abort/invalidate response cũ theo query/phiên. |
| lib/features/documents/documents-api.ts | retrieveDocuments(query, signal) → validated chunk/text/citation array. | Cookie, query/limit 10; không ACL/client scope. Kiểm tra shape và matching chunk/document IDs; lỗi JSON/malformed payload giữ safe message. |
| lib/features/documents/DocumentSearchPage.svelte | Documents state → confirm/search/status/results/keyboard/details. | Không search theo mỗi phím; không total/score/page fake; text escape, Arrow/Home/End điều hướng kết quả. |
| lib/features/documents/UploadSurface.svelte | Open/inline target/snippet → một form mounted. | Di chuyển DOM của form giữa inline target và native dialog, không remount/clone File input; giữ state và không duplicate IDs/request owners. |
| lib/features/llm/llm-state.svelte.ts | createLlmState; initialize/reloadModels/chooseModel/save/disconnect/dispose. | Một confirmed catalog, init idempotent, locks và late-response guard; giữ omission/delete/new-key/URL-change/fallback, clear secret khi dispose. |
| lib/features/llm/LlmConnectionForm.svelte | LLM state/locks → fields/actions/status. | Presentational form, không tự bootstrap hoặc giữ API owner. Close/reopen Settings không làm mất save/catalog. |
| lib/i18n/locales/vi-VN/translation.json | Labels/safe UiMessage keys → tiếng Việt. | Thêm keys F011, giữ keys/placeholder/plurals cũ. |
| lib/i18n/locales/en-US/translation.json | Labels/safe UiMessage keys → English. | Cùng logical key set, English fallback hiện hữu. |
| lib/i18n/locales/ru-RU/translation.json | Labels/safe UiMessage keys → tiếng Nga. | Cùng logical key set, xử lý text dài qua responsive/QA. |
| frontend/package.json | Thêm marked 18.1.1 pinned. | Một lexer cần thiết; không thêm sanitizer vì mọi token render qua Svelte escaping và không có HTML insertion. |
| frontend/package-lock.json | marked lock; source-map-js 1.2.2 patch. | npm audit đã báo advisory của transitive source-map-js 1.2.1. Update patch trong graph hiện có; audit cuối 0 vulnerabilities. |
| README.md | Mô tả UX/state/contract và browser entry point. | Lệnh runnable chỉ ở README. Làm rõ Stop/retry/Search/upload/sources và deferred backend. |

## Nguồn references đã thích nghi

| Nguồn references/src/lib/components/ | Hành vi port/tham khảo | Thích nghi và phần không đưa sang |
| --- | --- | --- |
| chat/MessageInput.svelte::inOrNearComposition, keydown | IME, auto-grow, stop/send hierarchy. | Plain textarea/cookie API active; không Tiptap/voice/tools/legacy token. |
| chat/Messages/Markdown.svelte::parseTokens/updateHandler | Parse trong streaming, gộp update theo frame. | marked token components, cancellation khi unmount; không raw HTML/artifacts/embeds. |
| chat/Messages/Markdown/MarkdownTokens.svelte | Heading/list/table/link/code structure. | HTTP(S) allowlist, escaped leaves, không SourceToken mapping giả. |
| chat/Messages/CodeBlock.svelte::copyCode/collapseCodeBlock | Copy/collapse/code toolbar. | Native clipboard và active toast; không editor/run-code/Python/HTML preview. |
| chat/Messages/ResponseMessage.svelte::copyToClipboard/regenerateResponse | Actions của answer. | Retry độc lập trên cùng lượt; không persisted branch/edit/delete. |
| chat/Chat.svelte::scrollToBottom/autoScroll | Follow output và xuống cuối khi đọc phía trên. | Ngưỡng active 80px, một scroll owner, ResizeObserver cho async renderer. |
| layout/SearchModal.svelte::searchHandler/onKeyDown | Search/results/keyboard/detail layout. | Passage API, query sau xác nhận; không history APIs/pagination/dedup revision giả. |
| chat/Messages/Citations.svelte::showSourceModal | Chip/list/source surface. | Metadata gốc và chi tiết thu gọn; không confidence percentage/file URL/page giả. |
| chat/Messages/Citations/CitationModal.svelte | Source details hierarchy. | SourceDetails dùng chung; excerpt chỉ từ retrieve response của chính kết quả Search. |
| layout/Sidebar.svelte, Sidebar/UserMenu.svelte, chat/SettingsModal.svelte | Shell/Settings/account UX F010 được giữ. | Không framework migration, global legacy stores hoặc advanced provider parameters. |
| common/Modal.svelte::handleKeyDown/isTopModal | Focus/Escape/return và background protection. | Native dialog active; không dependency modal mới. |

Các component mới port hành vi và cấu trúc thích hợp, không import code runtime
từ references. Source paths và invariant active là đầu vào của spec/triển khai;
legacy auth, client-selected scope và direct file URLs không trở thành contract.

## Kiểm chứng thực tế

Baseline trước F011: frontend 34 tests pass, 0 fail.

| Kiểm tra | Kết quả cuối | Hành vi có bằng chứng |
| --- | --- | --- |
| npm test | 40 pass, 0 fail, 0 skip | API/auth/i18n, owners, Stop/retry snapshots, old/new search response, LLM init/failed saves, malformed retrieve và Markdown/link policy. |
| npm run build | Pass, không compiler warnings | 281 modules; build artifact cục bộ, không commit dist. |
| node tests/frontend-ux-browser.mjs | 49 checks pass | Safe Markdown/table/code/blocked HTML/images/link, completed gate, Stop/retry, copy success/failure/locale update, collapsed code, source focus, single upload/File retention/status, query confirmation, locale/state, autoscroll, 8 viewports/scale2/reduced motion/logout. |
| node tests/workspace-browser.mjs | 29 checks pass | Catalog trước Settings, close/save owner, New Chat generations, Project/upload/placeholder flows, focus/keyboard/contrast và 8 viewports F010. |
| node tests/llm-browser.mjs | 66 checks pass | Bao gồm locale/upload/layout helpers; model/key/selection locks, stale responses/polling/deadline/expiry, overflow và metadata panel. |
| node tests/auth-browser.mjs | 62 checks pass | F009 auth/register/toast/layout regression giữ nguyên. |
| unittest discover: test_f004_004_authorized_retrieval.py | 2 tests pass | Database-backed readable predicate và authorized citation results. |
| unittest discover: test_f005_007_e2e.py | 5 tests pass | Disposable PostgreSQL/fake providers; Alpha/Beta session isolation; /documents/retrieve không trả document/chunk/text của account không có quyền. |
| npm audit sau patch update | 0 vulnerabilities | marked pinned và source-map-js patch trong lockfile. |

Tổng browser checks: 206. Các suite độc lập có fixtures riêng.
Không gọi 7 backend tests này là full backend suite. F011 không sửa backend.

Ban đầu E2E không chạy được vì Docker Linux engine dừng (0 tests, setup error).
Đã khởi động bằng Docker Desktop CLI và chạy lại thành công 5 tests.
Không áp dụng migration vào DB phát triển. Fixtures tự tạo/hủy container test.
Runtime backend có StarletteDeprecationWarning từ dependency hiện hữu; tests vẫn pass.

Test-first đã thấy fail ở owners/retrieve/Markdown chưa tồn tại; sau code các
behavior checks pass. Browser mới thấy fail trước renderer integration.
Sau đó test autoscroll chứng minh fail khi renderer tăng chiều cao sau frame;
ResizeObserver sửa đúng điểm này. Ảnh QA phát hiện toast copy giữ locale cũ; browser regression thấy fail, subscription theo locale sửa và tự cleanup.
Test query đang sửa chứng minh response cũ
không được công bố; guard query/sequence sửa và suite 40 tests pass.

Regression assertions cập nhật có chủ đích: IDs nằm trong technical panel; send
khi busy đổi thành Stop; upload từ plus là dialog. Giữ assertions lock/body/key/
file/citation/authorization thay vì bỏ chúng. Popover focus được chờ theo điều kiện
toggle thực, không sleep đoán thời điểm. Clipboard Windows chuẩn hóa CRLF; test
so sánh nguyên nội dung sau canonical newline, không đổi production text.

## AC/task audit

| Nhóm AC | Task | Bằng chứng |
| --- | --- | --- |
| AC-01..05, 27..28, 33 | F011-001 | Owners và unit tests; workspace/LLM browser lifecycle/locks/key isolation. |
| AC-06..09, 18 | F011-002 | Stop/retry unit và F011 browser; IME/double-submit/New Chat regressions. |
| AC-10..13, 28 | F011-003 | Markdown policy unit, F011 render/clipboard/error/overflow checks. |
| AC-14, 30, 32 | F011-004 | Red/green ResizeObserver case; top-reader/jump-latest/navigation checks. |
| AC-15..18 | F011-005 | One mounted form and retained File; upload/deadline/stale-poll browser regression. |
| AC-19..22, 25 | F011-006 | Search owner/query/shape tests, browser body/confirmation/escaping; 2+5 backend authorized fixtures. |
| AC-23..25 | F011-007 | Completed gate/source panel/revision/IDs/escaping and no blob requests. |
| AC-26..32 | F011-008 | F009/F010 regressions; keys/plurals/locales, focus/touch/contrast/viewports/scale2/reduced motion. |
| AC-33..35 | F011-009 | Build/tests, report/reuse matrix, README and roadmap backend giữ riêng. |

Ảnh QA nằm trong logs/f011/: chat-1920/1366/1280/1024/768/375/320/640.png,
search-desktop.png, search-mobile.png, upload-zoom.png.
Đã xem trực tiếp chat desktop và Search mobile để kiểm tra bố cục/chữ/overflow.
Các file ảnh/log là output kiểm tra, không commit.

## Phần cần feature backend tiếp theo

- PostgreSQL saved conversation/message/history search/folders và account ownership.
- Multi-turn context, edit/branch và generation contracts với quyền tài liệu kiểm lại.
- Authorized document library/selected-document narrowing.
- Exact citation excerpt/PDF preview/download theo immutable revision/chunk.
- Notes/Workspace CRUD, advanced Controls và tool contracts.

Các phần này vẫn ngoài F011 và không có fake endpoint, fake persistence hoặc
client authorization path. Xem roadmap trong spec F011 để lập feature tiếp theo.
