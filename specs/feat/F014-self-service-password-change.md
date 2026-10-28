# F014 - Tự đổi mật khẩu trong Cài đặt tài khoản

Trạng thái: Hoàn tất F014-001 đến F014-008; đã nghiệm thu backend, frontend và browser/E2E ngày 2026-10-26.
Ngày lập: 2026-10-26.

## Goal

Cho phép user và admin tự đổi mật khẩu trong Ruvie Agent. Người dùng phải cung
cấp đúng mật khẩu hiện tại. Sau khi đổi, họ tiếp tục dùng phiên hiện tại; các
phiên khác của chính tài khoản đó bị thu hồi.

### Baseline trước triển khai

- `backend/ruvie/contracts/auth.py::RegisterRequest` quy định mật khẩu mới dài
  12–128 ký tự. Mật khẩu được giữ nguyên, kể cả khoảng trắng.
- `backend/ruvie/services/auth.py` có `hash_password`, `verify_password`,
  `AuthService.authenticate`, `resolve_session` và các hàm quản lý session.
  Chưa có use case tự đổi mật khẩu.
- `authenticate` khóa hàng user đến khi tạo session hoàn tất.
  `touch_presence` cũng khóa user trước khi cập nhật session.
- `backend/ruvie/api/security.py` có `check_origin`, `verify_csrf` và xử lý lỗi
  validation an toàn cho tạo tài khoản. Allowlist hiện chưa có ba trường mật khẩu
  của tính năng này.
- `backend/ruvie/services/admin.py::AdminAccountService.update_account` cho admin
  reset mật khẩu. Luồng đó xóa toàn bộ session của tài khoản được reset. Đây là
  nghiệp vụ khác với tự đổi mật khẩu.
- `frontend/src/lib/features/settings/SettingsPanel.svelte` hiện có tab Giao diện
  cho cài đặt cá nhân. Biến thể `system` hiển thị cấu hình LLM.
- `frontend/src/lib/pages/WorkspacePage.svelte` giữ SettingsPanel trong DOM và ẩn
  bằng `hidden` khi chuyển trang. Chỉ dựa vào unmount sẽ không xóa được form ẩn.

### Nguồn tham khảo và cách tái sử dụng

Ưu tiên dùng code active. Các đường dẫn sau đã được đọc trực tiếp:

| Nguồn | Hành vi dùng lại hoặc tham khảo | Thích nghi cần có |
| --- | --- | --- |
| `backend/ruvie/services/auth.py` | Hash scrypt, kiểm tra mật khẩu, session có token hash và thời hạn | Thêm transaction đổi mật khẩu; giữ đúng session gửi yêu cầu |
| `backend/ruvie/api/security.py` | Origin, CSRF và lỗi chỉ chứa trường/mã cho phép | Bảo vệ endpoint mới, không trả dữ liệu validation chứa mật khẩu |
| `backend/ruvie/services/audit.py::AuditEventWriter.append` | Ghi audit trong transaction của bên gọi | Ghi `account.password_change` cho chính người dùng |
| `frontend/src/lib/features/auth/PasswordField.svelte` | Hiện/ẩn mật khẩu, autocomplete và trạng thái lỗi | Dùng trong form settings; bảo đảm nhãn hiện/ẩn phân biệt ba trường và reset khi form bị ẩn |
| `references/backend/ruvie/routers/auths.py::update_password` | Xác minh mật khẩu hiện tại trước khi cập nhật | Dùng cookie/CSRF, service đồng bộ và PostgreSQL của active app; không mang JWT, trusted-header mode hoặc auth legacy vào |
| `references/src/lib/components/chat/Settings/Account/UpdatePassword.svelte` | Form ba trường, kiểm tra xác nhận, thông báo và xóa trường | Dùng Svelte 5, lỗi tại trường và kiểm tra cả backend; không dùng `localStorage.token`, lời gọi API hoặc toast lỗi thô của legacy |

Không import hoặc chạy runtime legacy. Không thay quyền project/tài liệu,
provider hoặc dữ liệu tài liệu. Không cần bảng/cột mới theo thiết kế này.

## User Story

Là người dùng đã đăng nhập, tôi muốn tự đổi mật khẩu tại tab Tài khoản trong
Cài đặt, để cập nhật thông tin đăng nhập và kết thúc các phiên đăng nhập khác.

Admin sử dụng cùng chức năng với user. Không cần quyền quản trị để tự đổi.

## Scope

### In

- Thêm tab **Tài khoản** ngang hàng với **Giao diện** trong Cài đặt cá nhân.
- Đặt form **Đổi mật khẩu** bên trong tab Tài khoản; không mở trang riêng.
- Nhập mật khẩu hiện tại, mật khẩu mới và xác nhận mật khẩu mới.
- Mỗi trường có nút hiện/ẩn riêng; mặc định ẩn.
- Kiểm tra frontend và backend; backend là bên quyết định cuối cùng.
- Từ chối mật khẩu mới trùng mật khẩu hiện tại.
- Đổi hash, thu hồi các session khác và ghi audit trong một transaction.
- Giữ session hiện tại, cookie, CSRF và thời hạn hiện có; không gia hạn phiên.
- Xử lý lỗi, trạng thái đang gửi, hết phiên và phản hồi về muộn.
- Dịch nội dung mới cho vi-VN, en-US và ru-RU.
- Kiểm thử service, HTTP, đồng thời trên PostgreSQL và giao diện trình duyệt.

### Out

- Quên mật khẩu, email/OTP, link khôi phục hoặc bắt buộc đổi lần đăng nhập đầu.
- Thay đổi nghiệp vụ admin reset mật khẩu, tạo tài khoản hoặc đổi vai trò.
- Sửa tên/email, quản lý danh sách thiết bị hoặc chọn session cần đăng xuất.
- Đổi chính sách mật khẩu chung, thêm dependency hoặc đổi thuật toán hash.
- Thêm cơ chế rate limit hoặc CAPTCHA riêng trong feature này.
- Thay cài đặt LLM của admin; chuyển vị trí bộ chọn ngôn ngữ/theme hiện có.
- Thêm schema, migration hoặc thay đổi thời hạn session.
- Hủy các request/stream đã được xác thực và đang chạy trước lúc thu hồi session.

## Flow

### 1. Giao diện và điều hướng

1. Người dùng mở Cài đặt. Tab mặc định vẫn là Giao diện.
2. Người dùng chọn tab Tài khoản trong cùng trang Cài đặt.
3. Hệ thống hiển thị form Đổi mật khẩu với ba trường rỗng.
4. Trợ giúp nêu rõ: mật khẩu mới dài 12–128 ký tự, khác mật khẩu hiện tại;
   thành công sẽ đăng xuất các phiên khác và giữ phiên đang dùng.
5. Người dùng nhập dữ liệu rồi chọn **Đổi mật khẩu**.
6. Nếu dữ liệu sai, hiển thị toast lỗi; đánh dấu lỗi cạnh trường và đưa focus tới trường lỗi đầu.
   Lỗi xác nhận hoặc độ dài tại frontend không gửi request.
7. Nếu hợp lệ, form chuyển sang trạng thái **Đang đổi mật khẩu…**. Khóa trường
   và nút gửi để tránh gửi lặp; không chặn điều hướng ra khỏi form.
8. Khi nhận thành công, xóa ba trường và trạng thái hiện mật khẩu. Hiển thị toast thành công:
   **Đã đổi mật khẩu. Các phiên đăng nhập khác đã được đăng xuất.**
   Người dùng vẫn ở tab Tài khoản.

Cài đặt cá nhân có tablist dọc. Tab hỗ trợ Up/Down, Home/End, roving tabindex,
`aria-selected`, `aria-controls` và panel có `aria-labelledby`. Tab order không
đưa focus vào panel ẩn. Tên tab Tài khoản được dịch theo locale đang dùng.

