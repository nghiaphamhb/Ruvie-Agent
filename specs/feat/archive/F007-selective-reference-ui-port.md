# F007 - Port UI có chọn lọc từ references

## Goal

Đưa các phần UI phù hợp trong `references/` vào frontend của Ruvie Agent.
Bản đầu bám bố cục và hình thức của UI legacy. UI chỉ cung cấp các tính năng
đang có trong ứng dụng active. Chủ dự án có thể custom từng vùng UI sau đó.

Trong spec này, **port** là chép phần markup, style hoặc tương tác đã chọn
sang active, rồi sửa cho phù hợp với Svelte 5 và API active. Port không phải
import runtime từ `references/`. **CSS variables** là các biến dùng chung
cho màu, font, khoảng cách và kích thước của UI.

Phạm vi và kế hoạch F007-001–007 đã được chủ dự án xác nhận ngày 2026-10-07.
Chủ dự án yêu cầu viết task cụ thể để có thể triển khai bằng Goal mode.
Theo yêu cầu cập nhật ngày 2026-10-08, F007 chỉ triển khai và kiểm chứng UI desktop.
Tiến độ triển khai và bằng chứng kiểm chứng được ghi trong Tasks bên dưới.

## User Story

Là người dùng đã được cấp tài khoản, tôi muốn dùng giao diện quen thuộc của
Ruvie để đăng nhập, tải tài liệu và chat có nguồn, để sử dụng các tính năng
hiện có mà không gặp các nút cho tính năng chưa được hỗ trợ.

Là chủ dự án, tôi muốn các vùng UI và style được tách rõ, để thay đổi giao
diện theo ý thích mà không phải sửa API hoặc logic quyền tài liệu.

## Scope

### In

- Port khung sidebar/header, vùng chào, vùng hội thoại, ô nhập câu hỏi,
  nguồn tham khảo, hình thức thẻ file và các form liên quan.
- UI có ba mục điều hướng: **Chat**, **Tải tài liệu**, **Kết nối LLM**.
  Tài khoản và **Đăng xuất** là thao tác chung.
- Sau đăng nhập hoặc reload với phiên hợp lệ, mở màn hình Chat.
  Chuyển màn hình là thay đổi UI trong trang hiện tại. Không thêm router.
- Chỉ triển khai UI desktop: sidebar luôn hiển thị ở bên trái, vùng nội dung
  nằm bên phải. Không có nút menu thu gọn hoặc drawer điều hướng.
- Màn hình Chat có header, bộ chọn một model, vùng hội thoại và ô nhập.
  Màn hình Tải tài liệu có form upload và trạng thái lần upload hiện tại.
  Màn hình Kết nối LLM có form kết nối riêng đang có.
- Giữ tên Ruvie Agent, nội dung tiếng Việt và các nhãn thao tác rõ nghĩa.
  Bản đầu dùng giao diện sáng. Lấy bố cục, tỷ lệ và hình thức từ legacy;
  không đổi sang một phong cách thiết kế khác.
- Tái sử dụng code active trước. Port phần legacy tương thích cho phần còn
  thiếu. Ghi đường dẫn nguồn, phần chép và phần điều chỉnh trong spec/README.
- Giữ các API, cookie phiên, CSRF, lựa chọn model theo tài khoản và SSE active.
  Backend tiếp tục quyết định quyền tài liệu và cấu hình provider.
- Dùng CSS variables cho các giá trị cần custom. Dùng scoped styles cho
  component và CSS chung cho khung ứng dụng. Không tạo thư viện UI riêng.
- Kiểm tra hành vi cũ cùng điều hướng mới, bố cục desktop, bàn phím, nguồn,
  response của phiên cũ và sự tách biệt giữa hai tài khoản.

#### Code hiện tại

Đây là hiện trạng được đọc ngày 2026-10-07. Khi triển khai, đọc lại worktree
và giữ các thay đổi của người dùng. F006 mở rộng contract chat của F004.
Không dùng giới hạn model cũ của F004 để thay contract F006 đang chạy.

| File/hàm active | Code đang làm | Khoảng trống cần giải quyết |
|---|---|---|
| `frontend/src/App.svelte`: `submitLogin`, `signOut`, `clearSession` | Đăng nhập, đăng xuất, giữ user/CSRF; xóa chat/catalog khi kết thúc phiên. | Form và header chưa nằm trong khung UI legacy. Cần giữ việc xóa state khi tách component. |
| `App.svelte`: `loadProjects`, `submitUpload`, `refreshUploadStatus` | Lấy project, gửi metadata/file và hỏi trạng thái mỗi 2 giây, tối đa 5 phút. | Form upload đang nằm trên hội thoại. Cần đưa sang màn hình riêng và kiểm tra response trễ khi đổi phiên. |
| `App.svelte`: `submit`, `handleInputKeydown`, `handleScroll`, `scrollToLatest` | Gửi một câu hỏi/model, ghép SSE, hiển thị lỗi/nguồn, xử lý IME và tự cuộn khi người dùng đang ở cuối. | Markup chat và nguồn nằm chung trong App. Cần port bố cục và giữ state khi chuyển màn hình. |
| `frontend/src/lib/components/LlmConnectionForm.svelte`: `reload`, `run`, `save`, `disconnect` | Tải kết nối/catalog khi mount, giữ/xóa key đúng contract, khóa thao tác và bỏ response sau unmount. | Form chiếm vùng trên hội thoại. Nếu chỉ mount khi mở màn hình LLM thì catalog không tự tải lúc vào Chat. |
| `frontend/src/lib/components/ModelSelector.svelte`: `toggleOpen`, `pick`, `handleKeydown` | Chọn một model, tìm theo tên/ID, tick, keyboard và native popover. | Đã thích nghi legacy ở F006. Chỉ cần đổi hình thức/vị trí và kiểm tra lại focus/popover. |
| `frontend/src/lib/auth-api.ts`, `documents-api.ts`, `llm-api.ts`, `chat-api.ts` | Gọi API active bằng cookie cùng origin; giữ payload, xử lý lỗi và SSE. | Tái sử dụng. Không thay bằng API/token/provider calls legacy. |
| `frontend/tests/llm-browser.mjs`, `frontend/tests/llm-e2e.mjs` | Có browser harness dùng API giả và E2E dùng API active. | Tests đang giả định form upload/LLM và chat cùng hiển thị. Cần điều hướng trước thao tác, giữ toàn bộ assertion nghiệp vụ. |

#### Phần legacy đã khảo sát

Các đường dẫn trong bảng là đường dẫn đầy đủ từ repository root.
Chỉ dùng những phần được ghi ở cột port. Không chép cả file lớn để rồi ẩn
những chức năng chưa có. Không sửa hoặc chạy `references/`.

