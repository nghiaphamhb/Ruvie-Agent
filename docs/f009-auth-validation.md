# F009 - Báo cáo triển khai và kiểm chứng

Ngày kiểm chứng: 2026-10-12.
Feature: [Trang đăng nhập và đăng ký Ruvie Agent](../specs/feat/F009-auth-pages-registration.md).
Trạng thái: hoàn tất F009-001 đến F009-006.
Phạm vi: code, migration, asset, test và tài liệu trong worktree. Chưa áp dụng migration vào database phát triển hoặc triển khai lên môi trường bên ngoài.

## Kết quả kiểm tra

| Kiểm tra | Kết quả | Bằng chứng tại workspace |
|---|---|---|
| Backend suite theo README | 166 test; 166 pass, 0 fail, 0 skip | `logs/f009/backend-tests.txt`; có Docker/PostgreSQL và browser E2E |
| Frontend suite | 33 test; 33 pass, 0 fail, 0 skip | `logs/f009/frontend-tests.txt` |
| Frontend production build | Pass | `logs/f009/frontend-build.txt` |
| Auth browser | 36 check pass | `logs/f009/auth-browser-tests.txt` |
| Browser hồi quy workspace/locale/upload/LLM | 66 check pass | `logs/f009/workspace-browser-tests.txt` |
| Browser → backend → PostgreSQL trên build cuối | 1 test pass, 0 fail, 0 skip | `logs/f009/auth-backend-browser.txt` |
| Migration offline SQL | Pass trong backend suite | `EmailMigrationSqlTests.test_offline_sql_enforces_case_insensitive_uniqueness` |
| Migration upgrade/downgrade/collision | Pass trên PostgreSQL dùng riêng cho test | `EmailPostgresTests` |
| Git whitespace check | Pass | `git diff --check` |
| Logo đúng phiên bản | Hash SHA-256 bản copy và logo v2 trùng nhau | `frontend/src/lib/assets/auth/ruvie-logo.png` và `output/branding/ruvie-logo-navy-v2.png` |

Các lệnh chính đã chạy:

- Từ root: `.\.venv\Scripts\python.exe -m unittest discover -s tests`.
- Từ root: `npm.cmd --prefix frontend test`.
- Từ root: `npm.cmd --prefix frontend run build`.
- Từ root: `node frontend/tests/auth-browser.mjs`.
- Từ root: `node frontend/tests/llm-browser.mjs`.
- Chạy riêng browser E2E mới trên build cuối: `.\.venv\Scripts\python.exe -m unittest test_f009_006_registration_e2e.RegistrationPostgresTests.test_browser_register_reload_logout_and_login_against_active_backend`, với PYTHONPATH gồm `tests` và `backend`.
- Browser dùng Playwright có sẵn và Microsoft Edge đã cài. Không thêm dependency runtime.
- Backend test dùng database PostgreSQL/pgvector tạm của fixture. Không dùng database phát triển hoặc provider thật.

Lệnh chạy và cấu hình browser chuẩn được mô tả trong [README](../README.md).
Log có cảnh báo deprecation sẵn có của Starlette TestClient/httpx. Cảnh báo này không làm test thất bại; không thay dependency ngoài phạm vi feature.

## Tệp sản phẩm và cấu hình

