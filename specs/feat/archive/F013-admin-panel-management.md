# F013 - Cập nhật Admin Panel của Ruvie Agent

> Cập nhật giao diện (2026-10-25): sản phẩm chỉ hỗ trợ desktop; các bố cục,
> drawer và kiểm thử riêng cho mobile được loại bỏ. Admin Panel và hai trang
> Settings vẫn giữ sidebar chính, cùng khung cài đặt desktop.

> Bổ sung F013-011: cột Last active dùng hiện diện theo phiên đăng nhập, tách
> khỏi `is_active`. Hai modal Create account và Edit User dùng cùng thứ tự
> Name, Email, Role, Password; ô nhập có viền, footer căn phải và nút chính rõ ràng.

## Goal

Trả ngày tạo tài khoản trong dữ liệu quản trị. Tạo khung Admin Panel trong vùng nội dung của workspace, giữ sidebar chính và cung cấp hai tab Users / Setting. Cung cấp API danh sách, tìm kiếm và phân trang để bảng Users sử dụng ở bước tiếp theo.

## User Story

Là admin, tôi muốn mở Users và Setting ngay trong workspace để quản lý tài khoản, truy cập cài đặt và quay lại chat bằng sidebar chính. Tôi muốn xem ngày tạo tài khoản để biết một tài khoản được cấp từ khi nào. Tôi muốn tìm theo tên/email và chia danh sách thành các trang để tra cứu khi có nhiều tài khoản.

## Scope

### In

- F013-011: Heartbeat 30 giây ở tab đang hiển thị, 60 giây ở tab nền; Online
  khi ít nhất một session hợp lệ có heartbeat trong 180 giây. Users làm mới mỗi
  15 giây khi hiển thị. Giữ last active sau logout, không nhận ID/thời gian từ client.

- Bổ sung `created_at` vào dữ liệu tài khoản trong response tạo tài khoản và tra cứu email.
- Chuẩn hóa thời điểm trả về thành ISO 8601 có múi giờ và giữ lại trường này trong frontend.
- Thêm kiểm tra backend/frontend cho response hợp lệ và thời điểm không có múi giờ từ SQLite.
- F013-002: Thêm thanh điều hướng Users / Setting vào Admin Panel trong `WorkspaceShell` hiện có.
- Tab Users dùng lại `AccountsPanel`; tab Cài đặt hệ thống chỉ hiển thị LLM connection. Menu tài khoản > Cài đặt mở trang Giao diện nhúng trong workspace cho cả admin và user thường; giữ sidebar chính, không mở modal và không có mục LLM. Giữ nguyên hợp đồng API và phạm vi lưu LLM theo tài khoản hiện tại.
- Lưu tab chính trong query `view=admin-users` hoặc `view=admin-settings`. Hỗ trợ mở URL trực tiếp, reload, Back/Forward và bàn phím.
- F013-004: Thêm `GET /admin/users/list?q=&page=1&page_size=20` cho admin. Giữ nguyên `GET /admin/users?email=...` để tra cứu email chính xác.
- Danh sách gồm tài khoản đang hoạt động và bị vô hiệu hóa, tìm chuỗi con không phân biệt hoa/thường trong tên hoặc email, sắp xếp `created_at DESC, id ASC` và trả tổng số kết quả sau lọc.

### Out

- Hiển thị ngày trong bảng Users hoặc modal Edit User; thuộc task giao diện sau.
- Giao diện bảng Users và state tìm kiếm/phân trang; thuộc F013-005.
- Migration hoặc thay đổi cách lưu `users.created_at`.
- API quản trị ngoài danh sách Users, cài đặt toàn hệ thống, chuyển cài đặt LLM cá nhân thành cài đặt toàn cục.
- Thay đổi dữ liệu các form cài đặt hoặc viết chi tiết các task F013-005 đến F013-010.
- Thay đổi thuật toán tra cứu email chính xác, cho client chọn cột sắp xếp hoặc lọc theo quyền tài liệu.

## Flow

1. Backend đọc `User.created_at` từ PostgreSQL khi tạo tài khoản hoặc tra cứu tài khoản.
2. `AdminAccountSummary` xác thực timestamp có múi giờ và tuần tự hóa nó thành ISO 8601.
3. Frontend xác thực response, giữ `created_at` trong `AccountSummary` và chuyển dữ liệu cho state quản trị.
4. Admin chọn Quản trị trong menu tài khoản. `WorkspacePage.selectView` đọc lại session từ server trước khi mở Users.
5. Admin chọn Users hoặc Setting. Workspace cập nhật URL và tab được chọn; sidebar chính và các state chat, tài liệu, LLM vẫn cùng chủ sở hữu.
6. Cài đặt hệ thống nhúng `SettingsPanel` với mục LLM connection duy nhất. Menu tài khoản > Cài đặt điều hướng tới `view=settings`, nhúng cùng bố cục với mục Giao diện duy nhất. Hai trang giữ sidebar và owner của state workspace; Back/Forward, reload và URL trực tiếp hoạt động.
7. Người dùng chọn sidebar để rời Admin. Backend tiếp tục kiểm tra quyền cho mọi API quản trị; query URL chỉ chọn giao diện.
8. Client gọi API danh sách với `q` tối đa 255 ký tự sau bỏ khoảng trắng hai đầu, `page` từ 1 đến 1.000.000, `page_size` từ 1 đến 100; mặc định lần lượt là chuỗi rỗng, 1 và 20.
9. API xác thực session và role admin; service đọc lại actor trong database trước khi chạy truy vấn. Service dùng cùng điều kiện tìm kiếm cho truy vấn đếm và truy vấn trang, trả `users`, `total`, `page`, `page_size`.
10. Mỗi user chỉ có các trường của `AdminAccountSummary`. Frontend xác thực từng user cùng metadata phân trang trước khi trả kết quả cho caller. Ví dụ trang đầu: `{"users": [], "total": 0, "page": 1, "page_size": 20}`.