| Nguồn legacy | Phần cần port | Phần phải điều chỉnh hoặc bỏ |
|---|---|---|
| `references/src/lib/components/layout/Sidebar.svelte` | Cấu trúc điều hướng bên trái, vị trí brand/tài khoản, trạng thái mục đang chọn. | Bỏ chat history, folders, pin, notes, channels, workspace, search và các API/stores đi kèm; bỏ Sortable/UUID. Sidebar không biểu diễn ACL hoặc scope retrieval. |
| `references/src/lib/components/chat/Navbar.svelte` | Header gọn và vị trí bộ chọn model. | Bỏ share, archive, download chat và multi-model; dùng callback/state active, không dùng `$app/navigation`. |
| `references/src/lib/components/chat/Placeholder.svelte` | Bố cục vùng chào và ô nhập khi chưa có lượt chat. | Bỏ folder, suggestions từ provider, tools, skills và Markdown/DOMPurify chỉ dùng cho các phần đó. |
| `references/src/lib/components/chat/MessageInput.svelte` | Khung ô nhập, hình thức nút gửi, loading/disabled và ý tưởng tránh gửi lúc IME xác nhận ký tự. | Giữ textarea và `handleInputKeydown` active; bỏ rich-text editor, voice, ảnh, tools, file đính kèm vào chat, hàng đợi và stop/continue/regenerate. |
| `references/src/lib/components/chat/Messages/Citations.svelte` | Nút thu gọn số nguồn, danh sách tên nguồn và thứ tự nguồn. | Dùng `Citation[]` active; bỏ embed URL, favicon bên ngoài, relevance/distance, gộp nguồn legacy và fetch nội dung file. |
| `references/src/lib/components/common/FileItem.svelte` | Thẻ file với tên, loại/kích thước và dấu đang xử lý. | Dùng file người dùng chọn và trạng thái revision active; bỏ mở URL `/files/.../content`, preview, sửa/xóa file và modal nội dung. |
| `references/src/routes/auth/+page.svelte` | Bố cục form email/mật khẩu và submit/loading. | Chỉ có đăng nhập bằng tài khoản được cấp; giữ `auth-api.ts`; bỏ signup, OAuth/LDAP và `localStorage.token`. |
| `references/src/lib/components/AddConnectionModal.svelte`: `verifyOpenAIHandler`, `submitHandler`; `references/src/lib/components/chat/Settings/Connections.svelte`: `updateHandler` | Hình thức URL/key, trạng thái kiểm tra và lưu. | Giữ form/logic F006; bỏ direct-provider call, custom headers, Azure/Ollama riêng và nhiều connection. |
| `references/src/lib/components/chat/ModelSelector/Selector.svelte`: `toggleOpen`, `handleKeydown`, `filteredItems` | Hình thức trigger, tìm kiếm và mục có tick. | Giữ selector active đã port; bỏ Fuse/dayjs, pin/tags và quản lý tải/xóa model. |
| `references/src/app.css` | Tham khảo font, khoảng cách và hình thức bề mặt cần cho các vùng đã chọn. | Không chép toàn bộ CSS/Tailwind hoặc font assets không dùng; biến style chuyển vào CSS active. |

Chủ dự án không yêu cầu kiểm tra license riêng cho source được cung cấp
trong `references/`. Thiếu `LICENSE` không chặn việc port này.

#### Contract phải giữ

UI chỉ gọi các API active sau. F007 không thêm endpoint hoặc migration.

| Thao tác | Input | Output/hành vi cần giữ |
|---|---|---|
| `GET /auth/session` | Cookie phiên. | User và CSRF, hoặc `401` để hiển thị đăng nhập. |
| `POST /auth/login` | `{email, password}`. | Phiên hợp lệ, user và CSRF. Sai thông tin trả lỗi an toàn. |
| `POST /auth/logout` | Cookie và `X-CSRF-Token`. | `204`; UI xóa dữ liệu phiên và trở về đăng nhập. |
| `GET /projects` | Cookie phiên. | `{items: [{id, code, name}]}` do backend cấp. |
| `POST /documents/upload` | Multipart: `project_id`, `title`, `software`, `software_version`, `file`; cookie/CSRF. | `202` với `document_id`, `revision_id`, `job_id`, `status: pending`. Project ở đây là đích upload, không phải scope chat. |
| `GET /documents/revisions/{revision_id}/status` | Revision ID từ kết quả upload và cookie. | `pending`, `running`, `ready`, `failed` cùng `error_code` an toàn hoặc lỗi không tiết lộ tài liệu. |
| `GET /llm/connection`, `GET /models` | Cookie phiên. | Metadata không có key; catalog và trạng thái lựa chọn model. |
| `PUT /llm/connection` | `base_url`, `api_key` tùy chọn; cookie/CSRF. | Chỉ lưu kết nối hợp lệ; lỗi giữ kết nối đã lưu trước đó. |
| `DELETE /llm/connection` | Cookie/CSRF. | `204`; tải lại cấu hình dự phòng. |
| `PATCH /llm/connection/model` | `{model_id}`; cookie/CSRF. | Lựa chọn đã xác nhận; lỗi giữ lựa chọn cũ. |
| `POST /chat` | `{message, model_id}` bằng client hiện có. | SSE `delta` → `citations` nếu có → `completed`, hoặc lỗi. Không gửi history, URL/key, project ID, document ID hoặc scope. |

Nguồn active gồm `citation_id`, `document_id`, `revision_id`, `chunk_id`,
`ordinal`, `start_offset`, `end_offset`, `title`, `source_hash`, `software`
và `software_version`. UI không có nội dung đoạn trích, URL blob hoặc điểm
liên quan từ contract này. Không tạo các dữ liệu đó để giống legacy.

### Out

- Phiên bản mobile, drawer điều hướng, breakpoint cho điện thoại, xử lý
  bàn phím ảo/safe-area và kiểm thử bố cục hoặc tương tác chạm trên mobile.
- Lưu, tìm kiếm, chia sẻ, pin, archive hoặc đồng bộ lịch sử chat.
  Không thêm nút **Chat mới** trong F007.
- Truyền lịch sử cho LLM, sửa câu hỏi, regenerate, continue hoặc stop qua UI.
- Thư viện tài liệu, cây thư mục, danh sách mọi revision, preview/download,
  sửa/xóa tài liệu hoặc chọn tài liệu làm scope chat.
- Multi-model, nhiều connection, nhập model tùy ý, tải/xóa model.
- Voice, ảnh, tools, skills, web search, notes, tickets, automation và admin.
- Signup, quên mật khẩu, OAuth/LDAP/SSO và quản lý tài khoản.
- Dark-mode toggle, màn hình cấu hình theme, UI builder hoặc plugin theme.
  Chủ dự án custom bằng code/CSS variables ở giai đoạn sau.
- Chuyển sang SvelteKit, thêm Tailwind hoặc kéo package/store/API legacy vào.
  Không thêm runtime dependency chỉ để tái tạo hình thức UI.
- Sửa backend, schema, ingestion, embedding profile, ACL hoặc blob storage.
- Truy cập database dev/provider thật; chạy hoặc sửa legacy; xử lý task F005
  đang mở hoặc các thay đổi không thuộc F007.

## Flow

1. UI kiểm tra phiên qua `getAuthSession()`. Trong lúc chờ, hiển thị trạng
   thái kiểm tra; chưa hiển thị dữ liệu tài khoản hoặc các form được bảo vệ.
2. Không có phiên thì hiển thị form đăng nhập. Người dùng nhập email/mật khẩu.
   `submitLogin()` dùng `auth-api.ts`, nhận user/CSRF rồi mở màn hình Chat.