| Tệp | Thay đổi; input/output; lý do |
|---|---|
| `backend/ruvie/contracts/auth.py` | Thêm `RegisterRequest`, `normalize_identity`, `validate_email`. Nhận ba string; trả tên/email đã chuẩn hóa và password nguyên vẹn. Strict type, giới hạn độ dài, định dạng email và extra-forbidden bảo vệ biên HTTP. LoginRequest giữ chính sách password cũ. |
| `backend/ruvie/services/auth.py` | Thêm `RegisteredAccount`, `EmailTaken`, `AuthService.register`, `_stage_session`. Register nhận tên/email/password, trả user và CreatedSession. Flush User trước session để bảo đảm foreign key; commit chung một lần; rollback khi lỗi. Chỉ constraint email được chuyển thành EmailTaken. create_session tái sử dụng helper và giữ hành vi login. Không tạo role/membership/grant. |
| `backend/ruvie/api/auth.py` | Thêm `RegistrationRoute` để kiểm tra Origin trước parse và serialize validation không phản chiếu password. Thêm `POST /auth/register`: 201 + AuthResponse/cookie; 403/409/422/500 theo spec. `_set_session_cookie` dùng chung cho login/register. Route chỉ xử lý HTTP và gọi service. |
| `backend/ruvie/models/auth.py` | Thêm `uq_users_email_lower` vào User metadata. Index theo lower(email) khớp migration; giữ constraint email cũ. |
| `backend/migrations/versions/0009_users_email_lower_unique.py` | Upgrade thêm unique index; downgrade chỉ bỏ index mới. PostgreSQL tự từ chối dữ liệu case-only collision trong transaction. Không sửa account hoặc migration cũ. |
| `frontend/src/App.svelte` | Thêm `acceptSession`, `submitRegister`, `checkSession`, `clearAuthErrors`. Nhận AuthSession, giữ user/CSRF trong bộ nhớ, vào workspace và tải project. Lỗi project không bị báo thành lỗi đăng ký. AuthPage thay topbar/form auth cũ; workspace orchestration giữ nguyên. |
| `frontend/src/lib/auth-api.ts` | Thêm `register` và `AuthApiError.fieldErrors`. Gửi đúng ba trường với same-origin cookie; trả AuthSession hoặc safe UiMessage/field errors. Không retry tự động hoặc render raw detail. Login/logout/session giữ hợp đồng hiện có. |
| `frontend/src/lib/auth-form.ts` | `validEmail`, `validateRegistration`, `validateLogin` nhận string và trả lỗi có translation key. Độ dài password/name tính theo Unicode code point. Đăng ký yêu cầu email có domain dấu chấm; login vẫn chấp nhận local domain và password cũ. Đây là UX validation; backend vẫn kiểm tra lại. |
| `frontend/src/lib/components/AuthPage.svelte` | Layout kính/nền/asset/logo chung; mode `login/register` qua query/History API; Back/Forward và focus. Nhận busy/checking/error/callback. Remount form xóa password. CSS chỉ nằm trong auth, có mobile scrolling và fallback không blur. Card hiện rộng 360 px; khoảng cách giảm theo viewport thấp. Viền 1 px/alpha 0.18, nền alpha 0.40; canvas scale cùng gradient theo khung. |
| `frontend/src/lib/components/LoginForm.svelte` | Hai trường, local validation, focus lỗi và callback login. Input password cũ không bị buộc theo độ dài đăng ký mới. Label/autocomplete/aria-busy giữ rõ ràng. |
| `frontend/src/lib/components/RegisterForm.svelte` | Bốn trường giao diện, gồm xác nhận mật khẩu chính xác trên client. Callback register chỉ gửi ba trường API. Nhận lỗi server theo whitelist; xóa cả hai mật khẩu khi unmount/success; không có ô role/project. |
| `frontend/src/lib/components/PasswordField.svelte` | Input bindable và nút hiện/ẩn với aria-label/aria-pressed. Giữ password nguyên vẹn, cho paste/autocomplete, khóa khi busy và xóa khi unmount. Nút navy tạo tương phản cho icon Figma nguyên bản. |
| `frontend/src/lib/i18n/locales/vi-VN/translation.json` | Thêm nhãn và lỗi đăng ký tiếng Việt; không thiếu hoặc rỗng key. |
| `frontend/src/lib/i18n/locales/en-US/translation.json` | Thêm cùng logical key tiếng Anh; là catalog chuẩn cho MessageKey. |
| `frontend/src/lib/i18n/locales/ru-RU/translation.json` | Thêm cùng logical key tiếng Nga; kiểm tra nội dung dài trên mobile. |

## Asset và tài liệu