## Edge Cases

- F013-011: Nhiều tab dùng chung cookie được giới hạn ghi mỗi 25 giây. Nhiều
  thiết bị được gộp bằng session hợp lệ; logout một session không tắt session khác.
- F013-011: Session hết hạn, bị thu hồi hoặc tài khoản bị vô hiệu hóa không được
  tính Online. Tài khoản cũ chưa có timestamp hiển thị Chưa hoạt động.
- F013-011: Lỗi refresh nền giữ nguyên hàng và báo Chưa cập nhật; heartbeat lỗi
  mạng được thử ở nhịp sau. Logout/đổi tài khoản hủy timer/request của workspace cũ.

- SQLite có thể trả `datetime` không kèm múi giờ trong test; contract gắn UTC trước khi tuần tự hóa.
- Frontend từ chối timestamp thiếu, sai định dạng hoặc không có múi giờ theo quy ước API.
- Tra cứu không tìm thấy tài khoản vẫn trả danh sách rỗng.
- Response chỉ thêm ngày tạo vào metadata cho phép; không đưa hash mật khẩu, session hoặc dữ liệu bí mật vào response.
- Người dùng thường mở một trong hai URL Admin: quay về chat, xóa query Admin và không mount nội dung Admin.
- Session đã hết hạn hoặc thay đổi tài khoản/CSRF: xóa workspace theo luồng hiện có. Session bị hạ quyền: rời Admin nhưng giữ phiên đăng nhập và bản nháp chat.
- Lỗi đọc session: không mở view Admin mới, hiển thị thông báo hiện có. Phản hồi điều hướng cũ không được ghi đè thao tác mới.
- Cả tài khoản thường và quản trị dùng cùng khung Settings trên desktop, giữ nguyên sidebar chính. Trang cá nhân chỉ có mục Giao diện; Cài đặt hệ thống chỉ có mục Kết nối LLM.
- Chỉ mount một bộ form cài đặt tại một thời điểm để tránh trùng ID và nhóm radio. State LLM và theme tiếp tục thuộc workspace.
- F013-004: Chuỗi tìm kiếm rỗng hoặc chỉ có khoảng trắng trả danh sách không lọc. `%`, `_` và ký tự escape được tìm như ký tự thường, không mở rộng wildcard SQL.
- Trang vượt số kết quả trả `users: []` cùng `total` sau lọc. Ngày tạo bằng nhau dùng `id ASC` để các trang có thứ tự xác định.
- Dữ liệu có thể được tạo hoặc đổi giữa hai request; phân trang offset không cam kết snapshot xuyên suốt nhiều request.
- Query không hợp lệ hoặc field lạ trả 422 với mã lỗi an toàn; không phản chiếu chuỗi query. Người chưa đăng nhập trả 401, người không phải admin trả 403; không trả metadata tài khoản.
- Lỗi database trả 503 với `account_lookup_unavailable`. Mọi response danh sách có `Cache-Control: no-store`, không tạo cookie, session hoặc ghi dữ liệu tài khoản.

## Acceptance Criteria