3. App tải project và kết nối/model của tài khoản. Catalog vẫn được tải khi
   màn hình Kết nối LLM chưa được mở. Thiếu kết nối/model thì Chat có hướng
   dẫn mở **Kết nối LLM**, và khóa gửi cho tới khi có model hợp lệ.
4. Người dùng chuyển giữa ba màn hình bằng sidebar. Chuyển màn hình không
   xóa draft, chat, trạng thái upload hoặc catalog. Không gọi lại API chỉ vì
   đổi màn hình. Mỗi form vẫn có nút tải lại theo hành vi active.
5. Trên Tải tài liệu, người dùng chọn project do backend trả về, nhập metadata,
   chọn PDF/text và gửi. UI hiển thị thẻ file và trạng thái. Polling tiếp tục
   khi người dùng chuyển sang Chat. UI không báo phần trăm tiến độ giả.
6. Trên Kết nối LLM, người dùng dùng form F006. Thành công cập nhật catalog
   chung. Quay lại Chat có thể chọn model đã xác nhận. Lỗi không tự đổi provider.
7. Trên Chat, người dùng nhập câu hỏi và gửi. App gọi `streamChat()` với
   message/model. Người dùng có thể đổi màn hình khi đang stream; kết quả
   tiếp tục cập nhật. Model/kết nối vẫn khóa trong thời gian chat.
8. Chat hiển thị text đang nhận và trạng thái. Khi hoàn tất, UI hiển thị nguồn
   do backend trả về. Người dùng mở số nguồn, rồi xem metadata của từng nguồn.
   UI không tìm thêm nội dung từ URL hoặc ID trong metadata.
9. Khi người dùng cuộn lên để đọc, delta mới không kéo họ về cuối. Khi họ đang
   ở cuối, UI theo output. Việc chuyển màn hình không làm mất vị trí đọc.
10. Đăng xuất thành công hoặc nhận `401` từ API được bảo vệ thì App kết thúc
    phiên. App hủy chat, dừng theo dõi upload, xóa dữ liệu UI/key đang nhập
    và trở về đăng nhập. Response của phiên cũ không cập nhật phiên mới.
11. Reload làm mất chat/draft/upload trong bộ nhớ trang. Phiên và model/kết
    nối đã lưu vẫn được tải lại từ backend. Màn hình mặc định là Chat.

### Cấu trúc UI đề xuất

Cấu trúc dưới đây là kế hoạch đã chốt. Trạng thái từng component nằm trong Tasks.
Giữ API clients và hai component LLM active đang có.

```text
App.svelte
  ├─ LoginForm.svelte                      khi chưa đăng nhập
  └─ khung ứng dụng                        khi có phiên
       ├─ AppNavigation.svelte             sidebar desktop
       ├─ header và ModelSelector.svelte   model chỉ trong màn hình Chat
       ├─ ChatConversation.svelte          vùng chào/lượt chat
       │    └─ CitationSources.svelte      danh sách/metadata nguồn
       ├─ ChatComposer.svelte              draft/Enter/IME/gửi
       ├─ DocumentUploadPanel.svelte       form/thẻ file/trạng thái
       └─ LlmConnectionForm.svelte         form F006
```

- `App.svelte` giữ user, CSRF, `sessionSequence`, màn hình đang chọn, draft,
  turns, catalog và các cờ busy. App giữ các hàm gọi API và `AbortController`.
- `DocumentUploadPanel` nhận state/giá trị form từ App và trả callback cập nhật
  hoặc submit/refresh. App giữ upload sequence và polling. Thẻ file nằm trong
  panel; không tạo một hệ thống file chung.
- `ChatComposer` nhận draft/disabled và callback đổi draft/gửi. Nó giữ xử lý
  bàn phím/IME hiện có. `ChatConversation` nhận turns, giữ DOM cuộn và logic
  theo output. `CitationSources` chỉ nhận `Citation[]` và trình bày dữ liệu.
- `LoginForm` nhận loading/lỗi và callback `onlogin(email, password)`.
  Nó giữ giá trị input; xóa password sau thành công hoặc khi bị tháo khỏi DOM.
- Trong cùng phiên, giữ các panel đã mount và dùng `hidden` cho panel không
  được chọn. Panel ẩn không nhận Tab hoặc xuất hiện trong accessibility tree.
  Không đặt CSS khiến `hidden` mất tác dụng. Giữ key theo `authUser.id +
  csrfToken` quanh phần UI có dữ liệu phiên để reset component khi đổi phiên.
- `LlmConnectionForm` vẫn mount một lần cho mỗi phiên kể cả khi bị ẩn.
  `onmodelschange`, `onbusychange`, `onexpired` vẫn nối tới App. Không chuyển
  logic tải catalog sang điều hướng hoặc tạo bản sao state model.
- Chuyển màn hình khi đang có tác vụ không tháo component hoặc hủy request.
  Sidebar desktop luôn hiển thị; state nghiệp vụ không nằm trong sidebar.
- CSS variables ở `frontend/src/app.css` giữ các tên đang có như `--paper`,
  `--surface`, `--ink`, `--muted`, `--border`, `--accent`, `--accent-hover`,
  `--soft`. Thêm biến font, màu lỗi, khoảng cách, bo góc, chiều rộng sidebar
  và nội dung khi chúng được dùng. Component dùng biến chung cho giá trị theme.

## Edge Cases

- Phiên kiểm tra chậm hoặc login sai: có loading/lỗi tại form; không submit
  lặp, không hiển thị UI của tài khoản trước.
- Không có project: Tải tài liệu hiển thị **Bạn chưa tham gia project nào**;
  không có project giả hoặc nút upload khả dụng. Lỗi tải có nút thử lại.
- File thiếu, metadata thiếu hoặc chưa chọn project: không gửi upload.
  Giữ giới hạn PDF/text UTF-8, tối đa 25 MiB theo UI/API active.
- Upload đang xử lý: form khóa; đổi màn hình không tạo upload thứ hai hoặc
  vòng polling thứ hai. `ready`/`failed` dừng polling. Hết 5 phút có thao tác
  làm mới trạng thái; job ở server vẫn tiếp tục.
- Upload/status trả `404`: báo thông tin chung về project/tài liệu không truy
  cập được; không suy ra tài liệu tồn tại. `401` kết thúc phiên.
- Logout, đổi tài khoản hoặc component bị tháo khi upload/status đang chờ:
  dùng sequence của tác vụ và phiên để bỏ response cũ, kể cả nhánh lỗi/finally.
- Chưa có kết nối, catalog rỗng hoặc model đã mất: khóa gửi, giải thích và
  cho mở kết nối hoặc tải lại/chọn lại model. Không tự gửi model khác.
- Kết nối/lưu model đang chờ: khóa gửi và các thao tác xung đột. Đổi màn hình
  không mở khóa các nút đang phải khóa.
- Key giữ/xóa/URL đổi: giữ đúng F006. Key đã lưu không điền lại vào input,
  không ghi localStorage hoặc log; key đang nhập bị xóa khi kết thúc phiên.
- SSE lỗi giữa chừng: giữ text đã nhận, hiển thị lỗi an toàn và bỏ nguồn của
  lượt thất bại. Không hiện trạng thái hoàn tất hoặc nguồn chưa được xác nhận.
- Nguồn rỗng: không có nút **0 nguồn**. Cùng tài liệu nhưng khác revision/chunk
  vẫn giữ từng citation; không gộp mất identity hoặc thứ tự backend trả về.