Form dùng label hiển thị, lỗi có `aria-describedby`/`aria-invalid`, thông báo
thành công hoặc lỗi đều dùng toast của `svelte-sonner` đang có trong active app.
Toast phải được công bố cho trình đọc màn hình qua live region của thư viện.
Lỗi cạnh trường hỗ trợ xác định chỗ cần sửa; không thay thế toast hoặc tạo thêm
banner thông báo kết quả. Nút hiện/ẩn có tên truy cập phân biệt từng trường.
Cho phép paste và password manager; dùng `current-password` cho trường hiện tại,
`new-password` cho hai trường còn lại. Giữ token màu và kích thước điều khiển
của active UI; dùng được ở mobile và cả hai theme.

Không ghi mật khẩu vào URL, storage, state dùng chung hoặc log. Lỗi validation
cục bộ có thể giữ dữ liệu để sửa. Sau phản hồi lỗi từ server hoặc lỗi mạng,
xóa ba trường và reset hiện/ẩn; hiển thị toast lỗi an toàn để người dùng nhập lại.
Validation cục bộ, lỗi nghiệp vụ, lỗi mạng và hết phiên đều dùng toast lỗi.
Mỗi lần gửi bị lỗi chỉ tạo một toast tổng hợp, không tạo một toast cho mỗi trường.
Không phát toast khi gõ từng ký tự hoặc blur. Trạng thái đang gửi nằm ở nút gửi.
Khi rời form, xóa toast thuộc form; bỏ qua toast từ phản hồi muộn. Với hết phiên,
chuyển notice lên auth owner ở App theo F014-006 để toast còn sau khi form
unmount; không phát hai toast cho cùng một kết quả.

Khi chuyển tab, rời Cài đặt, logout, mất session hoặc đổi danh tính, phải xóa
mật khẩu và vô hiệu hóa phản hồi cũ. Do SettingsPanel có thể vẫn mounted, cần
truyền trạng thái hiển thị thực tế hoặc unmount riêng form khi không còn active.
Abort request phía browser không có nghĩa transaction phía server đã bị hủy.
Không hiển thị thông báo của request cũ lên form mới hoặc tài khoản khác.

### 2. Hợp đồng API đã triển khai

Endpoint và contract bên dưới đã có trong active app. Các giới hạn, lỗi và
response này là hợp đồng cần giữ khi hoàn tất browser/E2E verification.

`POST /auth/password`

- Dùng cookie `ruvie_session`, Origin được phép và `X-CSRF-Token` của session.
- Không nhận user ID, email, role, token session đích hoặc tùy chọn bỏ kiểm tra.
- Không nhận trường ngoài hợp đồng; không ép kiểu dữ liệu.

```json
{
  "current_password": "old-password-example",
  "new_password": "new-password-example",
  "password_confirmation": "new-password-example"
}
```

| Trường | Quy tắc backend |
| --- | --- |
| `current_password` | Chuỗi bắt buộc, dài 1–1024 ký tự theo khả năng đăng nhập hiện có; phải khớp hash đang lưu |
| `new_password` | Chuỗi bắt buộc, dài 12–128 ký tự; khác mật khẩu hiện tại |
| `password_confirmation` | Chuỗi bắt buộc, dài 12–128 ký tự; bằng chính xác mật khẩu mới |

Không trim hoặc chuẩn hóa Unicode của mật khẩu. Frontend đếm Unicode code point
cho giới hạn độ dài để khớp Python; không dùng riêng số UTF-16 code unit của JS.
Các trường nhạy cảm không xuất hiện trong repr của contract hoặc lỗi HTTP.

Thành công: `204 No Content`, `Cache-Control: no-store`, không `Set-Cookie`, không
trả mật khẩu/hash, session token hoặc thông tin tài khoản mới.

| HTTP | `detail.code` | Kết quả |
| --- | --- | --- |
| 401 | `authentication_required` | Cookie thiếu/hết hạn/bị thu hồi hoặc user không active; dùng luồng hết phiên hiện có |
| 403 | `origin_not_allowed` / `csrf_invalid` | Không thực hiện cập nhật |
| 422 | `validation_error` | Thiếu trường, sai kiểu, sai độ dài, JSON lỗi hoặc có trường ngoài hợp đồng |
| 422 | `current_password_incorrect` | Lỗi ở `current_password`; không dùng 401 để tránh đăng xuất khi gõ sai |
| 422 | `password_confirmation_mismatch` | Lỗi ở `password_confirmation` |
| 422 | `password_unchanged` | Lỗi ở `new_password` |
| 503 | `password_change_unavailable` | Không hoàn tất được transaction; thông báo an toàn |

Lỗi validation chỉ dùng allowlist ba tên trường cùng mã
`required`, `invalid_type`, `password_length`. Có trường ngoài hợp đồng thì trả
mã chung; không phản chiếu tên/giá trị tùy ý. Frontend ánh xạ mã sang bản dịch,
không hiển thị raw exception. Mọi response của endpoint phải `no-store`, kể cả
validation, Origin/CSRF và lỗi hệ thống.

Kiểm tra Origin trước parse body. Bọc `RequestValidationError` cho endpoint mới:
`hide_input_in_errors` trong Pydantic một mình không ngăn FastAPI phản chiếu input.
Tái sử dụng helper phù hợp, giữ nguyên hợp đồng lỗi các endpoint auth/admin cũ.

### 3. Xử lý backend và session

`ChangePasswordRequest` nằm ở `contracts/auth.py`; use case
`AuthService.change_password(actor_user_id, session_token, command)` nằm ở
`services/auth.py`. Token đến từ cookie do route đọc, không từ JSON. Service
trả kết quả có cấu trúc hoặc lỗi miền; API chịu trách nhiệm HTTP.

1. Route xác minh Origin, session và CSRF bằng cơ chế active; gọi service.
2. Trong transaction, service khóa hàng user trước, rồi khóa session gửi yêu cầu.
   Dùng thứ tự user → session để phù hợp login, presence và reset của admin.
3. Đọc lại dữ liệu database bằng truy vấn refresh; không tin object/cache identity
   đã được kiểm tra trước khi chờ khóa. Kiểm tra user active, session thuộc actor,
   chưa hết hạn và chưa bị thu hồi. Đối chiếu bằng SHA-256 của cookie token.
4. Kiểm tra lại command cho caller nội bộ. Kiểm tra xác nhận và độ dài; xác minh
   mật khẩu hiện tại với hash mới nhất sau khi có khóa. Từ chối mật khẩu mới trùng.
5. Hash mật khẩu mới bằng `hash_password` với salt mới.
6. Cập nhật `users.password_hash`; xóa mọi `auth_sessions` của user đó trừ hàng
   session đã xác minh. Không thay session của tài khoản khác.
7. Ghi audit action `account.password_change`, resource_type `user`, actor và
   resource cùng user ID, outcome `allow`, reason `self_service`.
   Không ghi mật khẩu, hash, token, CSRF hoặc request body vào audit/log.
8. Commit cả ba thay đổi. Nếu hash, audit, flush hoặc commit thất bại, rollback
   toàn bộ. Khi DB lỗi, kết thúc transaction và trả lỗi an toàn.
9. Route trả 204 sau commit. Cookie, CSRF, identity, role và thời hạn giữ nguyên.

Đây là luồng tự đổi, không gọi hàm reset của admin vì hàm đó xóa mọi session.
Không dùng `set_existing_user_password` như một use case hoàn chỉnh vì hàm đó
chưa xác minh mật khẩu hiện tại, session và thu hồi phiên trong cùng transaction.

Các tab dùng chung cookie là cùng một session và đều được giữ. Browser/profile
khác có session riêng sẽ bị thu hồi. Request mới từ session bị thu hồi phải bị
từ chối; stream/request đã chạy không thuộc phạm vi hủy của feature này.

## Edge Cases