- [ ] Response tạo tài khoản và tra cứu tài khoản đều có `created_at` ISO 8601 với múi giờ.
- [ ] `created_at` luôn lấy từ giá trị database; request client không thể chọn giá trị này.
- [ ] Frontend giữ timestamp hợp lệ và từ chối timestamp thiếu hoặc sai định dạng.
- [ ] Giá trị SQLite không có múi giờ được tuần tự hóa như UTC.
- [ ] Tra cứu không thấy tài khoản vẫn trả `users: []`.
- [ ] Các response quản trị không lộ thông tin xác thực hoặc session.
- [x] F013-002: Admin thấy đúng hai tab Users / Setting và sidebar chính trong khung workspace.
- [x] Tab Users hiển thị `AccountsPanel` hiện tại; tab Setting hiển thị mục Kết nối LLM duy nhất, không mở dialog và không có Giao diện.
- [x] URL trực tiếp, reload và Back/Forward khôi phục đúng tab; phím mũi tên/Home/End chuyển tab và focus đúng.
- [x] Cả hai view Admin đều kiểm tra session mới; người dùng thường hoặc admin bị hạ quyền không thể mount view Admin.
- [x] Quay lại chat giữ nguyên bản nháp; đổi tab không tạo lại owner cho state chat, tài liệu hoặc LLM.
- [x] Cài đặt cá nhân dùng trang nhúng qua menu tài khoản cho cả admin và user thường; chỉ có Giao diện, không có LLM. Giao diện dùng được ở 375px và hai theme.
- [x] F013-004: Admin lấy được danh sách với `created_at`, `total`, `page` và `page_size`, gồm cả tài khoản bị vô hiệu hóa.
- [x] Tìm kiếm tên/email không phân biệt hoa/thường, bỏ khoảng trắng hai đầu và coi wildcard là ký tự thường; `total` đếm sau lọc.
- [x] Phân trang có thứ tự xác định, không trùng giữa các trang khi dữ liệu không đổi; trang vượt kết quả trả danh sách rỗng.
- [x] Query sai bị từ chối; người dùng thường, session hết hạn, actor bị hạ quyền hoặc vô hiệu hóa không đọc được danh sách.
- [x] Response và lỗi không lộ hash mật khẩu, token, CSRF hoặc lỗi SQL; không cache, không phát cookie và không thêm session.
- [x] Client mã hóa query, giữ cookie hiện tại, kiểm tra metadata phân trang và từng account; tra cứu email cũ vẫn hoạt động.
- [x] F013-006: Bút chì ở mỗi hàng Users mở modal đúng tài khoản, hiển thị avatar chữ cái đầu, ngày tạo và các trường Role/Name/Email/New Password đã điền metadata hiện tại; trường mật khẩu luôn bắt đầu rỗng.
- [x] Modal làm tối nền, khóa cuộn nền, giữ focus trong dialog, đưa focus vào Name khi mở và trả focus về nút mở khi đóng; Escape, nút đóng và click backdrop đóng modal.
- [x] Nút hiện/ẩn mật khẩu đổi loại input; đóng modal xóa bản nháp và mật khẩu; Save bị khóa đến khi API cập nhật được triển khai ở task sau.
- [x] F013-007: Save chỉ hoạt động khi Name hoặc Email khác giá trị ban đầu sau chuẩn hóa; gửi đúng các trường đã đổi; thành công cập nhật hàng hiện tại, đồng bộ tên hiển thị nếu admin sửa tài khoản của mình, hiện thông báo bản địa hóa và giữ modal mở với dữ liệu mới làm baseline.
- [x] Khi PATCH có kết quả không xác định, client không gửi lại PATCH tự động; đọc `GET /admin/users/{id}` để đối chiếu. Nếu trạng thái đọc lại khớp thay đổi yêu cầu thì đồng bộ UI; nếu không khớp/không đọc được thì giữ modal và bản nháp, báo kết quả chưa xác định để admin tự quyết định.
- [x] GET/PATCH theo ID chỉ trả metadata allowlist, xác minh admin hiện hành từ database; PATCH yêu cầu Origin + CSRF, ghi audit cùng thay đổi, không cho dữ liệu client xác thực quyền.
- [x] F013-008: PATCH theo ID chấp nhận `system_role` với đúng hai giá trị `user` và `admin`; chỉ admin hiện hành được đổi role.
- [x] Không cho hạ quyền admin đang hoạt động cuối cùng; admin bị vô hiệu hóa không được tính. Các yêu cầu đổi role đồng thời phải được tuần tự hóa để không thể hạ quyền toàn bộ admin.
- [x] Nếu admin tự hạ quyền thành user, giữ phiên đăng nhập, đóng Admin Panel, quay về chat, ẩn đường dẫn Admin và giữ bản nháp workspace.
- [x] Modal Edit User cho phép chọn Role; thay đổi role làm Save bật, lưu thành công giữ modal mở và cập nhật role/baseline/danh sách.
- [x] Nếu phản hồi PATCH tự hạ quyền bị mất, đọc lại phiên `/auth/session`; đồng bộ giao diện theo role hiện hành mà không đăng xuất hoặc gửi lại PATCH.
- [x] F013-009: New Password tùy chọn, rỗng nghĩa là giữ nguyên; giá trị mới giữ nguyên khoảng trắng và có độ dài 12–128 ký tự. Mật khẩu mới không xuất hiện trong response, lỗi hoặc audit.
- [ ] Đổi mật khẩu cập nhật hash, thu hồi mọi phiên của tài khoản đích và ghi audit trong cùng transaction. Đăng nhập đang chạy phải đồng bộ với reset để không tạo phiên mới bằng mật khẩu cũ sau khi reset hoàn tất.
- [ ] Admin reset mật khẩu người khác vẫn giữ phiên của admin; tài khoản đích phải đăng nhập lại. Admin reset mật khẩu của chính mình được đưa về màn đăng nhập sau khi server xác nhận thành công.
- [ ] Nếu response đổi mật khẩu bị mất, client không retry PATCH và không coi GET metadata là bằng chứng mật khẩu đã đổi; hiển thị kết quả chưa xác định. Nếu phiên hiện tại đã bị thu hồi, workspace chuyển về đăng nhập.
- [x] F013-010: Regression tích hợp xác nhận CRUD admin hiện có, role, admin cuối cùng, mật khẩu, audit và thu hồi phiên; kiểm tra UI qua locale vi/en/ru, sáng/tối, desktop/mobile, focus và quyền. Mọi test chạy trên database dùng riêng và provider giả.

### Điều chỉnh điều hướng cài đặt (2026-10-25)