- Text giống HTML trong answer/title/metadata: hiển thị như text, không chạy
  HTML/JavaScript. Không thêm `{@html}` hoặc Markdown renderer trong F007.
- Tên tài liệu/model dài hoặc nguồn có nhiều ID: wrap/cuộn trong vùng phù hợp;
  không tạo tràn ngang toàn trang hoặc cắt mất khả năng xem metadata.
- Chọn mục trên sidebar: đưa focus tới tiêu đề màn hình mới. Đóng popover
  model trước khi ẩn Chat; focus không nằm trong panel đã ẩn.
- Đổi kích thước cửa sổ desktop: sidebar và các thao tác vẫn truy cập được;
  không có overlay điều hướng chặn nội dung.
- Màn hình desktop thấp, zoom 200% hoặc reduced motion: vùng nội dung và
  composer vẫn truy cập được; không phụ thuộc animation để hiểu trạng thái.

## Acceptance Criteria

- [x] AC-01: UI đăng nhập và khung ứng dụng dùng hình thức được port từ các
      nguồn trong bảng. Có ghi phần chép/điều chỉnh; không chỉ thay tên/màu
      UI cũ hoặc nhập toàn bộ subsystem legacy.
- [x] AC-02: Khi có phiên, ba mục Chat/Tải tài liệu/Kết nối LLM hoạt động;
      mục hiện tại có trạng thái rõ. Không có control cho các tính năng Out.
- [x] AC-03: Login sai có lỗi an toàn; login đúng mở Chat; logout/`401` xóa
      dữ liệu phiên. Response trễ của tài khoản A không xuất hiện ở B.
- [x] AC-04: Catalog tự tải khi vào Chat mà chưa mở Kết nối LLM. Đổi màn
      hình không tạo lại GET kết nối/catalog, không xóa draft/chat/model.
- [x] AC-05: Upload chỉ nhận project từ danh sách backend và metadata/file
      theo contract active. Có trạng thái pending/running/ready/failed,
      timeout/làm mới và lỗi; đổi màn hình không dừng hoặc nhân đôi polling.
- [x] AC-06: Chọn model B rồi gửi thì payload chat chỉ có message và ID B.
      Lỗi lưu giữ model cũ; model mất khóa gửi. Quy tắc key/fallback F006 giữ nguyên.
- [x] AC-07: Enter gửi một lần; Shift+Enter xuống dòng; xác nhận IME không
      gửi. Delta hiện dần; lỗi và hoàn tất có trạng thái đúng. Đổi màn hình
      trong stream rồi trở lại vẫn thấy kết quả của cùng lượt chat.
- [x] AC-08: Khi đang đọc phía trên, stream không kéo xuống cuối. Khi đang
      ở cuối, stream theo output. Vị trí đọc giữ sau khi chuyển màn hình.
- [x] AC-09: Nguồn chỉ xuất hiện ở lượt hoàn tất có citations. Mở/đóng và
      xem đủ metadata của từng citation; không có preview, điểm liên quan,
      favicon ngoài hoặc request đọc blob/content tự thêm.
- [x] AC-10: Reload xóa lịch sử chat trong trang nhưng tải lại phiên và
      model/kết nối đã lưu. Không ghi chat, key, tài liệu hoặc scope vào localStorage.
- [x] AC-11: Với viewport desktop 1280×720 và 1024×600, Chat/composer/nguồn,
      form upload/LLM đều truy cập được; không tràn ngang toàn trang. Zoom
      200% vẫn thao tác được. Upload/LLM không chiếm vùng trên hội thoại.
- [x] AC-12: Sidebar desktop và model picker thao tác được bằng bàn phím;
      Escape đóng picker và trả focus đúng; đổi mục đặt focus vào màn hình mới.
      Input có label; nút icon có tên; trạng thái/lỗi đọc được; vùng ẩn không
      nhận focus. Focus nhìn thấy và text thường có contrast ít nhất 4.5:1.
- [x] AC-13: Đổi CSS variables thay màu/font/khoảng cách/bo góc ở các vùng
      đã port mà không phải sửa API/business logic. Không thêm runtime dependency.
- [x] AC-14: Frontend tests/build, browser API giả và E2E hai tài khoản với
      API active đều đạt. Hai tài khoản vẫn chỉ nhận nguồn/provider/model
      riêng. Có kết quả thực tế; skip không được ghi là pass.
- [x] AC-15: Không sửa/chạy/import runtime `references/`, không dùng directory
      `archive`, không đổi backend/schema/ACL/storage. Không đưa source legacy
      không liên quan, secrets, log, screenshot hoặc dist vào thay đổi cần commit.

## Tasks

### Quy tắc triển khai bằng Goal mode

- Spec và kế hoạch F007 đã được xác nhận. Spec này không tự kích hoạt Goal
  hoặc cấp yêu cầu triển khai. Khi chủ dự án yêu cầu triển khai F007 bằng Goal
  mode, thực hiện các task theo thứ tự dưới đây trong cùng phạm vi đã chốt.
- Không yêu cầu xác nhận lại giữa các task cho việc đổi tên component,
  vị trí CSS hoặc cập nhật locator test nằm trong kế hoạch này. Nếu cần đổi
  API, quyền, dữ liệu hoặc thêm tính năng Out, báo khác biệt và xin xác nhận
  trước phần thay đổi đó; tiếp tục phần độc lập đã được phép.
- Trước mỗi task, đọc file active và nguồn legacy liên quan. Dùng tests hiện
  có trước; thêm test hành vi có ý nghĩa cho tương tác mới trước implementation.
  Không tạo test chỉ khớp tên class hoặc sao chép logic implementation.
- Các đường dẫn component đề xuất nằm trong `frontend/src/lib/components/`.
  Các task được phép sửa `App.svelte`, `app.css` và browser tests liên quan.
  Không reset, stage hoặc commit các thay đổi của người dùng ngoài task.
- Lệnh chạy chuẩn và cấu hình công cụ lấy từ README: **Tests**, **Browser to
  backend integration**. Ghi hướng dẫn mới vào README, không tạo cách chạy
  thứ hai trong spec. Tests dùng API/provider giả và PostgreSQL dùng một lần.
- Chỉ tick task khi đủ điều kiện Done. Ghi bằng chứng dưới task: file đã đổi,
  phần legacy đã port, lệnh đã chạy, pass/fail/skip và giới hạn chưa kiểm chứng.
  Nếu thiếu browser/Docker, giữ task kiểm chứng liên quan chưa tick.
- Khi chạy toàn bộ F007, Goal chỉ hoàn tất sau F007-007 và tất cả AC có bằng
  chứng đạt. Khi chỉ được giao một task, dừng sau Done của task đó.