| Tình huống | Hành vi yêu cầu |
| --- | --- |
| Sai mật khẩu hiện tại | Toast lỗi và đánh dấu trường; không sửa hash/session/audit thành công |
| Mật khẩu mới trùng hiện tại | Từ chối sau khi xác minh mật khẩu hiện tại; không cập nhật |
| Xác nhận lệch, thiếu/sai kiểu, vượt giới hạn hoặc JSON lỗi | Từ chối an toàn, không phản chiếu mật khẩu |
| Khoảng trắng hoặc Unicode trong mật khẩu | So khớp nguyên giá trị; không tự trim hoặc normalize |
| Hết phiên trước khi gửi hoặc trong lúc chờ khóa | 401, không tạo session thay thế hoặc hồi sinh session đã bị xóa |
| Admin reset cùng lúc | Tuần tự theo khóa user; nếu reset đã xóa session thì yêu cầu tự đổi bị từ chối; reset chạy sau vẫn xóa cả session đang giữ theo nghiệp vụ hiện có |
| Hai session cùng đổi bằng mật khẩu cũ | Chỉ một lần đổi thành công; session còn lại bị thu hồi trước khi được xử lý |
| Hai request cùng session | Tuần tự; request dùng mật khẩu cũ không được ghi đè kết quả request đã commit |
| Login bằng mật khẩu cũ chạy đồng thời | Login xảy ra trước thì session mới tạo phải nằm trong số bị thu hồi; login xảy ra sau thì mật khẩu cũ không đăng nhập được |
| Presence hoặc logout đồng thời | Không deadlock do đảo thứ tự khóa; không hồi sinh session đã thu hồi; logout cuối cùng vẫn có hiệu lực |
| Hash/audit/commit thất bại | Rollback hash và thu hồi session; không báo thành công |
| Server trả lỗi sau rollback | Toast lỗi an toàn, xóa các trường và cho nhập lại |
| Mất kết nối hoặc mất phản hồi sau khi gửi | Toast lỗi nêu chưa xác định kết quả; không tự gửi lại và không khẳng định mật khẩu chưa đổi; hướng dẫn kiểm tra bằng mật khẩu mới khi đăng nhập |
| Rời form khi đang gửi | Xóa dữ liệu client, bỏ qua phản hồi muộn; transaction đã nhận có thể vẫn hoàn tất |
| Đổi locale hoặc theme | Label/thông báo đổi theo locale; không gửi lại request hoặc đổi tab; trạng thái form vẫn thuộc cùng phiên |

## Kết quả kiểm chứng hiện tại

Nghiệm thu ngày 2026-10-26 trên PostgreSQL/pgvector dùng một lần, fake providers
và Microsoft Edge headless. Không chạy vào database ứng dụng.

| Kiểm tra | Lệnh đã chạy | Kết quả |
| --- | --- | --- |
| Backend đầy đủ, gồm browser/E2E | `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py'` | 311 test, 0 failure/error, 0 skip; 759.104 giây |
| Frontend build | `npm --prefix frontend run build` | Đạt; 299 modules |
| Frontend test | `npm --prefix frontend test` | 89 pass, 0 fail, 0 skip |
| Frontend lint | `npm --prefix frontend run lint` | Đạt |
| Frontend format | `npm --prefix frontend run format:check` | Đạt |
| F014 HTTP giả | `node frontend/tests/account-settings-browser.mjs` | 16 nhóm đạt |
| Admin regression | `node frontend/tests/admin-browser.mjs` | 34 nhóm đạt |
| Auth regression | `node frontend/tests/auth-browser.mjs` | 61 kiểm tra đạt |
| Theme regression | `node frontend/tests/theme-browser.mjs` | 9 kiểm tra đạt |
| Workspace regression | `node frontend/tests/workspace-browser.mjs` | 29 kiểm tra đạt |
| LLM regression | `node frontend/tests/llm-browser.mjs` | 82 kiểm tra đạt |
| Frontend UX regression | `node frontend/tests/frontend-ux-browser.mjs` | 42 kiểm tra đạt |
| Whitespace diff | `git diff --check` | Đạt |

- Backend F014: contract 5, service 8, API 7, concurrency PostgreSQL 13 và E2E 2
  test. Các test này nằm trong lượt full suite đạt nêu trên. Hai lượt E2E user/admin
  đều báo 7 kiểm tra trình duyệt đạt. Admin E2E hiện có cũng đạt 11 nhóm.
- E2E xác minh mật khẩu cũ/mới, cookie giữ nguyên, không có Set-Cookie, no-store,
  session A1/A2/B1, hash, audit, identity, role, membership và access grant.
- Browser kiểm tra validation/focus, hiện/ẩn độc lập, pending/duplicate submit,
  phản hồi muộn 204/401 sau điều hướng, lỗi 401/403/422/503/mạng, toast đơn,
  đổi locale/dismiss, bàn phím, mobile 360px và light/dark.
- Hai lỗi tìm được bằng browser đã sửa: ID tab Giao diện trùng ID tab Tài khoản;
  focus lỗi server chạy khi input còn disabled. Focus hiện chờ `tick()` sau khi
  mở khóa input và kiểm tra lại generation/active trước khi thực hiện.
- Regression fixture được đồng bộ: Settings cá nhân có hai tab; auth dùng URL/
  history để chuyển mode, selector submit hiện có và locale rõ ràng. Một lượt
  auth timeout lúc build đang ghi lại dist; chạy riêng sau build đạt 61 kiểm tra.
- Playwright 1.60.0 dùng npm cache trong thư mục ignored
  `frontend/node_modules/.f014-browser-tools`; không đổi package.json/lockfile.
  `RUVIE_PLAYWRIGHT_PATH` trỏ tới module này; `RUVIE_BROWSER_PATH` trỏ tới Edge
  đã cài. Backend dùng `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=tests;backend`.
- Không có migration mới. Không còn gate F014 bị chặn hoặc bài kiểm tra bị skip.

### Bản đồ code đã triển khai

| File production | Vai trò và điểm vào |
| --- | --- |
| `backend/ruvie/contracts/auth.py` | `ChangePasswordRequest`: nhận ba chuỗi strict, kiểm tra độ dài/xác nhận, ẩn mật khẩu trong repr |
| `backend/ruvie/services/auth.py` | `AuthService.change_password`: actor/token/command → `ChangedPasswordResult`; khóa user/session, kiểm tra lại, hash/revoke/audit nguyên tử; `PasswordChangeError` chỉ mang mã an toàn |
| `backend/ruvie/api/auth.py` | Route `POST /auth/password` và wrapper: Origin trước parse, identity/CSRF, serialization lỗi allowlist, 204/no-store, không đổi cookie |
| `frontend/src/lib/features/auth/auth-api.ts` | `changePassword` gửi cookie/CSRF và ba trường, trả thành công hoặc `PasswordChangeApiError`; không retry, không dùng lỗi thô |
| `frontend/src/lib/features/auth/PasswordField.svelte` | Tái sử dụng input/toggle; thêm resetKey và nhãn toggle riêng, giữ mặc định cho caller cũ |
| `frontend/src/lib/features/settings/password-form.ts` | `validatePasswordChange`: giá trị form → lỗi UiMessage theo trường, đếm Unicode code point và giữ khoảng trắng |
| `frontend/src/lib/features/settings/ChangePasswordForm.svelte` | Form ba trường, pending/reset/focus, AbortController/generation, toast phản ứng với locale và callback hết phiên |
| `frontend/src/lib/features/settings/SettingsPanel.svelte` | Tab Appearance/Account cá nhân, ARIA/keyboard, mount form khi active; system chỉ có LLM |
| `frontend/src/lib/pages/WorkspacePage.svelte` | Truyền CSRF/active và đưa notice hết phiên qua vòng đời workspace |
| `frontend/src/App.svelte` | `expireWorkspace` nhận notice an toàn, phát auth toast trước khi clear workspace |
| `frontend/src/lib/i18n/locales/vi-VN/translation.json` | Nhãn, trợ giúp và thông báo tiếng Việt |
| `frontend/src/lib/i18n/locales/en-US/translation.json` | Cùng hợp đồng khóa dịch tiếng Anh |
| `frontend/src/lib/i18n/locales/ru-RU/translation.json` | Cùng hợp đồng khóa dịch tiếng Nga |