- Đổi nhãn tab quản trị thành **Cài đặt hệ thống**, chỉ giữ **Kết nối LLM**.
- Chuyển **Giao diện** sang **Cài đặt** trong menu tài khoản. Cả admin và user thường mở trang này trong vùng nội dung chính, giữ sidebar và trạng thái chat/tài liệu/LLM.
- Thay `SettingsModal.svelte` bằng `SettingsPanel.svelte`; dùng lại `ThemeSelector`, `LanguageSelector`, owner theme và owner LLM đang có. Không chuyển cấu hình LLM theo tài khoản thành cấu hình toàn cục.
- Tham khảo `references/src/lib/components/admin/Settings.svelte` và `references/src/lib/components/chat/SettingsModal.svelte`; chỉ dùng mẫu phân chia cài đặt cá nhân/quản trị, không nhập runtime/store/auth legacy.
- Các ghi nhận F013-002/F013-003 bên dưới mô tả lần triển khai trước; hành vi hiện tại theo điều chỉnh này.

## Tasks

- [ ] F013-001 — Bổ sung Created at vào dữ liệu trả về cho frontend.
  - **Work:** Thêm trường bắt buộc `created_at` có kiểu thời điểm aware vào contract quản trị; chuẩn hóa giá trị SQLite không có múi giờ thành UTC; cập nhật kiểu dữ liệu và kiểm tra ISO 8601 ở frontend; cập nhật unit/API/E2E fixtures và kiểm thử tạo tài khoản lẫn tra cứu.
  - **Where:** `backend/ruvie/contracts/admin.py`; `frontend/src/lib/features/admin/admin-api.ts`; `tests/test_f012_003_admin_accounts.py`; `tests/test_f012_004_admin_api.py`; `tests/test_f012_005_accounts_e2e.py`; `frontend/tests/admin-api.test.mjs`; `frontend/tests/admin-state.test.mjs`; `frontend/tests/admin-browser.mjs`; `frontend/tests/admin-e2e.mjs`.
  - **Done:** Hai response trả `created_at` từ database dưới dạng ISO 8601 có múi giờ; frontend chỉ chấp nhận và giữ timestamp hợp lệ; trường hợp timestamp SQLite được chuẩn hóa UTC; test task và các kiểm tra hồi quy bắt buộc đạt.
- [x] F013-002 — Tạo khung Admin Panel với hai tab Users / Setting.
  - **Work:** Viết browser test cho điều hướng và quyền trước; thêm tab chính trong `AdminPage`; mở rộng view/query và kiểm tra session cho Setting; nhúng nội dung cài đặt hiện có với sidebar phụ; xác nhận focus, Back/Forward, state workspace và responsive; chạy test/build/lint/format check.
  - **Where:** `frontend/src/lib/pages/AdminPage.svelte`; `frontend/src/lib/pages/WorkspacePage.svelte`; `frontend/src/lib/layout/AppSidebar.svelte`; `frontend/src/lib/features/settings/SettingsModal.svelte`; `frontend/tests/admin-browser.mjs`; `frontend/tests/admin-form.test.mjs` (bổ sung `created_at` còn thiếu trong fixture response).
  - **Reuse:** Dùng lại `WorkspaceShell`, `AccountsPanel`, `SettingsModal`, state LLM và theme hiện có. Tham khảo thanh điều hướng tại `references/src/routes/(app)/admin/+layout.svelte` và sidebar cài đặt tại `references/src/lib/components/admin/Settings.svelte`; không nhập runtime, store hoặc cơ chế auth của legacy.
  - **Done:** Hai tab mở trong cùng workspace, URL và bàn phím hoạt động, Setting hiển thị sidebar phụ với form hiện có, quyền được kiểm tra trước mỗi lần điều hướng Admin, các kiểm tra frontend và browser đạt. F013-003 giữ nguyên đầu mục, chưa mở rộng nội dung trong task này.
  - **Validation (2026-10-23):** Test mới thất bại trước khi triển khai vì thiếu `#admin-tab-users`. Sau triển khai, `npm --prefix frontend test` đạt 66/66, không skip; `npm --prefix frontend run build`, `npm --prefix frontend run lint` và `npm --prefix frontend run format:check` đạt. Với Playwright và Edge đã cấu hình theo `AGENTS.md`: `node frontend/tests/admin-browser.mjs` đạt 30 nhóm; `node frontend/tests/theme-browser.mjs` đạt 10 kiểm tra; `node frontend/tests/workspace-browser.mjs` đạt 35 kiểm tra; `node frontend/tests/llm-browser.mjs` đạt 82 kiểm tra. Không đổi backend nên không chạy lại suite backend cho task này.
- [x] F013-003 — Đưa Appearance và LLM connection vào sidebar phụ của Setting.
  - **Verified (2026-10-23):** Đã triển khai cùng F013-002 trong `SettingsModal.svelte` (`embedded`, `settingsContent`) và `WorkspacePage.svelte` (`workspaceSettings`). Hai mục Appearance / LLM connection dùng lại form và state hiện có; mobile xếp sidebar phụ trên nội dung. Browser Admin đạt 30 nhóm, Theme 10, Workspace 35 và LLM 82 kiểm tra trong lần xác minh F013-002; đã xem ảnh desktop/mobile. Không cần thay đổi production code riêng cho task này.