- `frontend/src/lib/assets/auth/outer-ring.png`: nhóm 203:4, crop 192×192, canvas ngoài.
- `outer-left.png`: nhóm 203:1007, crop 476×442, canvas ngoài.
- `outer-right.png`: nhóm 203:2010, crop 483×166, canvas ngoài.
- `inner-ring.png`: nhóm 101:12080, crop 192×89, canvas trong.
- `inner-curl.png`: nhóm 101:13083, crop 476×443, canvas trong.
- `inner-left.png`: nhóm 101:17134, crop 293×286, canvas trong.
- `inner-right.png`: nhóm 101:18137, crop 206×132, canvas trong.
- `eye-hide.svg`: icon 101:14116, giữ root size 11.3833×11.3833, trong nút 44×44.
- `ruvie-logo.png`: bản copy nguyên vẹn của logo v2 có alpha; CSS đổi màu hiển thị thành trắng.
- [Asset README](../frontend/src/lib/assets/auth/README.md): nguồn, crop/slot và khác biệt đã chấp nhận.
- [README](../README.md): đăng ký, giới hạn quyền tài khoản mới, nguồn port và lệnh browser checks.
- [Database setup](database-setup.md): unique email, xung đột dữ liệu cũ và downgrade.
- [Spec F009](../specs/feat/F009-auth-pages-registration.md): trạng thái sáu task và tiêu chí nghiệm thu.

PNG export Figma đã gộp blend/nền và crop theo frame cha.
AuthPage dùng canvas gradient tham chiếu, đặt asset đúng vị trí crop và không kéo giãn ảnh.
SVG trang trí trả màu hồng khác screenshot đã được loại bỏ.
Không chỉnh pixel PNG, không dùng screenshot toàn trang làm asset, không có URL asset tạm trong code.

## Nguồn legacy được áp dụng

| Nguồn | Phần dùng | Phần loại bỏ hoặc thay đổi |
|---|---|---|
| `references/src/routes/auth/+page.svelte::chooseAuthMode`, `submitHandler`, `signInHandler`, `signUpHandler` | Chuyển form, focus, submit theo mode và nhận phiên sau thành công. | Port sang Svelte 5; dùng History API. Không lấy socket, SvelteKit stores/routing hoặc localStorage token. |
| `references/src/lib/components/common/SensitiveInput.svelte` | Toggle password, autocomplete và aria-pressed. | Dùng CSS/i18n active và icon Figma; bỏ legacy settings store. |
| `references/src/lib/apis/auths/index.ts::userSignIn`, `userSignUp` | Tách fetch khỏi component. | Dùng client active; payload display_name/email/password; không avatar hoặc JWT. |
| `references/backend/ruvie/routers/auths.py::signup`, `signup_handler` | Validate → kiểm tra trùng → tạo account → tạo session. | Nghiệp vụ ở AuthService, scrypt/PostgreSQL/cookie active. Không auto-admin/default group hoặc HTTPException trong service. |
| `references/backend/ruvie/models/auths.py::SignupForm`, `AuthsTable.insert_new_auth` | Ba trường identity và nguyên tắc account/credential cùng transaction. | Giữ User/AuthSession active; không thêm bảng Auth hoặc bcrypt legacy. |

Không chạy, sửa hoặc import runtime của references. Không dùng archive.

## Bằng chứng cho từng tiêu chí