Dùng lại scrypt, session, Origin/CSRF, audit và PasswordField của active app.
Nguồn legacy và phần thích nghi được ghi tại bảng nguồn tham khảo đầu spec;
không import runtime legacy hoặc thay mô hình phân quyền.

## Acceptance Criteria

- [x] AC-01: User và admin mở được tab Tài khoản trong Cài đặt cá nhân; Giao diện
  vẫn là tab mặc định; phần system LLM không nhận tab Tài khoản.
- [x] AC-02: Form có đúng ba trường, nút hiện/ẩn riêng và trợ giúp về 12–128 ký
  tự cùng việc đăng xuất phiên khác; dùng được bằng bàn phím và ở mobile.
- [x] AC-03: Frontend và backend cùng từ chối xác nhận lệch, mật khẩu mới không
  hợp lệ hoặc trùng hiện tại; gọi API trực tiếp không bỏ qua được quy tắc.
- [x] AC-04: Mật khẩu hiện tại sai trả 422, giữ phiên đăng nhập; mật khẩu và
  session đã lưu không đổi.
- [x] AC-05: Thành công chỉ đổi mật khẩu của actor; không nhận ID/role từ client,
  không đổi vai trò, membership, quyền tài liệu hoặc dữ liệu tài khoản khác.
- [x] AC-06: Sau 204, mật khẩu cũ không đăng nhập được và mật khẩu mới đăng nhập
  được; hash không bằng plaintext và xác minh được bằng helper active.
- [x] AC-07: Cookie, CSRF và thời hạn session hiện tại giữ nguyên; session khác
  của cùng user bị thu hồi; session của user khác còn dùng được.
- [x] AC-08: Thiếu/sai Origin, CSRF, cookie, user inactive hoặc session hết hạn/
  bị thu hồi đều bị từ chối; kiểm tra lại sau khi chờ khóa.
- [x] AC-09: Response, validation error, repr và audit không chứa mật khẩu/hash/
  token; endpoint luôn trả `Cache-Control: no-store`.
- [x] AC-10: Audit thành công được ghi cùng transaction; lỗi hash/audit/commit
  không để lại cập nhật dở hoặc session bị thu hồi riêng lẻ.
- [x] AC-11: Kiểm thử PostgreSQL chứng minh các race giữa tự đổi, login cũ và
  admin reset không giữ session trái quy tắc hoặc cho hai thay đổi cũ cùng thắng.
- [x] AC-12: Không gửi trùng khi đang xử lý; xóa mật khẩu và hiện/ẩn khi thành
  công, lỗi server/mạng, đổi tab, rời Cài đặt, logout hoặc hết phiên.
- [x] AC-13: Phản hồi cũ không hiển thị lên form mới hoặc tài khoản khác; lỗi
  mạng không tự retry hoặc báo chắc chắn chưa đổi mật khẩu.
- [x] AC-14: Thành công và mọi lỗi đều có toast an toàn, một toast mỗi kết quả;
  không phát trùng với luồng auth hoặc phát sau khi rời form. Có bản dịch
  vi-VN/en-US/ru-RU; toast có live region, lỗi gắn với input; tab/panel và focus
  có ngữ nghĩa truy cập; không ghi mật khẩu vào browser storage.
- [x] AC-15: Regression login/bootstrap, admin reset, presence, theme/locale,
  cấu hình LLM và điều hướng workspace vẫn giữ hợp đồng hiện có.

## Tasks

### Cách dùng phần bàn giao

Các task dưới đây giữ ID và hướng dẫn thực thi để đối chiếu/bàn giao. Toàn bộ
001–008 đã hoàn tất và được kiểm chứng theo bảng kết quả. Các bước Work mô tả
trình tự triển khai; baseline trong đó là bối cảnh trước thay đổi, không phải
khoảng trống còn lại. Tên file/type/hàm phải khớp code active hiện tại.

Trước mỗi task, đọc AGENTS.md, README.md, Flow và task phụ thuộc. Đọc lại code
active được chỉ định; không đọc thư mục `archive`. Báo file sẽ sửa và validation
trước khi thay đổi theo AGENTS.md. Spec không tự cấp quyền sửa toàn bộ kế hoạch.

Viết test hành vi trước, xác nhận test thất bại vì thiếu hành vi đó, rồi thêm
code tối thiểu để test đạt. Không thêm framework, repository layer, event bus
hoặc state toàn cục cho feature này. Không refactor auth/admin không liên quan.

| Task | Phụ thuộc | Sản phẩm bàn giao |
| --- | --- | --- |
| F014-001 | Không | Contract và test validation |
| F014-002 | 001 | Use case nguyên tử và test service |
| F014-003 | 001, 002 | Endpoint, lỗi an toàn và test HTTP |
| F014-004 | 002, 003 | Bằng chứng PostgreSQL cho rollback/tranh chấp khóa |
| F014-005 | Hợp đồng 001/003 ổn định | Client, helper và form; có thể test HTTP giả trước |
| F014-006 | 005 | Tab, lifecycle, auth toast và bản dịch |
| F014-007 | 003 đến 006 | Browser, tích hợp thật và regression |
| F014-008 | 007 đạt kiểm tra bắt buộc | Tài liệu và bằng chứng nghiệm thu |

Thứ tự mặc định: 001 → 002 → 003 → 004 → 005 → 006 → 007 → 008.
Bảng phụ thuộc không yêu cầu nhiều agent hoặc nhiều backend suite cùng lúc.

### F014-001 — Contract và validation mật khẩu

- [x] Hoàn thành F014-001.

**Where:** Sửa `backend/ruvie/contracts/auth.py`; tạo
`tests/test_f014_001_password_contract.py`.

**Đầu vào → đầu ra:** JSON ba trường → `ChangePasswordRequest` hoặc lỗi
validation có type xác định. Task này không đọc DB, hash hoặc xử lý HTTP.

**Work — thực hiện theo thứ tự**

1. Đọc RegisterRequest/LoginRequest. Tạo `ChangePasswordRequest` với
   `ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)`.
2. Ba trường bắt buộc đều `repr=False`: current_password dài 1–1024;
   new_password và password_confirmation dài 12–128 code point. Không default,
   không chấp nhận null, số, boolean, list hoặc object.
3. Không strip/normalize mật khẩu hoặc thêm quy tắc chữ hoa/số/ký tự đặc biệt.
4. Sau validation từng trường, kiểm tra new bằng confirmation. Dùng type lỗi
   `password_confirmation_mismatch` cố định, chẳng hạn PydanticCustomError từ
   dependency hiện có. Không đưa mật khẩu vào message hoặc context lỗi.
5. Chưa xét new trùng current ở contract. Service xét sau khi current đúng.
6. Test biên, sai kiểu, thiếu trường và extra. Test repr không chứa mật khẩu.
   Không coi `ValidationError.errors()` mặc định là dữ liệu an toàn để trả HTTP;
   task 003 phải có serializer riêng.

**Ma trận kiểm tra tối thiểu**

| Input | Kỳ vọng |
| --- | --- |
| Current dài 1/1024; new/confirm dài 12/128 | Hợp lệ khi confirm khớp |
| Current dài 0/1025; new/confirm dài 0/11/129 | Từ chối đúng trường |
| Thiếu trường, null, số, boolean, list, object | Không ép kiểu/default |
| Confirm khác new | Type lỗi password_confirmation_mismatch |
| Extra user_id/email/role hoặc key tùy ý | Bị từ chối |
| Khoảng trắng, Unicode, emoji ở biên | Giữ nguyên; Python đếm code point |
| Current bằng new, confirm khớp | Contract hợp lệ; service xét nghiệp vụ |