- [x] F013-004 — Bổ sung API danh sách, tìm kiếm và phân trang Users.
  - **Work:** Viết test API/service với database kiểm thử và test client trước; thêm contract query/response; thêm service lọc/đếm/phân trang với điều kiện admin từ database; đăng ký route riêng; thêm client danh sách; kiểm tra tương thích tra cứu cũ và chạy các suite bắt buộc.
  - **Where:** `backend/ruvie/contracts/admin.py`; `backend/ruvie/services/admin.py`; `backend/ruvie/api/admin.py`; `frontend/src/lib/features/admin/admin-api.ts`; `tests/test_f013_004_admin_users.py` (mới); `frontend/tests/admin-api.test.mjs`; `frontend/tests/auth-e2e.mjs` (selector submit cũ, được người dùng duyệt bổ sung).
  - **Reuse:** Dùng `get_admin_user_id`, `AdminAccountService.require_admin`, `AdminRoute`, `AdminAccountSummary` và client HTTP hiện có. Tham khảo `get_users` ở `references/backend/ruvie/routers/users.py` và `references/backend/ruvie/models/users.py` về danh sách/tổng số/phân trang; không port auth, group, store hoặc trường user ngoài allowlist.
  - **Done:** API danh sách và client đáp ứng các acceptance criteria F013-004; endpoint tra cứu email cũ giữ contract; test PostgreSQL và suite backend đầy đủ, frontend test/build/lint/format đạt. Chưa gắn danh sách vào UI Users.
  - **Validation (2026-10-24):** Test mới đã thất bại trước triển khai vì thiếu route/contract/client. `python -B -m unittest -v test_f013_004_admin_users` đạt 7/7, gồm PostgreSQL thật. `npm --prefix frontend test` đạt 68/68, không skip khi cấu hình Playwright; `npm --prefix frontend run build`, `npm --prefix frontend run lint` và `npm --prefix frontend run format:check` đạt. Lần đầu suite backend đầy đủ chạy 255 test, có 1 failure tại `test_f009_006_registration_e2e.RegistrationPostgresTests.test_browser_register_reload_logout_and_login_against_active_backend`: selector cũ trong `frontend/tests/auth-e2e.mjs` tìm nhãn nút khác giao diện hiện tại. Sau khi được duyệt bổ sung, selector đã chuyển sang nút submit của form đăng ký và test E2E đó đạt 1/1. Suite backend đầy đủ chạy lại thành công với Docker Desktop và Playwright/Edge: `python -B -m unittest discover -s tests -p 'test_*.py' -v` đạt 255/255, không skip; test PostgreSQL F013-004 pass, Admin E2E đạt 9 nhóm.
- [x] F013-005 — Hiển thị bảng Users, cột Created at và nút bút chì.
  - **Work:** Dùng `listAccounts()` để tải trang đầu khi mở Users; bổ sung state danh sách, tổng số kết quả, loading/error và sequence guard; thêm tìm theo tên/email với debounce 300 ms và reset về trang 1 khi query đổi; thêm Previous/Next theo `page`, `page_size`, `total`; hiển thị bảng Name, Role, Email, Status, Created at và edit button; tải lại danh sách sau khi tạo thành công; xử lý empty, không có kết quả, lỗi/retry và quyền hết hạn.
  - **Where:** `frontend/src/lib/features/admin/AccountsPanel.svelte`; `frontend/src/lib/features/admin/admin-state.svelte.ts`; `frontend/src/lib/pages/AdminPage.svelte`; locale `translation.json` en-US/vi-VN/ru-RU; `frontend/tests/admin-state.test.mjs`; `frontend/tests/admin-browser.mjs`.
  - **Reuse:** Dùng `listAccounts()` từ F013-004 để xác thực query/response, `AdminApiError` và callbacks hết hạn/mất quyền, UI tokens/theme hiện có. Tham khảo bố cục bảng, tìm kiếm và pagination từ `references/src/lib/components/admin/Users/UserList.svelte`; không dùng API, auth hay pagination state legacy.
  - **Done:** Bảng hiển thị đúng dữ liệu an toàn với ngày tạo theo locale; search debounce, phân trang và tải lại sau tạo hoạt động; request cũ không thể ghi đè kết quả mới; state loading/empty/error/retry rõ ràng; edit button có nhãn truy cập và được đánh dấu sắp có cho tới F013-006; responsive 375px và hai theme; frontend/browser/build/lint/format check đạt.
  - **Validation (2026-10-24):** Regression test state mới thất bại trước triển khai vì chưa có `loadUsers`; sau triển khai `node --experimental-strip-types --test tests/admin-state.test.mjs` đạt 10/10. `npm test` đạt 69 pass, 0 fail, 1 skip do browser component test không có Playwright path trong tiến trình npm. `npm run build`, `npm run lint` và `npm run format:check` đạt. Với Playwright/Edge đã cấu hình, `node tests/admin-browser.mjs` đạt 31 nhóm, gồm tìm kiếm, phân trang và viewport 375px; các kiểm tra browser Admin trước đó giữ xác nhận hai theme.