- [x] **F007-001 — Chốt đối chiếu source, state và baseline.**
  - **Phụ thuộc:** Không có. Phạm vi đã được xác nhận.
  - **Work:**
    1. Đọc `README.md`, `AGENTS.md`, F007 và trạng thái Git. Đọc lại các file
       active/legacy trong bảng; loại trừ `archive` không phân biệt hoa thường.
    2. Kiểm tra contract và luồng login → catalog → chat; upload → status;
       logout/`401` → clear state. Ghi nơi đang giữ state và callback cần giữ.
    3. Xác định các đoạn markup/style thực sự sẽ chép, dependency phải bỏ và
       phần active thay thế. Cập nhật bảng nguồn trong F007 bằng phát hiện mới
       trong phạm vi đã chốt; không tạo một spec hoặc kế hoạch xin duyệt khác.
    4. Chạy baseline frontend tests/build/browser API giả theo README trước
       khi sửa UI. Ghi failure/skip sẵn có riêng để không gán cho F007.
    5. Chốt mapping task → component → AC/test. Dùng sơ đồ component trong
       Flow; không tạo thêm layer/service/store chung chỉ để port UI.
  - **Where:** Spec này; đọc `frontend/src/App.svelte`, các API clients,
    `LlmConnectionForm.svelte`, `ModelSelector.svelte`, tests và bảng legacy.
    Chưa sửa production trong task này.
  - **Done:** Có bảng nguồn/state/dependency dùng được để code F007-002–006;
    có kết quả baseline thực tế hoặc lý do không chạy được. Không còn giả định
    rằng active có chat history, document library hoặc file-content API.
  - **Bằng chứng 2026-10-08:** Đã đối chiếu bảng nguồn và state trong Flow.
    Baseline frontend: 18 tests pass, 0 fail, 0 skip; build 117 modules đạt.
    Browser baseline thất bại tại assertion cuộn catalog dài trước sửa UI.
    Browser cần chờ danh sách lọc cập nhật trước ArrowUp; không bỏ assertion cuộn.
    Đã dùng Node được cung cấp bởi môi trường vì npm không có trong PATH.


- [x] **F007-002 — Port khung ứng dụng và điều hướng.**
  - **Phụ thuộc:** F007-001. **AC:** 02, 04, 11, 12, 15.
  - **Work:**
    1. Thêm browser checks cho mặc định Chat, ba mục điều hướng, giữ draft/state
       khi chuyển mục và GET catalog lúc form LLM còn ẩn. Cho tests bắt lỗi trước
       khi thêm khung UI.
    2. Tạo `AppNavigation.svelte` từ cấu trúc điều hướng đã chọn trong legacy.
       Props gồm mục hiện tại, tên tài khoản, trạng thái logout và callbacks
       đổi mục/logout. Không có state đóng/mở điều hướng.
    3. Thêm state `activeView: 'chat' | 'documents' | 'llm'` trong App, mặc
       định `chat`. Callback `selectView(view)` đổi vùng hiển thị và focus.
       Không gắn project/document vào state này để làm scope retrieval.
    4. Port header/sidebar desktop. Sidebar luôn hiển thị bên trái; các mục
       dùng được bằng Tab và Enter/Space. Mục hiện tại có trạng thái rõ;
       chọn mục thì focus vào tiêu đề màn hình mới. Không thêm breakpoint
       thu sidebar, nút menu hoặc drawer.
    5. Bọc các vùng hiện có bằng panel `hidden`; giữ chúng mount trong cùng
       phiên. Form LLM giữ key theo user/CSRF và callbacks tải catalog.
       Đổi kích thước cửa sổ desktop không thay state nghiệp vụ hoặc điều hướng.
    6. Đổi màn hình vẫn cho phép upload/stream tiếp tục. Giữ các cờ busy do
       App quản lý; không dùng chuyển mục để hủy tác vụ. Đóng popover
       model trước khi ẩn màn hình Chat; không để overlay nhận focus ở màn hình khác.
    7. Cập nhật helper/locator browser hiện có ngay khi panel bị ẩn: mở mục
       LLM trước thao tác form, quay về Chat trước gửi/chọn model. Các task sau
       tiếp tục cập nhật locator khi đổi markup; không chờ F007-005 để sửa
       các test bị ảnh hưởng bởi điều hướng của task này.
  - **Where:** Tạo `AppNavigation.svelte`; sửa `frontend/src/App.svelte`,
    `frontend/src/app.css`, `frontend/tests/llm-browser.mjs` và
    `frontend/tests/llm-e2e.mjs` cho helper điều hướng. Chỉ sửa
    `ModelSelector.svelte` nếu cần đóng popover khi đổi màn hình. Port từ
    `layout/Sidebar.svelte` và `chat/Navbar.svelte`.
  - **Done:** Có đúng ba mục, brand/tài khoản/logout; các panel ẩn không nhận
    Tab. Chat tải model trước khi mở LLM. Chuyển mục không tạo GET mới, mất
    draft hoặc khởi động lại tác vụ. Browser checks điều hướng và frontend
    tests/build đạt; không có dependency hoặc runtime import legacy.
  - **Bằng chứng 2026-10-08:** `AppNavigation.svelte` port brand/nav/account
    của `layout/Sidebar.svelte`. App giữ ba panel mount bằng `hidden`,
    focus heading và model ở header từ `chat/Navbar.svelte`.
    Browser kiểm tra mặc định Chat, draft/catalog không mất, keyboard sidebar,
    focus và đóng picker khi rời Chat; tác vụ chat/LLM tiếp tục qua điều hướng.
    Đã cập nhật helper điều hướng trong hai browser scripts, giữ assertions F006.
    Frontend unit 18 pass/0 fail/0 skip; build 125 modules đạt; API giả 18 nhóm đạt.