| AC | Bằng chứng |
|---|---|
| 01 | AuthPage chung và ảnh render login/register; logo hash trùng v2, một chữ R. |
| 02 | Asset README chỉ rõ node/slot/crop; browser kiểm tra mọi ảnh đã tải; đối chiếu render desktop với screenshot Figma. |
| 03 | AuthApiTests cũ và browser hồi quy login; test local-domain/short password giữ tương thích. |
| 04 | RegistrationContractTests và RegistrationApiTests từ chối type sai/trường thừa; browser form có bốn trường; request API vẫn có ba trường. |
| 05 | Test normalization, boundary 12/128, 11/129 và Unicode; validator frontend/backend; password whitespace được kiểm tra cả E2E. |
| 06 | RegistrationApiTests kiểm tra 201, AuthResponse, HttpOnly/Secure/SameSite/path/max-age; browser đọc được phiên mà không thấy cookie qua document.cookie. |
| 07 | Service test verify_password/hash salted và token hash khác raw token. |
| 08 | PostgreSQL index test, duplicate API test và hai request đồng thời có kết quả 201/409; một user/một session. |
| 09 | Unit fault-injection sau flush/commit và PostgreSQL session failure xác nhận rollback không có user/session dở. |
| 10 | Offline SQL, upgrade/downgrade/re-upgrade và collision test trên database tạm. |
| 11 | API Origin test, cookie/logout/CSRF test cũ và mới. |
| 12 | PostgreSQL E2E: project list rỗng; revision status 404; retrieve/chat không chứa dữ liệu/citation riêng; không membership/grant. Service chỉ insert User/AuthSession. |
| 13 | Browser E2E thật trên build cuối: register → workspace → reload → logout → duplicate → login; user ID giữ nguyên. |
| 14 | Auth browser: query/mode, Back/Forward, xóa password/show state, focus; E2E đã đăng nhập mở register không hiện auth form. |
| 15 | API validation redaction/internal failure; client whitelist; browser 409/422/500 hiển thị đúng trường/form và không raw SQL detail. |
| 16 | Auth browser kiểm tra busy, khóa submit/mode và Enter không tạo request thứ hai; client test không retry mạng/500. |
| 17 | PasswordField type=button, aria/autocomplete; browser toggle và focus; không chặn paste. |
| 18 | Catalog tests và browser đổi ba locale khi lỗi đang hiển thị; register mobile kiểm tra label/text dài. |
| 19 | Hai mode qua bảy viewport trong spec; page riêng 640×360 CSS px với deviceScaleFactor=2; scroll đến submit, không cuộn ngang. |
| 20 | Browser kiểm tra input/nút 44 px, font 14/16 px, outline focus, contrast icon ≥3:1 và chữ trên kính ≥4.5:1. |
| 21 | 66 check hồi quy workspace/locale/upload/LLM và backend suite; không đổi theme/workspace controls. |
| 22 | 166 backend + 33 frontend + build + 36 auth/66 hồi quy + browser backend build cuối; không có test skip. |
| 23 | README, database setup, asset README và bảng nguồn port trong báo cáo/spec. |

Ảnh QA tại workspace:
- [Login desktop](../logs/f009/login-1920.png).
- [Register mobile](../logs/f009/register-375.png).
- [Register viewport nhỏ](../logs/f009/register-320.png).

## Điều kiện dùng với database hiện tại

Chạy migration mới theo [database setup](database-setup.md) trước khi dùng registration với database hiện tại.
Chưa áp dụng migration vào database phát triển trong phiên này.
Nếu account cũ có email khác nhau chỉ ở hoa/thường, migration dừng; không tự hợp nhất hoặc xóa account.
Font hiện có thay Gilroy; form lớn hơn và card tối hơn để đạt readability/contrast theo spec.
Khôi phục mật khẩu, xác minh email, invitation/admin UI vẫn ngoài phạm vi đã thống nhất.


## Chỉnh scale và opacity theo phản hồi (2026-10-12)

- Bỏ chiều cao stage cố định 768px; giới hạn chiều cao tối thiểu theo viewport và giảm chiều rộng tối đa còn 1093px. Card 360px, logo 112px; thu gọn padding và khoảng cách.
- Nền card giảm alpha từ 0.60 xuống 0.45; giữ input/nút 44px, chữ input 16px và nhãn/helper 14px. Fallback không hỗ trợ blur vẫn là nền đặc.
- Regression mới tái hiện lỗi cũ: toàn bộ card đăng ký không nằm trong viewport 1526×702 ở zoom 100%. Sau sửa, login/register đều vừa ở 1920×1080, 1366×768, 1526×702 và 1280×720, không phải cuộn dọc. Đăng ký cũng vừa viewport 1526×702 với cả tiếng Việt, Anh và Nga. Viewport thấp/mobile vẫn cuộn được khi cần.
- Build thành công; 33 frontend tests, 43 auth browser checks và 66 workspace browser checks pass. Tương phản chữ trên kính vẫn đạt ≥4.5:1. Backend không thay đổi trong lần chỉnh giao diện này.
- Ảnh QA mới: `logs/f009/register-1526.png`, cùng ảnh login/register desktop và mobile đã cập nhật.

## Chỉnh theo ảnh mẫu 2 và thêm xác nhận mật khẩu (2026-10-12)

Yêu cầu mới thay thế scope cũ không có ô nhập lại mật khẩu. Backend/API không đổi.