- [x] F013-006 — Tạo modal Edit User với dữ liệu điền sẵn và nền tối.
  - **Work:** Bật nút bút chì trong mỗi hàng; mở modal cho account được chọn; điền role, display name, email, ngày tạo và avatar initials từ `AccountSummary`; giữ New Password rỗng, thêm hiện/ẩn; làm tối backdrop, khóa cuộn, quản lý focus và đóng bằng Escape/nút/backdrop; xóa draft khi unmount; giữ Save disabled đến khi task cập nhật API hoàn tất.
  - **Where:** `frontend/src/lib/features/admin/EditUserModal.svelte` (mới); `frontend/src/lib/features/admin/AccountsPanel.svelte`; locale `translation.json` en-US/vi-VN/ru-RU; `frontend/tests/admin-browser.mjs`.
  - **Reuse:** Dùng `AccountSummary` an toàn từ F013-004/005, `i18n` và CSS tokens hiện có. Tham khảo bố cục modal tại `references/src/lib/components/admin/Users/UserList/EditUserModal.svelte`; dùng contract `display_name` và timestamp ISO hiện tại, không dùng API cập nhật hoặc auth legacy.
  - **Done:** Modal hiển thị đúng user, hỗ trợ theme/responsive, đóng và trả focus đúng, không lưu mật khẩu nháp; Save chưa gửi request. Browser test chứng minh nội dung, nền tối, khóa cuộn, focus trap, đóng bằng Escape/backdrop và kiểm tra password rỗng sau mở lại.
  - **Validation (2026-10-24):** Browser test mới thất bại trên giao diện cũ vì edit button còn disabled. Sau triển khai `node tests/admin-browser.mjs` với Playwright/Edge đạt 31 nhóm, gồm focus trap, Escape/backdrop close, trả focus, password visibility/reset và nền cuộn. `npm --prefix frontend test` đạt 69 pass, 0 fail, 1 skip do browser component test không có Playwright path trong tiến trình npm. `npm --prefix frontend run build`, `npm --prefix frontend run lint` và `npm --prefix frontend run format:check` đạt.
- [x] F013-007 — Cho phép lưu thay đổi Name và Email.
  - **Work:** Bổ sung PATCH cập nhật riêng `display_name`/`email` và GET theo ID để đọc lại trạng thái; dùng lock và quyền admin đọc từ database, chuẩn hóa/kiểm tra giá trị, xử lý email trùng và audit trong transaction; kết nối API/state/modal; nút Save chỉ bật nếu thay đổi thực; khi thành công cập nhật bảng, đổi baseline để modal vẫn mở và báo toast bản địa hóa; khi mất response thì đối chiếu GET, không tự gửi lại PATCH; đồng bộ tên sidebar nếu admin sửa chính mình.
  - **Where:** `backend/ruvie/contracts/admin.py`; `backend/ruvie/services/admin.py`; `backend/ruvie/api/admin.py`; `backend/ruvie/api/security.py`; `frontend/src/lib/features/admin/admin-api.ts`; `frontend/src/lib/features/admin/admin-state.svelte.ts`; `frontend/src/lib/features/admin/EditUserModal.svelte`; `frontend/src/lib/features/admin/AccountsPanel.svelte`; `frontend/src/lib/pages/WorkspacePage.svelte`; locale `translation.json` en-US/vi-VN/ru-RU; `tests/test_f013_007_admin_update.py` (mới); `frontend/tests/admin-api.test.mjs`; `frontend/tests/admin-state.test.mjs`; `frontend/tests/admin-browser.mjs`.
  - **Reuse:** Dùng `RegisterRequest` để chuẩn hóa/kiểm tra tên và email, `AdminAccountService.require_admin`, `AdminAccountSummary`, `AdminRoute`, `verify_csrf`, `listAccounts()` và state danh sách hiện có. Legacy tham khảo `references/backend/ruvie/routers/users.py::update_user_by_id` để xác nhận hành vi cập nhật một phần và từ chối email trùng; không port legacy auth, role/password update, primary-admin policy hay model.
  - **Done:** Chỉ trường Name/Email thay đổi được gửi; giá trị không đổi đã chuẩn hóa không phát request; thành công hiện thông báo dịch theo locale, cập nhật đúng hàng/baseline và giữ modal mở; phản hồi bị mất được đối chiếu theo ID, không tự retry; API không lộ bí mật, kiểm tra quyền mới nhất, Origin/CSRF và audit; test backend/frontend/browser cùng các kiểm tra bắt buộc đạt.
  - **Validation (2026-10-24):** Backend suite chạy 259 test: 256 pass, 0 fail, 3 skip; test riêng F013-007 đạt 5/5, gồm PostgreSQL thật. Sau khi tìm thấy Playwright tại runtime dùng chung của Codex và cấu hình biến môi trường với Edge, chạy riêng ba browser E2E từng bị skip đạt 3/3, không skip (Admin E2E đạt 9 nhóm). `npm --prefix frontend test` đạt 73/73, không skip; `node frontend/tests/admin-browser.mjs` đạt 31 nhóm, gồm Save chỉ bật khi có thay đổi thực, cập nhật hàng và baseline, toast thành công, modal giữ mở và đóng/trả focus. Đã sửa selector ô tên bị khớp cả ô nút edit, mở lại modal trước kiểm tra backdrop và dùng tên fixture mới ở kiểm tra mobile trong `frontend/tests/admin-browser.mjs`; không đổi production code. Build đã đạt ở lần triển khai; lint và format check chạy lại đạt. Task hoàn tất.