- [x] **F007-003 — Port hội thoại, composer và nguồn.**
  - **Phụ thuộc:** F007-002. **AC:** 01, 06–09, 11, 12, 15.
  - **Work:**
    1. Bổ sung browser fixtures SSE có delta, citations, completed và lỗi giữa
       chừng. Thêm checks cho Enter/Shift+Enter/IME, giữ scroll và chuyển mục
       trong stream. Dùng event/điều kiện chờ; tránh sleep dài để ép test pass.
    2. Tạo `ChatConversation.svelte` nhận turns và `CitationSources.svelte`
       nhận citations. Port markup vùng chào/hội thoại/nguồn đã chọn; giữ
       question/answer/status/error từ `ChatTurn` active, không thêm chat API.
    3. Giữ một kiểu `ChatTurn` dùng chung nếu props cần type. Chỉ tách kiểu
       sang file nhỏ khi cần; không tạo repository/state framework frontend.
    4. Tạo `ChatComposer.svelte` nhận draft, disabled và callbacks input/submit.
       Di chuyển logic IME/keyboard từ App; Enter chỉ submit một lần, Shift+Enter
       xuống dòng. Dùng textarea; giữ draft trong App khi chuyển màn hình.
    5. App giữ `submit`, `streamChat`, sequence và AbortController. Các cờ
       busy/llmBusy/modelBusy/authBusy, catalog hợp lệ và draft rỗng tiếp tục
       quyết định gửi. Model selector đặt ở header màn hình Chat theo Navbar.
    6. Trong conversation, giữ logic `handleScroll`/`scrollToLatest` và ngưỡng
       gần cuối 80 px. Delta chỉ theo output khi đang ở cuối; panel ẩn không
       tính lại vị trí cuộn theo kích thước 0. Khi hiện lại, giữ vị trí đọc hoặc
       theo output nếu người dùng đã ở cuối trước khi rời màn hình.
    7. Nguồn có control thu gọn số nguồn và từng mục có tên/thứ tự. Chi tiết
       trình bày đủ fields của `Citation`; có thể dùng `<details>` hiện có.
       Dùng `citation_id` cho identity; không gộp mất revision/chunk hoặc fetch
       metadata/content khác. Chỉ render sources của lượt completed.
    8. Dùng text interpolation cho answer/title/metadata. Giữ text khi SSE lỗi,
       hiển thị lỗi và bỏ nguồn của lượt đó. Không thêm Markdown/HTML/preview.
  - **Where:** Tạo `ChatConversation.svelte`, `ChatComposer.svelte`,
    `CitationSources.svelte`; sửa App/CSS và `frontend/tests/llm-browser.mjs`.
    Giữ `frontend/src/lib/chat-api.ts`. Port từ `chat/Placeholder.svelte`,
    `chat/MessageInput.svelte`, `chat/Messages/Citations.svelte`.
  - **Done:** Lượt chat giữ payload/SSE cũ; B gửi đúng B. Có delta/loading/lỗi,
    IME và scroll đúng; quay lại Chat thấy cùng lượt. Nguồn mở được bằng bàn
    phím, metadata đủ, không có request blob. Frontend tests/build và các
    browser checks mới đạt; locator đã đổi vẫn giữ assertion nguồn F006.
  - **Bằng chứng 2026-10-08:** Đã tạo `ChatConversation.svelte`,
    `ChatComposer.svelte`, `CitationSources.svelte`, type chung `chat-turn.ts`.
    Port vùng chào căn giữa từ Placeholder, nút gửi tròn/arrow-up từ MessageInput,
    pill số nguồn và tên có thứ tự từ Citations. Giữ text interpolation và API active.
    Test nguồn có thứ tự và citation_id đã đỏ trước sửa. Test tự theo output
    khi gửi lượt mới từ vị trí đọc phía trên đã đỏ, rồi đạt sau sửa.
    Fixture HTTP SSE có gates cho delta/citations/completed/error kiểm tra stream
    thật, cuộn/đổi panel, giữ text lỗi và bỏ nguồn lỗi. Có IME/Enter/Shift+Enter,
    nguồn qua keyboard và đủ metadata, HTML title là text. App giữ payload/model/
    AbortController/sequence; component chỉ giữ DOM và tương tác.
    Frontend unit 18 pass/0 fail/0 skip; build 125 modules đạt; API giả 18 nhóm đạt.
    Đã chạy bằng Node runtime các script tương đương `npm test`, `npm run build`
    và `node tests/llm-browser.mjs` vì npm không có trong PATH.


- [x] **F007-004 — Port upload và trạng thái sang màn hình riêng.**
  - **Phụ thuộc:** F007-003. **AC:** 03, 05, 11, 12, 15.
  - **Work:**
    1. Thêm browser fake routes `/projects`, `/documents/upload` và revision
       status để kiểm tra form/metadata, pending → running → ready, failed,
       status lỗi, timeout/làm mới và response trễ sau logout. Dùng clock của
       browser/test để tiến thời gian qua deadline; không chờ thật 5 phút hoặc
       giảm deadline production cho test. Fixture kiểm tra không có status GET
       mới sau ready/failed hoặc sau khi phiên đã kết thúc.
    2. Tạo `DocumentUploadPanel.svelte` nhận project/loading/error, các giá trị
       input/file, upload/status state và callbacks đổi input/submit/refresh/
       tải project. Giữ hàm API, polling và sequence trong App.
    3. Chuyển form hiện có vào panel, giữ fields bắt buộc và giới hạn độ dài.
       Hiển thị tên/loại/kích thước file đang chọn theo hình thức `FileItem`.
       Không biến thẻ file thành link preview/download hoặc một thư viện file.
    4. Giữ multipart/cookie/CSRF bằng `uploadDocument()`. Chỉ cho chọn project
       được trả về; backend vẫn xác minh membership. Không thêm client ACL.
    5. Giữ polling 2 giây, deadline 5 phút và thao tác làm mới. Hiển thị trạng
       thái bằng text, loading icon chỉ khi đang chờ/đang xử lý. Không thêm
       phần trăm hoặc cơ chế retry-ingestion mà API chưa cung cấp.
    6. Trước mỗi response upload/status, nhánh catch và finally, kiểm tra tác
       vụ/phiên còn hiện hành. Logout/`401` vô hiệu sequence và dừng polling;
       response trễ không đặt uploadBusy/error/status của phiên mới. Xóa
       metadata và file người dùng chọn khi kết thúc phiên.
    7. Chuyển màn hình trong upload vẫn giữ file/metadata/status. Chỉ một submit
       và một vòng polling cho tác vụ hiện tại; khóa submit lặp và refresh lặp.
  - **Where:** Tạo `DocumentUploadPanel.svelte`; sửa App/CSS và browser fixtures
    trong `frontend/tests/llm-browser.mjs`. Giữ `documents-api.ts` và các tests
    payload hiện có. Port phần thẻ của `common/FileItem.svelte`.
  - **Done:** Form hiện đầy đủ trên Tải tài liệu, không nằm trên Chat. Fixture
    ghi nhận đúng multipart/CSRF và các trạng thái/error/timeout/làm mới.
    Chuyển mục không dừng hoặc nhân đôi tác vụ; logout/đổi user không có
    state từ response cũ. Frontend tests/build và browser checks upload đạt.
  - **Bằng chứng 2026-10-08:** Đã tạo `DocumentUploadPanel.svelte` với bindings
    metadata/file, props project/status và callbacks submit/refresh/reload.
    Port khung thẻ file, glyph tài liệu, tên/loại/kích thước và loading từ FileItem;
    không port click/content URL. App giữ multipart, polling 2 giây/deadline 5 phút.
    Tests đã đỏ tại thẻ file, metadata sau logout, finally cũ mở khóa upload mới
    và submit không khóa khi refresh; các lỗi này đã sửa và đạt.
    `upload-browser.mjs` tách fixture riêng để giữ script dễ đọc, được gọi bởi
    `llm-browser.mjs` nên không thêm lệnh chạy. Browser clock kiểm tra deadline
    mà không đổi timeout production. Có ready/failed/status lỗi/404/refresh,
    stale upload/poll/refresh và 401 hiện hành; kiểm tra dừng GET sau terminal/logout.
    Frontend unit 18 pass/0 fail/0 skip; build 127 modules đạt; API giả 26 nhóm đạt.