| File production thay đổi | Vai trò và kết quả |
|---|---|
| `AuthPage.svelte` | Khung co theo viewport, compact spacing khi desktop cao ≤740px; flex-shrink:0 cho nội dung dài cuộn được. Viền 1px/alpha 0.18, nền alpha 0.40. Canvas giữ gradient/PNG cùng scale; clientWidth/clientHeight xác định scale phủ khung. |
| `LanguageSelector.svelte` | Thêm prop compact mặc định false. Auth dùng một dropdown bo tròn; label ẩn thị giác nhưng vẫn là tên truy cập. Callback setLocale và variant workspace giữ nguyên. |
| `RegisterForm.svelte` | Có bốn trường; lưu confirmation trong state, validate trước onregister, focus vào ô thiếu/không khớp. Chỉ gửi tên/email/password, xóa cả hai mật khẩu khi success/unmount. Bỏ dòng mô tả để form gọn hơn. |
| `PasswordField.svelte` | Nhận id, reuse cho hai ô mật khẩu; nút show/hide độc lập và có nhãn theo từng ô. Icon nằm trên nền trắng, dùng CSS filter/opacity để đạt tương phản. |
| `auth-form.ts` | validateRegistration nhận confirmation; yêu cầu giá trị không rỗng và khớp chính xác, không trim/normalize Unicode. AuthField thêm password_confirmation chỉ để biểu diễn lỗi frontend. |
| Catalog en-US/vi-VN/ru-RU | Thêm nhãn nhập lại mật khẩu, show/hide confirmation và thông báo không khớp. |

Nguồn reuse: `references/src/routes/auth/+page.svelte::signUpHandler` so sánh password với confirmPassword trước userSignUp. Active luôn yêu cầu xác nhận, dùng inline error/focus thay toast/config legacy. Tái sử dụng LanguageSelector và PasswordField active; không thêm dependency.

Lỗi đã tái hiện trước sửa:
- Frame vượt đáy viewport 1280×605 dù document không có thanh cuộn; kiểm tra cũ chỉ đo scrollHeight nên bỏ sót vùng bị clip.
- Validator không yêu cầu xác nhận mật khẩu.
- Scale canvas cố định không phủ hết khung đăng ký, tạo dải màu ở mép.

Kết quả kiểm tra cuối:
- `npm.cmd --prefix frontend run build`: pass.
- `npm.cmd --prefix frontend test`: 34 pass, 0 fail, 0 skip.
- `node frontend/tests/auth-browser.mjs`: 52 checks pass. Đo cả frame/card trong viewport từ 1024×600; kiểm tra mobile/ba locale, mismatch không gọi API, focus confirmation, reset hai giá trị/show state, payload đúng ba trường, canvas phủ khung, border nhẹ và tương phản ≥4.5:1.
- `node frontend/tests/llm-browser.mjs`: 66 checks pass, gồm locale workspace.
- Với PYTHONPATH=backend;tests và browser paths theo README: `.venv/Scripts/python.exe -m unittest test_f009_006_registration_e2e.RegistrationPostgresTests.test_browser_register_reload_logout_and_login_against_active_backend`: 1 pass, 0 skip, 48.953s. Database PostgreSQL tạm; không tác động database phát triển.
- `git diff --check`: pass. Backend suite đầy đủ không chạy lại vì lần chỉnh này không đổi backend.
- Đối chiếu frontend đang chạy tại localhost:5173 ở 1280×605, zoom 100%: cả form và frame nằm trong viewport. Ảnh build cuối: `logs/f009/login-1280.png`, `logs/f009/register-1280.png`, `logs/f009/register-375.png`.

## Port toast và chỉnh nội dung auth (2026-10-12)

| File | Thay đổi |
|---|---|
| `frontend/package.json`, `frontend/package-lock.json` | Thêm dependency svelte-sonner chính xác 1.2.1, peer Svelte ^5.0.0. Không chạy hoặc import runtime references. |
| `AuthToastLayer.svelte` | Port Toaster richColors/top-right/closeButton từ references layout, dùng CSS active thay class Tailwind. Nhận notice/ondismiss/onretry; render thông báo an toàn theo locale, stable toast ID, tự ẩn 5s và retry mạng. |
| `App.svelte` | notifyAuth nhận success/error và UiMessage; dismissAuthNotice chỉ xóa đúng notice ID. Gọi ở phản hồi login/register/checkSession; host root giữ toast sau auth → workspace. |
| `AuthPage.svelte` | Không chuyển lỗi server/retry vào form nữa. Thêm margin-top 16px trước submit, giữ padding card và nút. |
| `LoginForm.svelte` | Bỏ banner lỗi server trong form; giữ lỗi local và focus vào trường đầu tiên. |
| `RegisterForm.svelte` | Lỗi API được toast; vẫn đánh dấu/focus trường server lỗi. Lỗi local vẫn inline. Xóa hint độ dài và tham chiếu aria-describedby tới hint. |
| Catalog en-US/vi-VN/ru-RU | Thêm nhãn vùng/nút đóng notification và thông báo login/register thành công. |