**Done:** Test đạt, không thay contract login/register hoặc chính sách chung.
Bàn giao type lỗi mismatch cho 002/003. Bao phủ phần contract AC-03, AC-09.

### F014-002 — Use case đổi mật khẩu nguyên tử

- [x] Hoàn thành F014-002.

**Where:** Sửa `backend/ruvie/services/auth.py`; dùng model User/AuthSession và
AuditEventWriter hiện có; tạo `tests/test_f014_002_password_service.py`.

**Đầu vào → đầu ra**

Đề xuất `AuthService.change_password(actor_user_id: str, session_token: str,
command: ChangePasswordRequest) -> ChangedPasswordResult`. Actor là identity đã
xác thực; token lấy từ cookie. Result là dataclass frozen chỉ có user_id;
route không serialize result ra HTTP. Không trả ORM object hoặc bí mật.

Dùng lỗi miền nhỏ như `PasswordChangeError(code)` với allowlist
`authentication_required`, `current_password_incorrect`, `password_unchanged`.
Revalidation có thể phát ValidationError; lỗi kỹ thuật rollback rồi propagate.
Service không import FastAPI hoặc tự quyết định HTTP status.

**Work — thực hiện theo thứ tự**

1. Fixture có user A, session A1/A2; user B, session B1. Snapshot hash, session,
   audit trước khi gọi. Chạy cả role user/admin cho actor A.
2. Bao thao tác DB bằng try/except rollback. Session của route có thể autobegin
   từ CSRF; không gọi `session.begin()` vô điều kiện hoặc commit chỉ để mở lại.
3. Query user theo actor ID với FOR UPDATE và populate_existing=True; từ chối
   user thiếu/inactive. Không tin object cũ trong identity map hoặc email body.
4. SHA-256 cookie token như resolve_session. Query session với cả token_hash
   và user_id == actor, FOR UPDATE và refresh. Luôn khóa user trước session.
5. Lấy UTC now mới sau khi có khóa; kiểm tra expires_at > now. Chuẩn hóa datetime
   naive trong unit test như code active. Token sai, token B1 cho actor A, session
   bị xóa/hết hạn đều phát authentication_required; không tạo phiên thay thế.
6. Không gọi resolve_session bên trong transaction đang giữ khóa: hàm hiện tại
   có thể delete/commit session hết hạn. Không dùng dependency check làm lần
   kiểm tra cuối sau khi chờ khóa.
7. Revalidate command bằng model_validate từ dữ liệu command; caller nội bộ có
   thể mutate/model_construct. Xác minh current với hash đã refresh. Hash thiếu/
   hỏng hoặc current sai phát current_password_incorrect.
8. Chỉ sau khi current đúng, xét new bằng current → password_unchanged.
   Hash new bằng helper hiện có và salt mới; không đổi tham số scrypt.
9. Gán hash mới; delete session với cả `user_id == actor_user_id` VÀ
   `id != retained_session.id`. Không chỉ lọc id != ... hoặc xóa toàn bộ bảng.
10. Append audit theo Flow, cùng transaction; flush khi cần. Commit đúng một lần
    cho hash/delete/audit. Mọi lỗi trước commit rollback rồi phát lại.
11. Trả result sau commit; không success trong finally hoặc nuốt lỗi audit.
    Không gọi create_session, _stage_session, admin reset hay
    set_existing_user_password để thay thế use case.
12. Giữ ID/token_hash/CSRF/expiry của A1, role, quyền và B1. updated_at tự đổi
    theo model là bình thường; không tự cập nhật presence trong use case này.

**Ma trận kiểm tra tối thiểu**

- Thành công A1: hash xác minh bằng new; A1 giữ metadata; A2 xóa; B1 còn;
  đúng một success audit cho A. Không có phiên khác vẫn đổi được.
- Sai current, new trùng, command bị mutate, user inactive/hash thiếu, token
  xóa/hết hạn/token B1 gắn actor A: hash/session/audit thành công không đổi.
- Preload ORM, sửa DB bằng transaction khác rồi gọi để kiểm tra refresh;
  tranh chấp row lock thật chuyển task 004.
- Inject lỗi hash, lỗi audit sau append/flush, lỗi commit trước commit thật.
  Đọc bằng session DB mới sau rollback để so với snapshot.
- Không inject lỗi sau commit thật rồi kết luận rollback hoàn tác được dữ liệu;
  mất phản hồi sau commit là trường hợp kết quả chưa xác định.

**Done:** AC-04 đến AC-07 và AC-10 được kiểm chứng ở service; lỗi nghiệp vụ
phân biệt được với lỗi kỹ thuật. SQLite pass chưa chứng minh row lock PostgreSQL.

### F014-003 — Endpoint và bảo vệ lỗi HTTP

- [x] Hoàn thành F014-003.

**Where:** Sửa `backend/ruvie/api/auth.py`; sửa
`backend/ruvie/api/security.py` nếu đặt helper tại đây; tạo
`tests/test_f014_003_password_api.py`.

**Đầu vào → đầu ra:** POST /auth/password với cookie/CSRF → 204 rỗng hoặc lỗi
trong bảng Flow. Dùng router /auth đã đăng ký; không thêm prefix/router mới.

**Work — thực hiện theo thứ tự**

1. HTTP test dùng auth router thật, DB tạm và TestClient riêng A1/A2/B1.
   Không chỉ override identity rồi bỏ qua cookie thật.
2. Đọc RegistrationRoute.get_route_handler: hiện chỉ /register dùng wrapper
   AccountCreationRoute. Thêm nhánh riêng bảo vệ /auth/password trong route
   class/helper cục bộ; giữ đường xử lý route auth/admin khác.
3. Wrapper gọi check_origin trước FastAPI parse body. Origin thiếu/sai trả
   403 origin_not_allowed và no-store kể cả JSON hỏng.
4. FastAPI validate ChangePasswordRequest; lấy actor bằng dependency session,
   gọi verify_csrf, đọc COOKIE_NAME từ request rồi gọi service. Service vẫn
   revalidate sau khóa; không dùng request.state như kiểm tra cuối.
5. Map HTTPException của identity/CSRF thành 401 authentication_required hoặc
   403 csrf_invalid. Phân biệt theo nguồn/status, không parse text exception.
   Không sửa mã lỗi của tất cả endpoint khác.
6. Map PasswordChangeError theo allowlist; current sai/new trùng trả 422.
   Map ValidationError của revalidation và RequestValidationError của HTTP
   qua serializer an toàn. Type mismatch trả password_confirmation_mismatch.
7. Serializer chỉ nhận ba field hợp lệ: missing → required;
   string_too_short/long → password_length; sai kiểu → invalid_type.
   JSON hỏng/extra trả validation_error chung; không phản chiếu key lạ, input,
   ctx, URL trợ giúp, str(error) hoặc giá trị password.
8. Lỗi có field trả shape cố định như ví dụ dưới. Validation có thể có nhiều
   field nhưng frontend chỉ phát một toast cho lần submit.
9. Bao đường identity/CSRF/service để lỗi DB/hash/audit thành 503
   password_change_unavailable an toàn. Kết thúc transaction lỗi bằng rollback.
   Catch nghiệp vụ/validation trước kỹ thuật; không biến mọi lỗi thành 503.
10. No-store phải có trên success, JSONResponse trả trực tiếp và HTTPException.
    204 không body và không Set-Cookie. Không thêm handler toàn app làm thay
    hợp đồng lỗi login/register/admin chỉ để bảo vệ endpoint mới.

Ví dụ lỗi nghiệp vụ:

```json
{"detail":{"code":"current_password_incorrect","fields":{"current_password":"current_password_incorrect"}}}
```

Ví dụ lỗi dữ liệu:

```json
{"detail":{"code":"validation_error","fields":{"new_password":"password_length"}}}
```

**Ma trận kiểm tra tối thiểu**