- [x] **F007-005 — Đồng bộ form đăng nhập, kết nối và bộ chọn model.**
  - **Phụ thuộc:** F007-004. **AC:** 01, 03, 04, 06, 10–12, 15.
  - **Work:**
    1. Tạo `LoginForm.svelte` cho input/loading/lỗi bằng bố cục login legacy.
       App giữ `submitLogin`, gọi `login()` và xử lý session. Form chuyển
       email/password qua callback; không chuyển auth sang token/localStorage.
    2. Restyle `LlmConnectionForm.svelte` từ phần form legacy đã chọn. Giữ
       `reload/run/save/disconnect`, các callbacks và fieldset locks; giữ Base
       URL/key tùy chọn, giữ/xóa key, gỡ kết nối và tải lại. Không thêm modal
       nhiều connection hoặc nút verify gọi provider trực tiếp.
    3. Restyle `ModelSelector.svelte` dựa trên Selector legacy. Giữ search
       chuỗi, tick, một model, `pick/handleKeydown`, vị trí native popover và
       focus. Không thêm pin/tags/model management hoặc dependency dropdown.
    4. Thêm control **Kết nối LLM** từ Chat khi catalog chưa khả dụng; control
       chỉ đổi màn hình. Lỗi connection/model hiển thị tại form/control liên
       quan và có cách tải lại/chọn lại. Không dùng control này để tự lưu.
    5. Cập nhật `frontend/tests/llm-browser.mjs` và `llm-e2e.mjs`: mở màn hình
       LLM trước URL/key, quay về Chat trước chọn model/gửi bằng sidebar desktop.
       Thay locator layout cũ bằng role/label của UI mới. Chuyển các checks
       nghiệp vụ ở viewport nhỏ sang viewport desktop; bỏ yêu cầu kiểm tra
       layout điện thoại. Giữ assertions model/key/nguồn/phiên của các checks đó.
    6. Giữ checks login, chọn B, reload, key trống, lỗi lưu/refresh, model mất,
       loading locks, response cũ, logout/hết phiên và hai user. Không bỏ test
       chỉ vì form hoặc nguồn đã chuyển vị trí.
  - **Where:** Tạo `LoginForm.svelte`; sửa App, hai component LLM/CSS,
    `frontend/tests/llm-form.test.mjs`, `llm-browser.mjs`, `llm-e2e.mjs` khi
    markup/props cần thay đổi. Giữ auth/LLM API clients.
    Port từ `routes/auth/+page.svelte`, `AddConnectionModal.svelte`,
    `chat/Settings/Connections.svelte`, `chat/ModelSelector/Selector.svelte`.
  - **Done:** Login và cả hai control LLM có cùng hình thức UI đã port; catalog
    vẫn tải khi form ẩn. Không lộ/lưu browser key; B/lỗi/fallback/reload/session
    giữ contract F006. Frontend tests/build và browser API giả đạt. E2E script
    đã được điều chỉnh; kiểm chứng API active thực hiện ở F007-007.
  - **Bằng chứng 2026-10-08:** Đã tạo `LoginForm.svelte`, giữ credentials trong
    component và cookie/CSRF trong App; bỏ password sau thành công/unmount.
    Port form gọn có label từ auth page, restyle URL/key theo AddConnectionModal,
    picker/search/tick rows theo Selector. Giữ toàn bộ run/save/reload/disconnect.
    Chat chưa có model có control mở LLM, không tự lưu hoặc gọi provider.
    Test đã đỏ tại login input chưa khóa, control kết nối chưa có, logout lỗi
    chưa hiển thị và logout 401 chưa clear; đã sửa và đạt. Tests key/model/
    fallback/reload/session F006 giữ nguyên. E2E helper dùng sidebar desktop.
    Frontend unit 18 pass/0 fail/0 skip; build 129 modules đạt; API giả 28 nhóm đạt.


- [x] **F007-006 — Hoàn thiện CSS variables và bố cục/accessibility desktop.**
  - **Phụ thuộc:** F007-005. **AC:** 01, 11–13, 15.
  - **Work:**
    1. Rà lại CSS của các vùng đã port. Đưa màu/font/spacing/radius và kích
       thước khung cần custom vào `:root`. Giữ tên biến active đang được dùng.
       Không đưa geometry riêng của popover hoặc mọi giá trị CSS vào config.
    2. Dùng scoped styles cho component, CSS chung cho reset/khung/theme.
       Bỏ style cũ không còn caller của F007; không dọn CSS ngoài phạm vi.
    3. Kiểm tra desktop 1280×720 và desktop thấp 1024×600.
       Chỉ vùng nội dung cần cuộn; composer/nguồn/form vẫn truy cập được.
       Dùng kích thước linh hoạt và wrap cho text dài; sidebar luôn hiển thị.
    4. Kiểm tra zoom 200%, sidebar/picker bằng keyboard, focus và vùng hidden.
       Label input, tên nút icon, `aria-current` cho điều hướng, `aria-expanded`
       cho picker/nguồn, `role=status`/`role=alert` phản ánh trạng thái thực tế.
    5. Đảm bảo focus nhìn thấy, contrast text thường 4.5:1 và reduced motion.
       Không dùng màu hoặc hover làm dấu hiệu duy nhất.
    6. Thử đổi các biến màu/font/spacing/radius bằng browser để xác nhận cả
       sidebar/chat/upload/LLM nhận thay đổi. Hoàn nguyên giá trị thử. Ghi
       tên biến và component cần sửa cho từng loại custom trong README.
  - **Where:** `frontend/src/app.css`, scoped styles trong các component F007,
    `frontend/tests/llm-browser.mjs`, `README.md`. Tham khảo phần CSS cần dùng
    trong `references/src/app.css`; không chép stylesheet/assets toàn bộ.
  - **Done:** Các viewport/zoom/focus/hidden và text dài đạt kiểm tra browser;
    không tràn ngang toàn trang. Theme thay bằng biến đã ghi mà không sửa API.
    UI vẫn bám reference; frontend tests/build/browser đạt, không dependency mới.
  - **Bằng chứng 2026-10-08:** Chuyển styles vùng UI vào từng component;
    CSS global giữ reset/frame/theme. Port paper gradient và màu sáng từ
    `references/src/app.css`, dùng system font, không chép font assets.
    Có variables màu/font/spacing/radius/width trong README. Browser thay biến
    và xác minh cả sidebar/chat/upload/LLM đổi hình thức, rồi hoàn nguyên.
    `layout-browser.mjs` kiểm tra 1280×720, 1024×600 và bố cục tương đương
    zoom 200%: 640×360 CSS px với deviceScaleFactor=2, browser desktop.
    Có tên model/tài khoản/file/title/hash dài, mở nguồn bằng click bình thường,
    cuộn metadata và composer; không tràn ngang hoặc cuộn toàn trang.
    Đã sửa header quá cao do model dài, giữ tên đầy đủ trong tooltip/list;
    conversation không bị co về 0 px khi zoom, panel cuộn để truy cập composer.
    Source-count giữ pill như legacy. Focus keyboard, Tab bỏ panel hidden,
    Escape trả focus, contrast các cặp theme ≥4.5:1 và reduced-motion đều đạt.
    Đã xem screenshots desktop/upload/LLM/zoom/source trong logs (ignored).
    Frontend unit 18 pass/0 fail/0 skip; build 129 modules đạt; API giả 40 nhóm đạt.