- [x] F013-008 — Cho phép đổi Role, bảo vệ admin cuối cùng và xử lý tự hạ quyền.
  - **Work:** Mở rộng PATCH một phần để nhận role; tuần tự hóa thay đổi role trong PostgreSQL; từ chối hạ quyền admin hoạt động cuối cùng; ghi audit cùng transaction; bật Role trong modal và đưa role vào dirty state/payload; cập nhật danh sách sau lưu; tự rời Admin khi role của tài khoản hiện tại thành user; khi PATCH tự hạ quyền mất phản hồi, xác minh lại `/auth/session` để giữ phiên và reconcile role.
  - **Where:** `backend/ruvie/contracts/admin.py`; `backend/ruvie/services/admin.py`; `backend/ruvie/api/admin.py`; `frontend/src/lib/features/admin/admin-api.ts`; `frontend/src/lib/features/admin/admin-state.svelte.ts`; `frontend/src/lib/features/admin/EditUserModal.svelte`; `frontend/src/lib/features/admin/AccountsPanel.svelte`; `frontend/src/lib/pages/WorkspacePage.svelte`; locale `translation.json` en-US/vi-VN/ru-RU; `tests/test_f013_008_admin_roles.py` (mới); `frontend/tests/admin-api.test.mjs`; `frontend/tests/admin-state.test.mjs`; `frontend/tests/admin-browser.mjs`.
  - **Reuse:** Dùng `AdminAccountService.require_admin`, `AdminAccountSummary`, PATCH/GET theo ID, `getAuthSession`, callback mất quyền và event `ruvie:account-updated`. Tham khảo hành vi role tại `references/backend/ruvie/routers/users.py::update_user_by_id` và `references/src/lib/components/admin/Users/UserList/EditUserModal.svelte`; áp dụng chính sách active-admin cuối cùng và role database của active app, không port auth/session hay chính sách primary-admin của legacy.
  - **Done:** Chỉ role `user`/`admin` được chấp nhận; không thể hạ quyền admin hoạt động cuối cùng kể cả qua hai request đồng thời; admin inactive không ngăn hạ quyền; audit ghi cùng transaction; admin đổi role tài khoản khác thấy cập nhật; admin tự hạ quyền vẫn đăng nhập nhưng rời Admin và ẩn mục Admin; PATCH mất phản hồi được đối chiếu bằng session hiện hành; test PostgreSQL/frontend/browser và kiểm tra bắt buộc đạt.
  - **Validation (2026-10-24):** Regression test backend ban đầu xác nhận role bị contract cũ từ chối; sau khi triển khai, API SQLite đạt 4/4 và PostgreSQL concurrency đạt 1/1. Suite backend lần đầu có 1 failure do test F013-007 còn kỳ vọng `system_role` bị từ chối; sau khi được duyệt cập nhật tương thích, suite đầy đủ đạt 266/266, không skip; Admin E2E đạt 9 nhóm. Frontend test đạt 74/74, không skip khi cấu hình Playwright; Admin browser đạt 32 nhóm; build, lint và format check đạt. Task hoàn tất.
- [x] F013-009 — Cho phép admin đặt mật khẩu mới và xử lý phiên đăng nhập liên quan.
  - **Work:** Mở rộng PATCH cập nhật tài khoản với mật khẩu tùy chọn; áp dụng giới hạn mật khẩu 12–128 như đăng ký và giữ nguyên chuỗi; tuần tự hóa đăng nhập/reset bằng khóa tài khoản; cập nhật hash, xóa mọi `AuthSession` của đích và ghi audit trong transaction; mở trường trong modal; xử lý reset người khác, tự reset và response bị mất mà không thử lại hoặc xác nhận bằng GET metadata.
  - **Where:** `backend/ruvie/contracts/admin.py`; `backend/ruvie/services/admin.py`; `backend/ruvie/services/auth.py`; `backend/ruvie/api/admin.py`; `frontend/src/lib/features/admin/admin-api.ts`; `frontend/src/lib/features/admin/admin-state.svelte.ts`; `frontend/src/lib/features/admin/EditUserModal.svelte`; `frontend/src/lib/features/admin/AccountsPanel.svelte`; `frontend/src/lib/pages/WorkspacePage.svelte`; locale `translation.json` en-US/vi-VN/ru-RU; `tests/test_f013_009_admin_passwords.py` (mới); `frontend/tests/admin-api.test.mjs`; `frontend/tests/admin-state.test.mjs`; `frontend/tests/admin-browser.mjs`.
  - **Reuse:** Dùng cùng giới hạn password của `RegisterRequest`, `hash_password`, bảng `AuthSession`, `AuthService.authenticate`, PATCH hiện tại, `AdminAccountSummary`, callbacks phiên hiện có và modal đã có trường New Password. Legacy tham khảo kiểm tra mật khẩu và hash tại `references/backend/ruvie/routers/users.py::update_user_by_id`; dùng Scrypt và session DB của active app, không port auth/session runtime legacy.
  - **Done:** Admin có thể đặt mật khẩu mới cho tài khoản; mật khẩu không bao giờ đi vào response/log/audit; mọi phiên của tài khoản đích bị thu hồi cùng transaction; mật khẩu cũ không đăng nhập được và mật khẩu mới đăng nhập được; reset self kết thúc session hiện tại; response mất không retry và UI không báo thành công giả; test PostgreSQL/frontend/browser và kiểm tra bắt buộc đạt.
  - **Validation (2026-10-24):** Regression contract/API SQLite đạt 4/4: password tùy chọn và giữ khoảng trắng, kiểm tra độ dài/redaction, reset account khác và tự reset, thu hồi session, từ chối mật khẩu sai. Test PostgreSQL disposable đạt 1/1, xác nhận mật khẩu cũ không đăng nhập được, mật khẩu mới đăng nhập được, session đích bị vô hiệu hóa, session admin giữ nguyên và audit không chứa bí mật. Frontend đạt 77/77 không skip; Admin browser đạt 32 nhóm. Build, lint và format check đạt. Suite backend đầy đủ đạt 271/271, không skip; Admin E2E đạt 11 nhóm, gồm reset thành công và PATCH commit nhưng mất response (một PATCH, không GET metadata, không báo thành công giả). Task hoàn tất.