Nguồn: `references/src/routes/+layout.svelte:1297` (Toaster); `references/src/routes/auth/+page.svelte::signInHandler`, `signUpHandler`, `setSessionUser` (toast.error/success). Loại bỏ raw error string, localStorage token và socket của legacy. API/cookie/CSRF và chính sách mật khẩu active giữ nguyên.

[Sonner upstream](https://github.com/wobsoriano/svelte-sonner) là nguồn đối chiếu API Svelte 5; version và peer được xác minh bằng npm registry.

Kiểm tra đã hoàn tất: build pass; 34 frontend unit tests pass, 0 fail/skip; 62 auth browser checks pass. Các case mới kiểm tra server error ở toast, card không đổi chiều cao, success tồn tại trong workspace, close/auto-close, repeated response không trùng toast, đổi locale tại chỗ, mobile fit và retry transport failure. Ảnh `logs/f009/login-toast-mobile.png`.

Kiểm tra hồi quy cuối cho lần port toast:
- `node frontend/tests/llm-browser.mjs`: 66 checks pass. Assertion login của i18n-browser và llm-browser được chuyển từ banner alert sang Sonner toast; kiểm tra đổi locale/raw-error giữ nguyên.
- Với browser paths và PYTHONPATH=backend;tests như README: `.venv/Scripts/python.exe -m unittest test_f009_006_registration_e2e.RegistrationPostgresTests.test_browser_register_reload_logout_and_login_against_active_backend`: 1 pass, 0 skip, 49.532s trên PostgreSQL tạm.
- `npm.cmd --prefix frontend run build`, `npm.cmd --prefix frontend test`, `node frontend/tests/auth-browser.mjs`, `git diff --check`: đều pass (34 unit tests, 62 auth checks). Full backend suite không chạy lại vì không có thay đổi backend trong lần port này.

## Đồng bộ dropdown và favicon R (2026-10-12)

- LanguageSelector compact dùng customizable native select khi hỗ trợ appearance:base-select: picker xanh navy, chữ trắng, bo góc 16px, option bo góc 10px và highlight/dấu chọn. Giữ select, label và setLocale hiện có; workspace variant mặc định giữ nguyên. Trình duyệt cũ fallback native select.
- frontend/public/favicon.png là bản sao nguyên vẹn ảnh R người dùng gửi (codex-clipboard-82bd5439-04f9-403e-955b-67b781e5d699.png). frontend/index.html khai báo icon PNG tại /favicon.png. Frontend đang chạy trả HTTP 200 cho icon.
- Browser QA mở picker kiểm tra computed option color trắng và nền picker xanh; ảnh logs/f009/language-dropdown.png. Keyboard test dùng Arrow để mở/di chuyển, Enter commit, Home về lựa chọn đầu theo hành vi customizable select.
- Build pass; auth browser 62 checks pass. Không đổi backend.

Kiểm tra cuối: npm.cmd --prefix frontend test pass; node frontend/tests/llm-browser.mjs 66 checks pass; git diff --check pass.

## Sửa nguồn favicon theo xác nhận của người dùng

Favicon hiện dùng frontend/public/favicon.svg, nhúng logo gốc output/branding/ruvie-logo-navy-v2.png và giới hạn viewBox vào chữ R trước chữ u. Không vẽ lại hình R. SVG đổi glyph sang trắng trên nền xanh; favicon PNG từ ảnh clipboard đã được xóa. frontend/index.html trỏ sang /favicon.svg để thay đường dẫn cũ. Build pass; kiểm tra trình duyệt HTTP 200, decode thành công và ảnh QA logs/f009/favicon-ruvie-r.png.