- [x] **F007-007 — Kiểm chứng toàn luồng và ghi bàn giao.**
  - **Phụ thuộc:** F007-006. **AC:** Toàn bộ AC-01–15.
  - **Work:**
    1. Chạy frontend suite/build và browser API giả theo README. Browser suite
       phải bao gồm điều hướng, upload/status, streaming/nguồn, model/key,
       desktop/keyboard và response trễ. Không chỉ chạy screenshot smoke test.
    2. Build UI mới rồi chạy backend suite theo README với browser tools và
       Docker sẵn có. Dùng `tests/test_f006_008_browser_e2e.py`,
       `frontend/tests/llm-e2e.mjs` và fixture PostgreSQL/provider giả F005.
       Không tạo database hoặc provider connection dev cho F007.
    3. E2E phải xác nhận A đăng nhập → mở LLM/kết nối → chọn B → chat có nguồn
       A → reload vẫn B; B có model/key/nguồn riêng trên desktop; đăng nhập lại
       A vẫn B. Cấu hình backend, provider requests và checks isolation cũ giữ nguyên.
    4. Chỉ chỉnh fixture/locator test nếu UI mới cần. Không nới assertion hoặc
       thay API active bằng mock trong E2E. Thiếu điều kiện thì ghi skip và
       để AC-14/task này mở; không suy từ API giả rằng E2E đã đạt.
    5. Kiểm tra diff: không runtime import từ references, legacy endpoints/
       tokens, request provider từ browser, control Out, runtime dependency,
       thay đổi backend/schema hoặc generated files. Kiểm tra whitespace.
    6. README tiếng Anh mô tả phạm vi desktop, ba màn hình, giới hạn chat/upload,
       cách custom
       CSS/component, nguồn legacy đã dùng và hướng dẫn chạy browser mới.
       Ghi lệnh mới tại README nếu thực sự cần; ưu tiên harness hiện có.
    7. Ghi kết quả từng task và AC trong F007. Báo các file production/config
       đã đổi, nguồn đã port, khác biệt contract đã loại bỏ và pass/fail/skip
       thực tế. Chỉ tick các mục có bằng chứng; không tick task feature khác.
  - **Where:** `README.md`, spec F007, browser tests hiện có; chỉ điều chỉnh
    `tests/test_f006_008_browser_e2e.py` nếu setup test cần cho UI mới.
    Không sửa production backend hoặc migration.
  - **Done:** Suites/build/browser/E2E bắt buộc đạt; mỗi AC có bằng chứng.
    Có hướng dẫn custom và nguồn port chính xác. UI active chạy độc lập với
    references, không mất các assertion nghiệp vụ/authorization F005/F006.
    Diff chỉ có thay đổi thuộc F007 và không ghi nhận artifact/log/secrets.


### Bằng chứng bàn giao F007-007 — 2026-10-08

- Frontend: Node runtime v24.19.0 chạy script trực tiếp vì npm không có trong
  PATH. Các lệnh Node fallback đã được ghi trong README, cùng browser paths.
  `--experimental-strip-types --test tests/*.test.mjs`: 18 pass, 0 fail, 0 skip.
  `node_modules/vite/bin/vite.js build`: đạt, 129 modules, không warning Svelte.
  `tests/llm-browser.mjs`: 40 nhóm kiểm tra đạt, 0 fail, không skip.
- Backend: `.venv/Scripts/python.exe -m unittest discover -s tests`:
  138 tests, OK, 0 fail, 0 error, 0 skip (106.013 giây ở lần cuối chạy full).
  Suite được kiểm tra có test browser E2E bắt buộc trong 138 test được discover.
  Sau sửa CSS vùng đọc ở zoom, chạy lại đúng build cuối bằng
  `.venv/Scripts/python.exe -m unittest discover -s tests -p test_f006_008_browser_e2e.py -v`:
  1 test, OK, 0 fail/error/skip, 32.822 giây.
- E2E dùng Docker Linux, PostgreSQL/pgvector dùng một lần và fake provider.
  Test xác nhận hai tài khoản, model B lưu/reload/login lại cho A, model/key
  riêng của B, nguồn riêng và provider payload không chứa dữ liệu tài khoản khác.
  Không dùng database/provider dev. Backend có Starlette deprecation warning
  sẵn có về httpx; warning không làm test fail và không đổi dependency trong F007.
- `git diff --check` đạt. Whitespace của file mới được kiểm tra riêng và đạt.
  Git status của `references`, `backend`, `tests`, `frontend/dist`, `logs` không
  có thay đổi cần commit do F007. Package/lock/config không thêm dependency.
  Các thay đổi F006/.env.example có sẵn được giữ nguyên, không reset/stage/commit.
- README tiếng Anh có phạm vi desktop, hành vi reload/chat/upload, bảng custom
  CSS/component, nguồn port và các lệnh chạy. Screenshot chỉ nằm trong logs ignored.

| AC | Bằng chứng hiện hành |
| --- | --- |
| 01 | Bảng nguồn trong Scope/README; component comments và screenshots đã xem: sidebar/header, welcome/composer, pill nguồn, file card, login/LLM. |
| 02 | `llm-browser.mjs`: mặc định Chat và ba mục; `AppNavigation.items` chỉ có ba view, account/logout riêng. Không có control Out trong markup active. |
| 03 | Login sai/loading, logout lỗi/401; fixtures trễ project/model/upload/poll/refresh; guard task/session và reset metadata/file; E2E hai tài khoản. |
| 04 | Catalog tải khi form LLM ẩn; đổi view giữ draft/model và không tăng GET catalog. Panels hidden vẫn mount, không tạo request qua selectView. |
| 05 | `upload-browser.mjs`: project backend, multipart/CSRF/metadata/file; pending/running/ready/failed, 404/status lỗi/deadline/refresh; không nhân đôi hoặc tiếp tục GET sau terminal/logout. |
| 06 | Tests F006 giữ nguyên: chọn B gửi B, lỗi giữ model cũ, model mất khóa gửi, key giữ/xóa/URL đổi, fallback. E2E kiểm tra provider model/key thực nhận. |
| 07 | Fixture HTTP SSE có gates; Enter/Shift+Enter/IME; stream qua điều hướng; completed và lỗi giữ text, bỏ nguồn lỗi. |
| 08 | Delta khi đọc phía trên giữ scroll; ở cuối theo output; hidden panel không dùng geometry 0; quay lại giữ vị trí; gửi lượt mới theo câu trả lời mới. |
| 09 | Keyboard/native details; citation_id và toàn bộ metadata; số thứ tự/pill; HTML title/answer là text; sources dài trên cả ba viewport; mở nguồn không có request files/documents/retrieval/content. |
| 10 | Reload kiểm tra turns/draft/metadata/file/status bị xóa; model/kết nối trở lại từ backend; localStorage rỗng và key input rỗng. E2E login lại A vẫn B. |
| 11 | Desktop 1280×720, 1024×600 và zoom-equivalent 640×360 CSS px @2x; thao tác nguồn/composer/form, text dài, chỉ region scroll; không tràn ngang. |
| 12 | Sidebar Enter/Space, focus heading có outline; Tab không vào panel hidden; picker search/tick/Escape trả focus; nguồn qua Enter; label/status/alert, contrast ≥4.5:1 và animation reduced-motion. |
| 13 | Thay/hoàn nguyên variables: padding/radius/sidebar/chat/upload/LLM, font và màu selected row; scoped styles; README bảng custom; package dependencies không đổi. |
| 14 | Frontend 18 tests + build + browser 40 nhóm; backend 138 tests; E2E hai tài khoản chạy lại trên build cuối đạt 1 test; 0 skip. |
| 15 | Diff/status kiểm tra: không sửa/chạy/import runtime references, không dùng archive, không sửa backend/schema/ACL/storage; không dependency/secrets/artifacts mới cần commit. |

F007-001–007 và AC-01–15 đã đủ bằng chứng đạt. UI active chạy độc lập với
references. Chủ dự án có thể custom CSS variables hoặc scoped styles theo README.