- [x] F013-010 — Kiểm thử tích hợp, hồi quy, đa ngôn ngữ và giao diện responsive.
  - **Work:** Bổ sung E2E qua UI và backend/PostgreSQL disposable cho quản trị tài khoản, đổi role, reset mật khẩu và thu hồi phiên; kiểm tra locale vi/en/ru, light/dark, desktop/mobile, focus/keyboard, quyền admin/user và các luồng response bị mất; sửa lỗi hồi quy phát hiện trong phạm vi Admin F013 rồi chạy lại các suite cần thiết.
  - **Where:** `frontend/tests/admin-e2e.mjs`; `tests/test_f013_010_admin_e2e.py` (mới); `frontend/tests/admin-browser.mjs`; `frontend/tests/i18n.test.mjs`; `specs/feat/F013-admin-panel-management.md`.
  - **Reuse:** Mở rộng harness disposable PostgreSQL và Playwright trong `tests/test_f012_005_accounts_e2e.py`, `tests/test_f005_007_e2e.py` và browser Admin hiện có; dùng fake provider và không kết nối application database.
  - **Done:** Các kiểm thử tích hợp chứng minh contract, quyền, audit, thu hồi phiên và hành vi UI trong ba locale, hai theme, desktop/mobile; backend suite, frontend tests, E2E/browser, build, lint và format đạt; chỉ khi đó đánh dấu F013-010 hoàn tất.
  - **Validation (2026-10-24):** `tests/test_f013_010_admin_e2e.py` đạt 1/1 trên PostgreSQL disposable; `test_f012_005_accounts_e2e.AccountsEndToEndTests.test_browser_admin_provisions_roles_lost_response_lookup_and_delegation` đạt, chạy Admin E2E 11 nhóm qua frontend thật và backend dùng riêng. Browser regression xác nhận password reset, session cũ và lost PATCH response; Admin browser đạt 32 nhóm với responsive/theme/keyboard/admin checks; i18n test xác nhận thông báo password reset cho vi/en/ru. Full backend suite đạt 271/271; `npm --prefix frontend test` đạt 77/77 không skip; build, lint, format check đạt. Task hoàn tất.

- [x] F013-011 — Hiện diện người dùng và chuẩn hóa hai modal.
  - **Work:** Thêm migration 0011; ghi timestamp theo session và tài khoản; bổ sung heartbeat có Origin/CSRF; trả presence theo trang; hiển thị Last active, polling nền; thống nhất Create/Edit modal.
  - **Where:** `backend/ruvie/models/auth.py`, `services/auth.py`, `api/auth.py`, `contracts/admin.py`, `services/admin.py`; migration `0011_user_presence.py`; `frontend/src/lib/features/auth/presence.ts`, `auth-api.ts`; WorkspacePage; admin API/state/AccountsPanel và hai form/modal; SurfaceDialog; ba catalog locale.
  - **Reuse:** AuthSession, CSRF/Origin hiện có, SurfaceDialog, PasswordField/eye asset và admin state request generation. Tham khảo cách hiển thị relative time và ngưỡng 180 giây tại `references/src/lib/components/admin/Users/UserList.svelte`; không port auth, client timestamp hay runtime legacy.
  - **Done:** Chứng minh nhiều phiên, timeout, logout, thu hồi, quyền admin, throttle, retry/dispose; kiểm tra PostgreSQL migration, backend suite, frontend và browser.
  - **Validation (2026-10-25):** Bộ backend đầy đủ chạy lại đạt 276/276, không skip; Admin E2E đạt 11 nhóm. `test_f013_011_user_presence` đạt 5/5, gồm API heartbeat làm mới lease cũ trên PostgreSQL thật và migration 0011. Frontend đạt 83/83, không skip; browser Admin đạt 34 nhóm, Workspace 29, UX 42, Theme 9, LLM/locale/zoom 82. Build, lint và format check đạt. Đã kiểm tra SQL migration và áp dụng revision `0011_user_presence` vào database phát triển. Snapshot migration F012 chỉ so sánh các cột của revision 0009; helper điều hướng chờ workspace khôi phục session sau reload trước khi Back khỏi Settings. Task hoàn tất.