| Request | HTTP / quan sát |
| --- | --- |
| Hợp lệ bằng user/admin | 204, body rỗng, no-store, không Set-Cookie |
| Sai current | 422, mã/field đúng, A1 vẫn xác thực được |
| Confirm lệch / new trùng | 422 đúng mã/field, DB không đổi |
| Cookie thiếu/hết hạn/bị thu hồi, user inactive | 401, không success audit |
| Origin thiếu/sai và JSON hỏng | 403 origin_not_allowed, không phản chiếu body |
| CSRF thiếu/sai, cookie hợp lệ | 403 csrf_invalid |
| Missing/type/length/extra/JSON lỗi | 422 safe shape |
| Lỗi kỹ thuật chứa marker bí mật | 503 mã chung, không lộ exception/SQL params |

Mỗi ca assert no-store và body không chứa marker password/hash/cookie token.
Đọc DB mới để chứng minh lỗi không thay hash/session. Chạy regression auth/admin
để phát hiện wrapper làm đổi hợp đồng cũ. Không nới Origin/CSRF vì test.

**Done:** HTTP test đạt AC-03 đến AC-09; frontend phân biệt sai mật khẩu với
hết phiên bằng status/code, không đoán text backend.

### F014-004 — Kiểm thử transaction và đồng thời PostgreSQL

- [x] Hoàn thành F014-004.

**Where:** Tạo `tests/test_f014_004_password_concurrency.py`. Tái sử dụng fixture
disposable `tests/test_f005_007_e2e.py` như cách
`tests/test_f012_005_accounts_e2e.py` dùng. Tham khảo lock test trong
`tests/test_f012_003_admin_accounts.py` và reset test
`tests/test_f013_009_admin_passwords.py`.

**Work — thực hiện theo thứ tự**

1. Dùng PostgreSQL/pgvector disposable, migration hiện có và fake providers;
   lifecycle setup/cleanup theo fixture active. Không dùng database ứng dụng.
2. Mỗi thread có SQLAlchemy Session riêng; không share Session/ORM object hoặc
   mutable TestClient. Session cookie của từng bên phải được xác định rõ.
3. Dùng Event, transaction blocker hoặc patch helper trong test để giữ bên thắng
   sau khi có user lock. Xác minh bên kia đợi lock bằng query giám sát có deadline
   như test active; không sleep rồi giả định thứ tự đúng.
4. Không dùng Barrier đợi cả hai thread vào hash_password: bên thứ hai đang đợi
   user lock sẽ không tới đó. Chặn bên đã có khóa bằng Event và release trong
   finally kể cả assert lỗi. Không thêm hook test vào production.
5. Future/Event có timeout hữu hạn; kết thúc worker trước khi đóng DB/container.
   Không để teardown treo do thread giữ khóa.
6. Chạy hai thứ tự thắng cho login và reset theo bảng sau. Khi cả hai worker
   kết thúc, dùng session DB mới kiểm tra hash, session còn lại và audit.

| Ca tranh chấp | Kết quả bắt buộc |
| --- | --- |
| A1/A2 đổi cùng current cũ | Một success, một authentication_required; chỉ session thắng còn; một success audit |
| Hai request A1, current cũ, new khác nhau | Một success; request sau current_password_incorrect; hash của request thắng |
| Login cũ commit trước tự đổi | Session login vừa tạo cũng bị thu hồi; A1 giữ |
| Tự đổi commit trước login cũ | Login cũ bị từ chối; không tạo session mới bằng mật khẩu cũ |
| Admin reset commit trước tự đổi | A1 bị thu hồi; tự đổi bị từ chối; giữ mật khẩu admin đặt |
| Tự đổi commit trước admin reset | Reset sau đổi hash và xóa cả A1 theo hợp đồng reset hiện có |
| A1 hết hạn/bị thu hồi khi chờ user lock | Kiểm tra lại sau khóa → authentication_required; hash không đổi |
| Presence A2 cùng tự đổi A1 | Presence có thể chạy trước; sau commit A2 luôn mất quyền, không được tạo lại |
| Logout A1 cùng tự đổi A1 | Logout thắng trước thì tự đổi không xác thực; tự đổi thắng trước thì logout vẫn xóa A1; cuối cùng không còn A1 |

7. Inject lỗi audit sau flush và lỗi commit trước commit thật trên PostgreSQL.
   Hash/session/audit khớp snapshot sau rollback. Không bulk sửa/xóa audit cũ
   để cleanup vì audit có cơ chế bất biến.
8. Không thêm retry/deadlock framework vào app chỉ để test đạt. Nếu phát hiện
   bug ngoài phạm vi, báo bằng chứng và xin duyệt file liên quan trước mở rộng.

**Done:** AC-08, AC-10, AC-11 có bằng chứng PostgreSQL. Báo từng ca đã chạy;
SQLite pass hoặc Docker test skip chưa đủ hoàn thành task này.

### F014-005 — Client và form đổi mật khẩu

- [x] Hoàn thành F014-005.

**Where**

- Sửa `frontend/src/lib/features/auth/auth-api.ts`.
- Sửa `frontend/src/lib/features/auth/PasswordField.svelte` bằng props tùy chọn.
- Tạo `frontend/src/lib/features/settings/password-form.ts`,
  `frontend/src/lib/features/settings/ChangePasswordForm.svelte`,
  `frontend/tests/password-form.test.mjs`.
- Mở rộng `frontend/tests/auth-api.test.mjs`.
- Sửa ba catalog locale được liệt kê ở 006 cho các key client/form cần ngay.

**Đầu vào → đầu ra**

- `changePassword(csrfToken, command, signal?) -> Promise<void>` gửi ba trường
  của API. Chỉ 204 thành công; không đọc JSON khi 204.
- `PasswordChangeField` gồm ba tên field; `PasswordChangeFieldErrors` là
  `Partial<Record<PasswordFieldName, UiMessage>>`. Không ép sang AuthField của
  login/register. Lỗi client nhỏ có status/code/uiMessage/fieldErrors; không
  gắn raw body, command hoặc mật khẩu vào Error.
- `validatePasswordChange(values)` là helper thuần trả fieldErrors; type/helper
  đặt trong password-form.ts khi phù hợp. Không tạo store/factory cho ba input.
- Form nhận csrfToken/onexpired theo điểm nối 006; mật khẩu chỉ ở instance form,
  không đưa lên WorkspacePage hoặc store dùng chung.

**Work — thực hiện theo thứ tự**

1. Thêm key account.password.* mà client/form dùng trong cả ba catalog ngay
   ở task này, để MessageKey có type hợp lệ; 006 chỉ bổ sung tab/điểm nối còn lại.
   Client tái sử dụng fetch helper nếu giữ được signal/credentials. Gửi JSON,
   CSRF, same-origin cookie và cache no-store; không identity. Không tự đặt
   Origin vì browser cung cấp; không log body và không retry POST.
2. Parser chỉ nhận status/code/fields allowlist. 422 map trường; 401 hết phiên;
   403 quyền/CSRF; 503 lỗi dịch vụ xác định. Body/code lạ không hiện raw text hoặc
   coi là success. Network/body phản hồi không xác định phải báo chưa biết kết
   quả; không khẳng định rollback khi không nhận mã lỗi xác định từ backend.
3. Helper local dùng `[...value].length`, không trim/normalize. Kiểm tra required,
   độ dài, confirm và new khác current. Focus theo thứ tự current → new → confirm.
   Form dùng novalidate để browser không chặn submit trước toast; validation
   ứng dụng vẫn kiểm tra đầy đủ mọi trường.
4. Submit có lỗi local: giữ input, lưu fieldErrors, focus trường lỗi đầu và một
   toast tổng hợp. Không request; không phát toast trên input/blur.
5. Sau local validation, đặt busy đồng bộ trước await; chụp generation request.
   Disabled input/nút gửi, đổi nhãn đang xử lý; không chặn navigation rời form.
6. 204 về và request còn hiện hành: xóa ba input/fieldErrors, reset hiện/ẩn,
   nhả busy, phát một success toast. Không clear session, điều hướng login hoặc
   xóa draft chat do thành công.
7. 422 về: xóa input/show-hide, giữ fieldErrors an toàn, focus trường liên quan,
   một error toast. 403/503 có toast tổng hợp; không onexpired. Network lỗi xóa
   input và báo chưa xác định kết quả; không có nút retry POST tự động.
8. 401 khi form còn active: xóa input/show-hide, chuyển message lên onexpired.
   Không vừa phát toast form vừa phát auth toast. Task 006 giữ toast ở App sau
   khi form unmount.
9. AbortController và disposed/generation thuộc instance. Unmount invalidate
   generation trước abort/dismiss. Sau mỗi await, kiểm tra guard trước state,
   toast/onexpired; abort do rời form không phát network toast. finally cũ không
   được nhả busy cho instance/request mới. Abort không đảm bảo server rollback.
10. Dùng một toast ID riêng như account-password-response để thay kết quả cũ.
    Lưu notice bằng UiMessage để đổi locale cập nhật toast đang mở. Dismiss/
    auto-close clear notice để effect không phát lại. Unmount chỉ dismiss ID
    của form; không `toast.dismiss()` toàn app.
11. Không thêm Toaster: App đã render AuthToastLayer. Dùng toast.success/error
    của svelte-sonner đang có; không banner kết quả. Chỉ một toast tổng hợp cho
    mỗi submit hoặc kết quả, kể cả nhiều field sai.
12. PasswordField có show state nội bộ và chỉ reset ở onDestroy. Thêm resetKey
    tùy chọn mặc định ổn định; đổi key thì show=false. Thêm nhãn toggle tùy chọn
    để ba trường phân biệt được. Giữ default login/register. Tăng key sau success/
    lỗi server hoặc unmount riêng field; chỉ set value='' chưa đủ reset show.

**Ma trận kiểm tra tối thiểu**

| Ca | Kỳ vọng |
| --- | --- |
| Payload client | Đúng endpoint/method/3 key/CSRF/credentials, không identity |
| 204 rỗng | Resolve void, không response.json |
| Mọi lỗi trong API table | Status/code/field map đúng, không raw body |
| Local invalid/Unicode ở biên | Lỗi đúng, không trim, không request |
| Double submit pending | Chỉ một request |
| Success/422/403/503/network | Reset đúng, một toast, không retry |
| Rời form trước 204/401/422 | Không state/toast/callback muộn |

Node test runner kiểm tra helper/client. DOM/focus/toast/show-hide cần browser
ở 007; không coi helper test là đã kiểm tra giao diện.

**Done:** Client/helper tests đạt; form có thể nối ở 006 mà không đưa business
logic lên page. Đáp ứng phần form/client AC-02, AC-03, AC-12, AC-13, AC-14.

### F014-006 — Tab Tài khoản, lifecycle và bản dịch

- [x] Hoàn thành F014-006.

**Where**

- Sửa `frontend/src/lib/features/settings/SettingsPanel.svelte`.
- Sửa `frontend/src/lib/pages/WorkspacePage.svelte` cho props/composition.
- Sửa `frontend/src/App.svelte` cho notice hết phiên qua auth owner.
- Sửa ba catalog `frontend/src/lib/i18n/locales/vi-VN/translation.json`,
  `frontend/src/lib/i18n/locales/en-US/translation.json`,
  `frontend/src/lib/i18n/locales/ru-RU/translation.json`.
- Đọc `frontend/src/lib/features/auth/AuthToastLayer.svelte` để dùng notice/
  Toaster hiện có; không cần thêm hệ thống thông báo.

**Work — thực hiện theo thứ tự**

1. Personal settings có state appearance | account, mặc định appearance.
   System=true vẫn chỉ LLM/children, không bắt caller system truyền CSRF/onexpired.
2. Thêm props csrfToken/onexpired cho personal và active. Active mặc định false
   nếu caller chưa truyền. Chỉ mount form khi
   `!system && active && selectedTab === 'account'`.
3. Workspace truyền `active={activeView === 'settings'}`, CSRF và callback hết
   phiên. Không chỉ kiểm tra tab: page giữ panel hidden khi chuyển chat/project.
   Không lưu hoặc xử lý mật khẩu trong page.
4. Chọn account → form mới rỗng. Chọn appearance/rời settings → unmount form,
   cleanup. Giữ tab trong instance SettingsPanel, không storage/query URL.
   Quay lại vẫn là tab đã chọn nhưng form mới rỗng. Reload/đổi user bắt đầu lại
   appearance như lần khởi tạo đầu.
5. Tablist dọc, liên kết ID/ARIA và roving tabindex. Up/Down vòng qua hai tab;
   Home/End tới đầu/cuối; di chuyển focus đồng thời kích hoạt tab. Panel ẩn không
   chứa input focusable hoạt động. Giữ logic system settings LLM.
6. Đọc App.clearSession, WorkspacePage.clearSession, notifyAuth, AuthToastLayer:
   hiện clearSession chỉ clear state, chưa phát toast. Cho callback nhận UiMessage
   tùy chọn; caller cũ không truyền message giữ hành vi cũ.
7. Form 401 truyền `message('account.password.errors.sessionExpired')`.
   Workspace giữ guard expired, dispose rồi chuyển message lên App. App clear
   identity/CSRF, chuyển login và gọi notifyAuth('error', message) một lần.
   Key mới không bật action retry của AuthNotice; không retry POST password.
   Auth toast nằm ngoài keyed workspace nên cleanup form không xóa nó.
8. Presence/request khác đã clear session trước thì guard/lifecycle bỏ callback
   muộn từ form. Không sửa toàn bộ chính sách toast của các flow auth khác.
9. Hoàn thiện key ở cả ba catalog, giữ các key form đã thêm ở 005. Namespace
   account.password.* và key tab settings.account. Bộ key tối thiểu: title,
   current, new, confirmation, help, submit, submitting, success, show/hide cho
   từng trường; errors.required, length, mismatch, unchanged, currentIncorrect,
   forbidden, unavailable, resultUnknown, sessionExpired, invalid.
   Dùng tên key nhất quán giữa helper/client/form, không để text hardcode.
10. Locale cập nhật label/helper/error/toast qua UiMessage; không reset field/
    tab hoặc gửi lại request. Theme chỉ thay giao diện. Không đổi ngôn ngữ LLM.
11. LanguageSelector/ThemeSelector vẫn ở Giao diện. Dùng CSS/token và responsive
    hiện có; không chuyển bộ chọn sang Account hoặc sửa layout ngoài feature.

**Kiểm tra trước khi bàn giao**

- User/admin đều thấy Account; tự đổi không phụ thuộc canAdmin.
- System LLM không mount form, không ID trùng giữa hai SettingsPanel.
- Chuyển tab/view, Back/Forward, logout, đổi user xóa input dù panel chỉ hidden.
- Ba catalog cùng key, không label rỗng hoặc key thô.
- 401 tạo một auth toast sau khi login hiện; current sai 422 giữ workspace.
- Tab/Arrow/Home/End và locale selector không tạo request đổi mật khẩu.

**Done:** AC-01, AC-12, AC-13, AC-14 có đường thực thi rõ. App chỉ được mở rộng
notice tùy chọn; không đổi session contract hoặc tạo Toaster/state toàn cục mới.

### F014-007 — Browser, tích hợp và regression

- [x] Hoàn thành F014-007.

**Where:** Tạo `frontend/tests/account-settings-browser.mjs`,
`frontend/tests/account-settings-e2e.mjs`,
`tests/test_f014_007_password_e2e.py`. Mở rộng regression liên quan hiện có
khi cần kiểm tra hợp đồng, không sửa test ngoài phạm vi để che lỗi.

**Work — thực hiện theo thứ tự**

1. Đọc README/AGENTS, xác nhận Playwright/Chromium và frontend build. Lệnh tạo
   dist/log hoặc cài prerequisite phải thuộc phạm vi đã báo/được duyệt.
   Browser test skip phải được báo là chưa xác minh, không coi là pass.
2. HTTP giả học cấu trúc frontend/tests/admin-browser.mjs: serve frontend/dist
   trên cổng tạm, fake HTTP boundary, thu payload/số lần request password.
   Không cần DB/provider thật cho script này.
3. Ưu tiên locator role/name/label; auto-wait/poll điều kiện thay sleep để chờ
   toast. Thu pageerror/console error để phát hiện runtime lỗi. Browser/server
   luôn cleanup trong finally kể cả assert thất bại.
4. Chạy ma trận bên dưới. Ca nghiệp vụ có thể chạy một locale; smoke layout/
   label phải có vi-VN/en-US/ru-RU, light/dark và desktop/mobile. Không nhân mọi
   ca theo mọi tổ hợp nếu không thêm coverage.
5. Python wrapper dùng test_f005_007_e2e disposable fixture, fake providers,
   migrations và backend/cổng tạm như test_f012_005_accounts_e2e. Python cấp môi
   trường cho script account-settings-e2e; không chạy trực tiếp vào app đang dùng.
6. E2E thật không mock password/login/session/DB. Dùng context A1/A2 độc lập
   của cùng user, context B1 của user khác.
7. Snapshot hash, role/quyền, session ID/token_hash/CSRF/expiry và audit bằng test
   DB trước submit. Đổi qua UI A1, assert success toast/form rỗng; A1 còn dùng,
   A2 bị 401, B1 còn dùng. Sau đó mới mở login để chứng minh old sai/new đúng.
   Login mới sẽ thêm session nên không đếm session snapshot sau bước login đó.
8. Chạy cho user/admin; giữ test reset admin để chứng minh reset vẫn xóa mọi
   session, khác use case tự đổi.
9. Chạy full backend suite đúng AGENTS.md cùng frontend tests/build/lint/
   format:check và browser regression đã chỉ định. Focused test không thay full
   suite. Không chạy hai backend suite có shared fixture cùng lúc.
10. Báo command và số pass/fail/skip thực tế. Phân biệt feature failure, regression
    có sẵn và prerequisite thiếu bằng bằng chứng; không xóa hoặc nới assert để
    báo đạt. Không chạy provider thật hoặc reset database ứng dụng.

**Ma trận browser HTTP giả**

| Ca | Quan sát bắt buộc |
| --- | --- |
| Settings → Account | Tab/panel đúng, 3 input rỗng; Appearance mặc định khi khởi tạo |
| Rỗng/ngắn/mismatch/unchanged | Một toast, đúng field/focus, 0 request |
| Paste/Unicode/hiện-ẩn từng trường | Không đổi chuỗi, toggle chỉ đổi field của nó |
| Pending, click/Enter lặp | Một request; disabled input/submit, vẫn điều hướng được |
| 204 | Một success toast, input rỗng và type=password, identity còn |
| 422 current sai | Một error toast, đúng field, input xóa, workspace còn |
| 403/503/network | Toast phù hợp, input xóa; network báo chưa xác định, không retry |
| 401 | Login hiện, một auth toast còn sau unmount, không thêm POST password |
| Hoãn response rồi đổi tab/view/user | Release response cũ không toast/callback làm hết phiên user mới |
| Toast mở rồi đổi locale | Dịch cập nhật, không request; dismiss rồi không tự sống lại |
| Keyboard/mobile/theme | Focus/tab/label đúng, không tràn ngang hoặc mất khả năng thao tác |
| Storage/log | Không mật khẩu trong storage/URL/console; chỉ ở request cần gửi |

Dùng marker giả cho test; không in mật khẩu trong báo cáo lỗi. Screenshot không
chụp input đang hiện plaintext; ghi trong logs ignored nếu cần.

**Done:** AC-01 đến AC-15 có bằng chứng đúng tầng. Full suite/frontend/browser
bắt buộc đạt. Nếu còn blocker, skip hoặc failure liên quan, để task unchecked
và ghi chính xác mục chưa xác minh.

### F014-008 — Đồng bộ tài liệu sau triển khai

- [x] Hoàn thành F014-008.

**Where:** Sửa `specs/02-architecture.md`,
`specs/to-be/administrator-operations.md` và cập nhật kết quả trong
`specs/feat/F014-self-service-password-change.md`.

**Work — thực hiện theo thứ tự**

1. Chỉ bắt đầu sau khi 007 có đủ bằng chứng đạt. Đọc diff production/test để dùng
   đúng tên endpoint/hàm/file cuối cùng, không ghi thiết kế chưa làm là hiện trạng.
2. Architecture: ghi tab Account, use case/API, transaction giữ phiên hiện tại/
   thu hồi phiên khác. Không nói admin reset giữ phiên; không sửa target section
   hoặc kiến trúc không liên quan.
3. Administrator-operations: chỉ đổi trạng thái mục tự đổi mật khẩu, link F014.
   Không đánh dấu toàn tài liệu to-be xong vì vẫn còn nghiệp vụ khác. Không
   thêm bản sao lệnh chạy app/test ở đây.
4. F014: ghi bảng task/AC, test/quan sát, command đã chạy, pass/fail/skip và giới
   hạn còn lại. Dùng số output thực tế, không ước tính.
5. Tick từng task/AC có bằng chứng. Chưa chạy PostgreSQL/browser hoặc còn lỗi
   liên quan thì để unchecked; không đổi tiêu chí để khớp implementation thiếu.
6. Kiểm tra link/path, task ID duy nhất và quy tắc toast/role/session/no migration
   khớp code. Chạy diff check và kiểm tra không có generated output/secrets.
7. Báo file production/config đã đổi, vai trò hàm quan trọng, nguồn legacy
   tham khảo/thích nghi, kết quả kiểm thử và phần chưa hoàn tất theo skill.

**Done:** Tài liệu khớp hành vi đã kiểm chứng, không mất backlog hoặc tick nhầm.
F014-001 đến F014-008 đã hoàn tất; bằng chứng nghiệm thu nằm ở phần kết quả kiểm chứng.

### Ma trận truy vết nghiệm thu

| Tiêu chí | Task chịu trách nhiệm | Bằng chứng chính |
| --- | --- | --- |
| AC-01 | 006, 007 | Tab/panel thật, personal và system đúng phạm vi |
| AC-02 | 005, 006, 007 | DOM/keyboard/show-hide/responsive |
| AC-03 | 001, 002, 003, 005, 007 | Contract/service/HTTP trực tiếp/local validation |
| AC-04 | 002, 003, 007 | Current sai 422, session còn |
| AC-05 | 002, 003, 007 | Actor/cookie thật, snapshot quyền và tài khoản khác |
| AC-06 | 002, 007 | Verify hash, login bằng mật khẩu cũ/mới |
| AC-07 | 002, 004, 007 | Snapshot A1/A2/B1 trước/sau commit |
| AC-08 | 002, 003, 004 | HTTP từ chối, kiểm tra lại sau chờ khóa |
| AC-09 | 001, 003, 007 | Marker bí mật/no-store/no Set-Cookie |
| AC-10 | 002, 004 | Inject lỗi trước commit thật, đọc DB mới sau rollback |
| AC-11 | 004 | Tranh chấp PostgreSQL có kiểm soát |
| AC-12 | 005, 006, 007 | Pending/reset show-hide/navigation/unmount |
| AC-13 | 005, 006, 007 | Hoãn response, instance mới, không retry POST |
| AC-14 | 005, 006, 007 | Một toast/notice, ba locale, ARIA/storage |
| AC-15 | 003, 006, 007, 008 | Regression đầy đủ và kết quả ghi trung thực |

Lệnh chuẩn vẫn nằm trong README.md và AGENTS.md. Focused test theo tên file ở
mỗi task phục vụ vòng phát triển; không thay full suite. Không commit build,
cache, logs hoặc screenshot. Không chạy E2E vào database ứng dụng.
