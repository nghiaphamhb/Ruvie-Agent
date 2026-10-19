# F009 - Trang đăng nhập và đăng ký Ruvie Agent

## Goal

Xây dựng trang đăng nhập và đăng ký Ruvie Agent theo template Figma đã được chọn.
Hai trang dùng chung nền, logo, khối kính và cách hiển thị lỗi.
Người dùng đăng ký tài khoản bằng tên hiển thị, email và mật khẩu.
Hệ thống tạo phiên đăng nhập sau khi đăng ký thành công.
Tài khoản mới chưa có quyền truy cập project hoặc tài liệu.

- Ngày xác nhận plan: 2026-10-12.
- Trạng thái: đã triển khai và kiểm chứng F009-001 đến F009-006.
- Phạm vi tài liệu: yêu cầu và phương án triển khai F009. Bằng chứng hoàn thành: [báo cáo kiểm chứng](../../docs/f009-auth-validation.md). Migration chưa áp dụng vào database phát triển.

### Căn cứ thiết kế

| Nguồn | Mục đích |
|---|---|
| [Glass Effect Login Page (Ruvie Agent)](https://www.figma.com/design/fuAT0dAEjv9r3v54sdoVZW/Glass-Effect-Login-Page--Ruvie-Agent-?node-id=203-3) | Template nền xanh và bố cục đăng nhập. File key: `fuAT0dAEjv9r3v54sdoVZW`. Frame gốc: `203:3`, 1920 × 1080. |
| Frame Figma `206:14` | Khối form kích thước khoảng 410 × 459 px. Đây là nguồn thông số form đã được đọc bằng design context. |
| [Logo v2](../../output/branding/ruvie-logo-navy-v2.png) | Logo có một chữ R biểu tượng đóng vai trò chữ đầu của “Ruvie”. Đây là logo đã được người dùng chọn. |
| [Mẫu spec](F000-pattern.md) | Cấu trúc tài liệu feature. |
| [Kiến trúc](../02-architecture.md), [quyền truy cập](../03-access-control.md) | Tách xác thực tài khoản khỏi quyền truy cập dữ liệu. |

### Yêu cầu, nền tảng trước F009 và phương án triển khai

| Loại | Nội dung |
|---|---|
| **Spec yêu cầu** | Login và đăng ký có giao diện chung theo Figma. Dùng logo v2. Đăng ký tạo tài khoản thật và phiên đăng nhập. |
| **Code trước F009** | `backend/ruvie/api/auth.py` có `login`, `current_session`, `logout`. Chưa có đăng ký hoặc khôi phục mật khẩu. |
| **Code trước F009** | `AuthService` trong `backend/ruvie/services/auth.py` xác thực mật khẩu bằng scrypt. `create_session` lưu phiên và commit ngay. |
| **Code trước F009** | `User` trong `backend/ruvie/models/auth.py` có `email`, `display_name`, `password_hash`, `is_active`. Email hiện có unique constraint theo giá trị lưu. |
| **Code trước F009** | `frontend/src/App.svelte` quản lý user, CSRF và khôi phục phiên. `LoginForm.svelte` chỉ có email và mật khẩu. |
| **Code trước F009** | Frontend dùng Svelte 5, CSS cục bộ, i18next và ba locale Việt/Anh/Nga. Chưa có router hoặc thư viện UI. |
| **Phương án đề xuất** | Thêm API đăng ký vào router hiện có. Thêm phương thức nghiệp vụ vào `AuthService`. Tạo `AuthPage.svelte` và `RegisterForm.svelte`; tái sử dụng `LoginForm.svelte`. |
| **Phương án đề xuất** | Thêm migration mới cho email duy nhất không phân biệt hoa/thường. Không thêm bảng tài khoản hoặc bảng mật khẩu riêng. |

## User Story

- Là người đã có tài khoản, tôi muốn đăng nhập bằng email và mật khẩu để vào Ruvie Agent.
- Là người chưa có tài khoản, tôi muốn nhập tên hiển thị, email và mật khẩu để tạo tài khoản.
- Là người đăng ký thành công, tôi muốn vào ứng dụng mà không phải nhập lại thông tin đăng nhập.
- Là người dùng điện thoại hoặc bàn phím, tôi muốn đọc được nhãn, thao tác được mọi nút và nhận được thông báo lỗi rõ ràng.
- Là người quản lý dữ liệu, tôi muốn tài khoản mới chỉ đọc tài liệu sau khi được cấp quyền.

## Scope

### In

#### 1. Giao diện chung

- Giữ nền xanh, lớp nền lớn bo góc, các hình trang trí và khối kính ở giữa theo Figma.
- Hai form dùng cùng layout. Form đăng ký cao hơn theo nội dung.
- Thay “Your logo” bằng logo v2. Không thêm một chữ R khác cạnh logo.
- Sao chép logo vào `frontend/src/lib/assets/auth/ruvie-logo.png`.
- Giữ PNG gốc. Dùng CSS `brightness(0) invert(1)` chỉ trên ảnh logo để hiển thị trắng trên nền xanh.
- Tải từng asset trang trí và icon cần dùng về thư mục asset của frontend.
- Không dùng ảnh chụp toàn màn hình làm nền thay cho việc xây dựng form.
- Không dùng URL asset Figma tạm thời trong mã chạy.
- Không đưa hàng nghìn vector của nhóm trang trí thành DOM. Dùng asset xuất từ nhóm tương ứng nếu nhóm chứa quá nhiều vector.
- Giữ font stack hiện có của frontend. Figma dùng Gilroy nhưng frontend chưa có font này. Việc dùng font hiện có là khác biệt được chấp nhận.
- CSS của trang auth chỉ tác động trang auth. Giao diện workspace sau đăng nhập giữ hành vi hiện có.
- Tái sử dụng bộ chọn ngôn ngữ hiện có với variant compact trên auth: một dropdown bo tròn, nhãn truy cập ẩn về thị giác, không che form. Variant mặc định trong workspace giữ nguyên.

#### 2. Quy tắc layout và khả năng sử dụng

- Khối form desktop rộng tối đa 424 px; viewport desktop thấp dùng 416 px để giữ độ rộng nội dung khi padding tăng gấp đôi. Form không vượt chiều rộng viewport; cả khung nền và form phải vừa viewport desktop cao từ 600 px ở zoom 100% khi chưa hiển thị lỗi.
- Logo rộng 112 px; giảm còn 96 px khi viewport desktop cao không quá 740 px. Ảnh giữ đúng tỉ lệ.
- Tiêu đề 22 px; giảm còn 20 px trên viewport desktop thấp. Viền kính 1 px với alpha 0.18; nền kính alpha 0.40 và blur 9 px.
- Ô nhập và nút thao tác chính có chiều cao tối thiểu 44 px.
- Nội dung nhập có kích thước tối thiểu 16 px.
- Nhãn, thông báo lỗi và liên kết cuối form có kích thước tối thiểu 14 px.
- Có nhãn thật cho mỗi ô nhập. Placeholder không thay nhãn.
- Có outline khi focus bằng bàn phím. Màu chữ thường đạt tỉ lệ tương phản tối thiểu 4.5:1.
- Nút hiện/ẩn mật khẩu có vùng bấm tối thiểu 44 × 44 px và nhãn truy cập phù hợp trạng thái.
- Cho phép dán mật khẩu và sử dụng trình quản lý mật khẩu.
- Khi viewport thấp, trang auth được cuộn theo chiều dọc. Không khóa toàn trang bằng chiều cao cố định.
- Trên mobile, giảm padding form và cho phép hình trang trí bị crop theo nền. Form luôn đọc được và không có cuộn ngang.
- Không bổ sung animation trang trí. Transition hiện có phải tôn trọng `prefers-reduced-motion`.
- `backdrop-filter` không được hỗ trợ thì dùng màu nền khối form đủ đậm để nội dung vẫn rõ.

Kích thước ô nhập và chữ là điều chỉnh có chủ đích so với Figma.
Figma có ô nhập 32 px và dòng cuối khoảng 10 px.
Các điều chỉnh trên phục vụ thao tác mobile và đọc nội dung.

#### 3. Form đăng nhập

- Trường Email.
- Trường Mật khẩu.
- Nút hiện/ẩn mật khẩu.
- Nút “Đăng nhập”.
- Liên kết “Chưa có tài khoản? Tạo tài khoản”.
- Giữ `autocomplete="username"` cho email và `autocomplete="current-password"` cho mật khẩu.
- Đăng nhập dùng API hiện có. Không áp dụng độ dài tối thiểu mới của đăng ký cho mật khẩu tài khoản cũ.
- Không hiển thị “Forgot Password?” trong feature này vì backend chưa có luồng khôi phục.

#### 4. Form đăng ký

| Trường | Tên trong API | Quy tắc |
|---|---|---|
| Tên hiển thị | `display_name` | Chuỗi bắt buộc. Bỏ khoảng trắng hai đầu. Sau chuẩn hóa dài 1–255 ký tự. Chấp nhận tên tiếng Việt và Unicode. |
| Email | `email` | Chuỗi bắt buộc. Bỏ khoảng trắng hai đầu và chuyển thành chữ thường. Dài 3–320 ký tự. Kiểm tra định dạng ở backend; HTML email validation chỉ hỗ trợ UX. |
| Mật khẩu | `password` | Chuỗi bắt buộc, 12–128 ký tự. Không trim, không cắt ngắn, không chuẩn hóa Unicode. Không áp đặt thêm quy tắc phải có chữ hoa hoặc ký tự đặc biệt. |

- Thêm ô “Nhập lại mật khẩu” bắt buộc trên giao diện. So sánh chính xác với mật khẩu, gồm khoảng trắng và Unicode. Lỗi thiếu/không khớp hiển thị gần ô; focus vào ô lỗi; không gửi API.
- Chỉ ba trường trong bảng được gửi cho API. Giá trị xác nhận chỉ tồn tại trong form và được xóa khi chuyển mode hoặc đăng ký thành công.
- Không hiển thị dòng hướng dẫn độ dài mật khẩu theo phản hồi mới. Validator và API vẫn yêu cầu 12–128 ký tự.
- Cho phép hiện/ẩn mật khẩu.
- Dùng `autocomplete="name"`, `autocomplete="email"` và `autocomplete="new-password"` tương ứng.
- Nút chính: “Tạo tài khoản”.
- Liên kết cuối: “Đã có tài khoản? Đăng nhập”.
- Không có trường role, project, quyền truy cập, trạng thái hoạt động hoặc avatar.
- Không thêm checkbox điều khoản khi chưa có tài liệu điều khoản của sản phẩm.
- Không truy vấn DNS hoặc gửi email để kiểm tra địa chỉ trong feature này.
- Tên hiển thị được render như văn bản. Không dùng HTML do người dùng cung cấp.

#### 5. Tạo tài khoản và phiên đăng nhập

- Mở đăng ký tài khoản bằng mật khẩu trên ứng dụng.
- Backend sinh UUID cho user.
- Backend lưu mật khẩu băm bằng `hash_password` hiện có.
- Tài khoản mới có `is_active=True`.
- Backend tạo tài khoản và `AuthSession` trong cùng một transaction.
- Transaction là một nhóm thao tác cơ sở dữ liệu được lưu toàn bộ hoặc hủy toàn bộ.
- Không commit user trước rồi mới tạo session.
- Nếu ghi user hoặc session thất bại, rollback toàn bộ nhóm thao tác.
- Sau commit thành công, API đặt cookie và trả user cùng CSRF.
- Cookie giữ cấu hình hiện có: `ruvie_session`, HttpOnly, Secure, SameSite=Lax, Path=/, thời hạn 12 giờ.
- Raw session token chỉ có trong cookie. Database lưu SHA-256 của token.
- Không lưu mật khẩu, session token hoặc CSRF vào localStorage/sessionStorage.
- Việc lưu lựa chọn ngôn ngữ hiện có được giữ nguyên.

#### 6. Email duy nhất và dữ liệu cũ

- Email `Person@example.test` và `person@example.test` là cùng một địa chỉ tài khoản.
- Chuẩn hóa email mới trước khi tra cứu và lưu.
- Kiểm tra tồn tại trước insert để trả lỗi dễ hiểu.
- Unique index trong PostgreSQL là cơ chế quyết định cuối cùng khi nhiều yêu cầu đăng ký cùng lúc.
- Đề xuất index: `uq_users_email_lower` trên `lower(email)`.
- Giữ unique constraint hiện có trên email.
- Thêm khai báo index tương ứng trong model để metadata và migration không lệch nhau.
- Migration chỉ thêm index. Không sửa email, mật khẩu, ID hoặc quyền của tài khoản cũ.
- Nếu dữ liệu cũ có email xung đột khi chuyển chữ thường, migration thất bại rõ ràng và rollback.
- Không tự xóa hoặc hợp nhất tài khoản cũ. Người vận hành phải xử lý xung đột trước khi chạy lại.
- Không sửa migration đã áp dụng.
- `downgrade` chỉ bỏ index được thêm trong feature này.
- SQL migration phải xuất được ở chế độ offline. Không yêu cầu truy vấn dữ liệu bằng Python trong migration offline.

#### 7. Quyền truy cập tài khoản mới

- Đăng ký không tạo `Membership`, `Role` hoặc `AccessGrant`.
- Không tự cấp admin cho tài khoản đầu tiên.
- Không tự gán nhóm hoặc project.
- Client gửi trường quyền hoặc ID project thì request bị từ chối.
- User mới thấy danh sách project rỗng khi chưa được cấp quyền.
- User mới vẫn đi qua predicate đọc tài liệu và `AuthorizedRetrievalService` hiện có.
- Tài liệu không được phép đọc không xuất hiện trong context, kết quả retrieval hoặc citation.
- Feature không thay đổi nội dung revision, chunk, embedding profile, provider settings hoặc private blob storage.

#### 8. Ngôn ngữ và lỗi

- Mọi nội dung mới có bản dịch trong `vi-VN`, `en-US`, `ru-RU`.
- Dùng `UiMessage` và translation key hiện có.
- Khi đổi ngôn ngữ, nhãn và lỗi đang hiển thị đổi theo ngôn ngữ mới.
- Không gửi raw lỗi HTTP, SQL, provider hoặc traceback lên UI.
- Lỗi validation hiển thị gần trường liên quan.
- Lỗi mạng hoặc lỗi lưu dữ liệu hiển thị ở mức form.
- Vùng lỗi có thông báo cho trình đọc màn hình và không chỉ phân biệt bằng màu.
- Sau submit không hợp lệ, focus đến trường lỗi đầu tiên.
- Trong khi gửi request, khóa submit, đổi form và nút hiện/ẩn mật khẩu để tránh thao tác đua nhau.
- Form có `aria-busy`. Nút chính hiện “Đang đăng nhập…” hoặc “Đang tạo tài khoản…”.

### Out

- Khôi phục hoặc đổi mật khẩu.
- Gửi email xác minh địa chỉ.
- Đăng ký theo lời mời hoặc quản trị viên duyệt tài khoản.
- Trang quản trị, cấp role, cấp project hoặc chỉnh ACL.
- OAuth, SSO, LDAP, passkey hoặc JWT của legacy.
- Avatar, số điện thoại, ngày sinh hoặc username riêng.
- Thay đổi giao diện chat, documents hoặc LLM settings.
- Thêm router, Tailwind, UI library hoặc dependency runtime cho việc dựng form.
- Viết hoặc sửa template trong Figma.
- Chỉnh lại logo hoặc tạo thêm bộ logo.
- Chạy, import hoặc sửa runtime của `references/`.
- Đọc hoặc sử dụng bất kỳ thư mục tên `archive`, không phân biệt hoa/thường.

### Kiến trúc và nguồn tái sử dụng

Ưu tiên mã active, sau đó port phần tương thích từ legacy.
Bảng dưới đây ghi nguồn tái sử dụng và cách áp dụng trong F009.

| Nguồn đã kiểm tra | Phần tái sử dụng | Điều chỉnh cho active project |
|---|---|---|
| `backend/ruvie/services/auth.py::hash_password`, `verify_password` | Băm và kiểm tra mật khẩu bằng scrypt. | Giữ thuật toán và định dạng hash. Độ dài mới chỉ áp dụng khi đăng ký. |
| `AuthService.authenticate`, `create_session`, `resolve_session`, `revoke_session` | Xác thực và vòng đời phiên. | Tách phần tạo bản ghi session chưa commit để đăng ký có thể lưu user và session trong một transaction. Giữ hợp đồng login hiện có. |
| `backend/ruvie/api/auth.py::_auth_response`, `login` | Serialize user/CSRF và đặt cookie. | Reuse helper cookie giữa login và register khi cần. Route không tự quyết định quyền hoặc ghi user trực tiếp. |
| `backend/ruvie/api/security.py::check_origin`, `verify_csrf` | Kiểm tra nguồn request và CSRF. | Register kiểm tra Origin giống login; chưa có phiên nên không yêu cầu CSRF session trước đăng ký. Logout và API được bảo vệ vẫn kiểm tra CSRF như hiện tại. |
| `frontend/src/lib/auth-api.ts` | Fetch cùng origin, cookie, `AuthApiError`. | Thêm `register` và mapping lỗi riêng của đăng ký. Không đổi request login/logout. |
| `frontend/src/App.svelte::submitLogin`, `clearSession`, `loadProjects` | Quản lý user/CSRF, xóa trạng thái cũ, tải project. | Thêm submit đăng ký và dùng cùng bước nhận phiên. |
| `references/src/routes/auth/+page.svelte::chooseAuthMode`, `submitHandler`, `signInHandler`, `signUpHandler` | Chuyển form, đặt focus, chọn hành động theo mode, vào ứng dụng sau thành công. | Port phần tương tác sang Svelte 5. Không port stores, socket, SvelteKit routing, localStorage token hoặc redirect tùy ý. |
| `references/src/lib/components/common/SensitiveInput.svelte` | Hiện/ẩn mật khẩu, autocomplete, `aria-pressed`. | Port phần tương tác bằng Svelte 5 và CSS active. Không kéo settings store hoặc context i18n legacy. Ưu tiên asset icon Figma cho hình hiển thị. |
| `references/src/lib/apis/auths/index.ts::userSignIn`, `userSignUp` | Tách client API khỏi form. | Áp dụng vào `auth-api.ts`; đổi payload `name` thành `display_name`, bỏ avatar và token response legacy. |
| `references/backend/ruvie/routers/auths.py::signup`, `signup_handler` | Kiểm tra email, mật khẩu, tài khoản trùng; tạo tài khoản rồi nhận phiên. | Chuyển nghiệp vụ vào `AuthService`. Dùng model User active, PostgreSQL, transaction chung và scrypt. Không port HTTPException trong service, cơ chế tự cấp admin hoặc nhóm mặc định. |
| `references/backend/ruvie/models/auths.py::SignupForm`, `AuthsTable.insert_new_auth` | Input có tên/email/mật khẩu; nguyên tắc lưu thông tin tài khoản cùng credential. | Active lưu credential trong User, không tạo bảng `auth` riêng. Không port bcrypt, profile_image_url hoặc model legacy. |

Các nguồn legacy chỉ dùng để tham khảo và port phần tương thích.
Không import runtime từ `references/`.
Ghi nguồn port trong comment liên quan và báo cáo triển khai.
Theo AGENTS.md của dự án, thiếu LICENSE trong mã legacy được cung cấp không chặn việc tái sử dụng.

## Flow

### 1. Mở trang auth và chuyển form

1. Browser mở ứng dụng.
2. `App.svelte` gọi `GET /auth/session`.
3. Nếu có phiên hợp lệ, App hiển thị workspace và tải project theo user đó.
4. Nếu API trả 401, App hiển thị trang auth.
5. Hai trang auth là hai mode trong SPA hiện có. Dùng `/?form=login` và `/?form=register`; không thêm router.
6. Nếu query thiếu hoặc không hợp lệ, dùng mode login.
7. Liên kết chuyển mode cập nhật query và trạng thái bằng History API. Browser Back/Forward khôi phục mode tương ứng.
8. Khi đổi mode, xóa lỗi, mật khẩu và trạng thái hiện mật khẩu. Có thể giữ email; tên hiển thị chỉ thuộc form đăng ký.
9. Đặt focus vào Email ở login hoặc Tên hiển thị ở register.
10. Khi đăng nhập thành công, bỏ query `form`. Đăng xuất quay về login.
11. Nếu kiểm tra phiên gặp lỗi mạng, hiển thị lỗi có thể thử lại. Không coi lỗi mạng là bằng chứng có phiên hợp lệ.

### 2. Đăng nhập

1. Người dùng nhập email và mật khẩu.
2. Form kiểm tra trường bắt buộc và định dạng email.
3. App gửi `POST /auth/login` theo hợp đồng hiện có.
4. Route kiểm tra Origin và gọi `AuthService.authenticate`.
5. Service trả user khi credential đúng và user còn hoạt động.
6. Service tạo phiên; route đặt cookie và trả `AuthResponse`.
7. App giữ user và CSRF trong bộ nhớ; form xóa mật khẩu.
8. App vào workspace và tải project.
9. Nếu credential sai hoặc user bị khóa, UI hiển thị cùng thông báo “Email hoặc mật khẩu không đúng”.
10. Nếu request thất bại, App giải phóng trạng thái busy và cho phép thử lại.

### 3. Đăng ký

1. Người dùng nhập tên hiển thị, email và mật khẩu.
2. Form kiểm tra các quy tắc trong Scope. UI hiển thị lỗi trước khi gửi nếu có thể phát hiện.
3. App gửi `POST /auth/register`.
4. API kiểm tra Origin và parse payload.
5. Hợp đồng input kiểm tra type, trường được phép, tên, email và độ dài mật khẩu.
6. `AuthService.register` chuẩn hóa tên/email và kiểm tra email đã tồn tại.
7. Service băm mật khẩu, thêm User và flush User. Chưa commit transaction.
8. Service thêm session chưa commit bằng logic dùng chung với login.
9. Service commit một lần cho cả user và session. Flush User ở bước 7 bảo đảm foreign key.
10. Nếu unique index báo email trùng, service rollback và trả kết quả lỗi tài khoản trùng.
11. Nếu database hoặc tạo session thất bại, service rollback và trả/raise lỗi được API xử lý an toàn.
12. Sau commit thành công, route đặt cookie và trả HTTP 201.
13. App nhận user/CSRF, xóa mật khẩu và vào workspace.
14. App tải project. Không có quyền thì kết quả rỗng; không tự tạo project.
15. Nếu bước tải project thất bại sau khi nhận phiên, hiển thị lỗi tải project trong workspace. Không báo rằng đăng ký đã thất bại.

### 4. Hợp đồng API đăng ký

Endpoint mới: `POST /auth/register`.

Request yêu cầu `Content-Type: application/json` và Origin thuộc allowlist server.

Ví dụ body:

```json
{
  "display_name": "Nguyễn An",
  "email": "an@example.test",
  "password": "example-password"
}
```

Các giá trị trong ví dụ chỉ dùng cho tài liệu và test.
`display_name`, `email`, `password` phải là string.
Thiếu trường, type sai, JSON lỗi hoặc trường thừa bị từ chối.
Client không được gửi `id`, `role`, `project_id`, `is_active` hoặc `password_hash`.

HTTP 201 dùng cấu trúc `AuthResponse` hiện có:

```json
{
  "user": {
    "id": "<UUID do server tạo>",
    "display_name": "Nguyễn An"
  },
  "csrf_token": "<CSRF của phiên mới>"
}
```

Response không chứa password, password_hash, raw session token hoặc quyền do client chọn.
Header Set-Cookie chứa session token theo cấu hình cookie trong Scope.

| HTTP | Tình huống | Kết quả UI |
|---|---|---|
| 201 | Tạo tài khoản và session thành công. | Nhận phiên và vào workspace. |
| 403 | Origin thiếu hoặc không có trong allowlist. | Thông báo nguồn request không được phép; không tạo tài khoản. |
| 409 | Email đã tồn tại, kể cả yêu cầu đồng thời. | Lỗi ở Email; người dùng có thể chuyển sang đăng nhập. |
| 422 | Input không hợp lệ. | Lỗi gần trường hoặc lỗi payload ở mức form. |
| 500 | Ghi dữ liệu/tạo session thất bại vì nguyên nhân khác. | Thông báo không thể tạo tài khoản; không lộ lỗi nội bộ. |

Payload lỗi riêng của register:

```json
{
  "detail": {
    "code": "validation_error",
    "fields": {
      "password": "password_length"
    }
  }
}
```

- `fields` chỉ xuất hiện khi có lỗi trường.
- Whitelist code mức form: `validation_error`, `origin_not_allowed`, `email_taken`, `registration_failed`.
- Whitelist code mức trường: `required`, `invalid_type`, `name_length`, `invalid_email`, `email_length`, `password_length`, `email_taken`.
- Trường thừa hoặc JSON lỗi dùng `validation_error` mức form.
- Frontend chỉ render translation key từ code và field nằm trong whitelist.
- Response không phản chiếu lại giá trị input.
- Đặc biệt, lỗi 422 không được chứa password trong `input` hoặc `ctx` của Pydantic.
- API phải serialize lỗi validation register thành payload an toàn ở trên. Không chuyển raw `RequestValidationError.errors()` thẳng ra response.
- Hợp đồng lỗi login/session/logout hiện có không bắt buộc đổi thành envelope này.

### 5. Ranh giới module

1. `contracts/auth.py`: định nghĩa input đăng ký và response; kiểm tra dữ liệu đầu vào.
2. `api/auth.py`: xử lý HTTP, Origin, parse/serialize lỗi an toàn, gọi service và đặt cookie.
3. `services/auth.py`: kiểm tra email trùng, tạo tài khoản, mật khẩu băm, transaction và session.
4. `models/auth.py`: User/AuthSession và index.
5. `main.py`: giữ nhiệm vụ đăng ký router và tài nguyên dùng chung. Router auth đã được đăng ký; không chuyển nghiệp vụ đăng ký vào main.
6. `auth-api.ts`: gửi request, parse kết quả và chuyển lỗi thành `UiMessage`.
7. `App.svelte`: quản lý phiên và điều hướng giữa auth/workspace.
8. Form và AuthPage: quản lý nội dung nhập, validation UX, focus và layout. Không truy cập database hoặc tự quyết định quyền.

Interface service được triển khai:

- `AuthService.register(display_name, email, password)`: trả structured result chứa user và `CreatedSession`; lỗi nghiệp vụ không dùng HTTPException.
- Helper tạo session chưa commit chỉ thêm bản ghi và trả secrets của session.
- `create_session(user_id)` hiện có giữ hành vi commit cho login.
- Register điều khiển transaction bao quanh user và session.
- SQLAlchemy IntegrityError chỉ được chuyển thành `email_taken` nếu xác định là xung đột unique email. Lỗi constraint khác không được báo sai thành email trùng.

## Edge Cases

| Điều kiện | Hành vi yêu cầu |
|---|---|
| Tên chỉ có khoảng trắng. | 422; focus Tên hiển thị; không tạo User. |
| Email rỗng, sai định dạng, quá dài hoặc không phải string. | 422; không gửi truy vấn tạo User. |
| Email có khoảng trắng hai đầu hoặc khác hoa/thường. | Chuẩn hóa trước tra cứu/lưu; cùng địa chỉ chỉ có một tài khoản. |
| Email trùng tài khoản đang hoạt động hoặc bị khóa. | 409; không ghi đè hoặc mở khóa tài khoản cũ. |
| Hai request đồng thời dùng cùng email. | Một request thành công; request còn lại 409. Chỉ một User và một phiên đăng ký thành công được tạo. |
| Database đã có email khác nhau chỉ ở hoa/thường. | Migration thất bại; transaction migration được rollback; dữ liệu giữ nguyên. |
| Password dài 11 hoặc 129 ký tự. | 422. Không cắt mật khẩu để biến thành hợp lệ. |
| Password dài 12 hoặc 128 ký tự, có Unicode hoặc khoảng trắng. | Chấp nhận theo quy tắc độ dài; kiểm tra lại đúng chuỗi bằng verify_password. |
| Tài khoản cũ có mật khẩu ngắn hơn 12 ký tự. | Vẫn login theo hợp đồng hiện có. |
| JSON thừa role/project/id hoặc chứa password_hash. | 422; không dùng giá trị này làm quyền hoặc dữ liệu lưu. |
| Origin thiếu hoặc bị cấm. | 403; không tạo User/session. |
| Băm mật khẩu hoặc insert session thất bại. | Không tồn tại user đăng ký dở hoặc session dở. Không trả cookie mới. |
| Client mất mạng sau khi server commit. | Không tự retry request đăng ký. Cho thử lại có chủ đích; nếu email đã tồn tại, cho chuyển sang login. Không ghi đè tài khoản. |
| Double-click hoặc nhấn Enter nhiều lần. | Frontend chỉ có một request đang gửi. Backend vẫn dựa vào unique index. |
| Đổi form trong lúc request đang gửi. | Chặn chuyển mode. Không để response muộn cập nhật nhầm form. |
| Chuyển form sau lỗi. | Xóa lỗi, password và trạng thái hiện password. Không lưu password vào URL. |
| Session còn hợp lệ khi mở URL register. | Hiển thị workspace; không hiện form auth. |
| Session hết hạn hoặc user bị khóa. | Xóa dữ liệu phiên cũ theo clearSession; quay lại login. |
| Đăng ký thành công nhưng loadProjects lỗi. | Giữ phiên mới; hiển thị lỗi tải project và cho thử lại. |
| User mới đoán document/project ID của người khác. | Áp dụng lỗi từ chối hiện có; không lộ nội dung, metadata/citation riêng tư hoặc storage URI. |
| Chuỗi tên chứa markup. | Hiển thị văn bản; không thực thi HTML/script. |
| Locale có nhãn hoặc lỗi dài. | Nội dung xuống dòng; card tăng chiều cao; không đè ô nhập/nút. |
| Viewport nhỏ, bàn phím ảo hoặc zoom 200%. | Cho cuộn dọc để đến nút submit và liên kết; không cuộn ngang. |
| Asset không tải được hoặc browser không hỗ trợ blur. | Form và nhãn vẫn hoạt động; logo có alt “Ruvie”; nền fallback giữ độ tương phản. |

## Acceptance Criteria

- [x] **AC-01:** Login và register dùng cùng nền Figma, khối kính và logo v2. Logo hiển thị đúng “Ruvie” với một chữ R.
- [x] **AC-02:** Asset Figma và logo có file cục bộ không rỗng, đúng callsite, slot và tỉ lệ. Không có URL asset tạm thời hoặc screenshot toàn màn hình trong code chạy.
- [x] **AC-03:** Form login chỉ yêu cầu email/mật khẩu. Login tài khoản có sẵn vẫn tạo và khôi phục phiên như trước.
- [x] **AC-04:** Form register có tên hiển thị/email/mật khẩu/nhập lại mật khẩu; chỉ gửi ba trường API. Backend từ chối trường thừa và input sai dù client bỏ qua validation.
- [x] **AC-05:** Tên sau trim dài 1–255; email hợp lệ sau chuẩn hóa dài 3–320; password dài 12–128 và được giữ nguyên trước băm.
- [x] **AC-06:** Register hợp lệ trả 201 và cùng shape AuthResponse hiện có; cookie HttpOnly/Secure/SameSite=Lax, thời hạn 12 giờ; password/hash/raw session token không có trong JSON.
- [x] **AC-07:** Database lưu password bằng scrypt và token bằng SHA-256. verify_password xác nhận đúng mật khẩu đăng ký.
- [x] **AC-08:** Email trùng, kể cả khác hoa/thường và hai request đồng thời, bị chặn bằng PostgreSQL. Không tạo hai tài khoản cho cùng địa chỉ.
- [x] **AC-09:** Lỗi tạo session hoặc lưu dữ liệu rollback cả user và session. Không có tài khoản dở sau lỗi.
- [x] **AC-10:** Migration mới xuất SQL được, upgrade/downgrade được trên PostgreSQL dùng riêng cho test và không sửa migration cũ. Dữ liệu email xung đột làm migration thất bại mà không bị xóa/hợp nhất.
- [x] **AC-11:** Register thiếu/sai Origin trả 403; không tạo bản ghi. Logout và request được bảo vệ vẫn giữ kiểm tra CSRF.
- [x] **AC-12:** Tài khoản mới không được cấp role/membership/grant. Danh sách project rỗng; đoán ID không đọc được tài liệu, revision, chunk hoặc citation của người khác.
- [x] **AC-13:** Sau register thành công, App vào workspace. Reload khôi phục đúng user; logout kết thúc phiên; login lại bằng mật khẩu đăng ký thành công.
- [x] **AC-14:** Hai mode chuyển bằng liên kết, query và Back/Forward. Chuyển mode xóa mật khẩu/lỗi và đặt focus đúng. Có phiên hợp lệ thì không hiển thị form.
- [x] **AC-15:** Lỗi 409 ở Email; lỗi 422 gần trường; lỗi mạng/500 ở form. Response và UI không chứa password, raw validation input, SQL hoặc traceback.
- [x] **AC-16:** Busy khóa submit và chuyển mode; nhiều lần bấm không tạo nhiều request đồng thời. Request lỗi giải phóng busy. Không có retry đăng ký tự động.
- [x] **AC-17:** Hiện/ẩn mật khẩu dùng được bằng bàn phím và có aria-label/aria-pressed. Paste và password manager không bị chặn.
- [x] **AC-18:** Việt/Anh/Nga có đủ translation key. Đổi ngôn ngữ cập nhật cả thông báo lỗi đang hiển thị. Không render raw server message.
- [x] **AC-19:** Kiểm tra layout tại 1920×1080, 1366×768, 1024×600, 768×1024, 375×812, 320×568 và 640×360 CSS px ở scale 2. Không cuộn ngang; nút và liên kết truy cập được bằng cuộn dọc.
- [x] **AC-20:** Nhãn/lỗi/nút có focus và độ tương phản đạt yêu cầu Scope. Chữ input tối thiểu 16 px; vùng thao tác tối thiểu 44 px.
- [x] **AC-21:** Chỉ khu vực auth đổi giao diện. Các check workspace, locale, upload, LLM và phân quyền đang có không bị hồi quy.
- [x] **AC-22:** Backend suite, frontend test/build, SQL migration và browser checks theo README đã chạy. Báo cáo ghi rõ pass/fail/skip; skip không được coi là đã kiểm tra xong tiêu chí phụ thuộc.
- [x] **AC-23:** README mô tả đăng ký mới, giới hạn quyền tài khoản mới và lệnh kiểm tra liên quan. Nguồn legacy đã port được ghi rõ.

## Tasks

Thực hiện theo thứ tự dưới đây.
Các task đã được triển khai và kiểm chứng.
Chi tiết Work/Where/Done giữ kế hoạch và tiêu chí; xem báo cáo kiểm chứng để đối chiếu kết quả thực tế.

### F009-001 - Chuẩn bị asset và thông số giao diện

- [x] **F009-001**

**Work**

1. Đọc lại design context và screenshot Figma `203:3`.
2. Root có thể trả sparse metadata vì nhiều vector. Đối chiếu child node với screenshot rồi lấy design context của từng phần nhìn thấy.
3. Dùng `206:14` làm tham chiếu khối form. Không triển khai từ sparse metadata hoặc screenshot đơn thuần.
4. Tải asset trang trí/icon cần dùng và kiểm tra kích thước gốc. Lưu chúng vào frontend.
5. Sao chép logo v2 đã chọn. Không overwrite file logo gốc.
6. Ghi token auth cục bộ: màu nền, màu kính, border, radius, spacing và kích thước chữ.
7. Ghi khác biệt đã chấp nhận: font stack active; input/nút lớn hơn; logo thật; bỏ Forgot Password; form register có thêm tên.
8. Xác định export từng nhóm trang trí khi nhóm có quá nhiều vector.

**Where**

- Nguồn: Figma file/frame trong Goal; `output/branding/ruvie-logo-navy-v2.png`.
- Tạo: `frontend/src/lib/assets/auth/`.
- Token/layout được dùng trong `AuthPage.svelte` ở F009-005.
- Ghi chú asset có thể đặt trong thư mục auth; chỉ thêm tài liệu nếu cần để nhận diện nguồn và slot.

**Done**

- Có asset cục bộ và logo đúng phiên bản.
- Mỗi asset được đối chiếu với slot trong Figma và có kích thước gốc.
- Không phát sinh dependency runtime hoặc mã React/Tailwind.
- Các file ảnh không rỗng; alpha/tỉ lệ logo được giữ.

### F009-002 - Bảo đảm email duy nhất trong PostgreSQL

- [x] **F009-002**

**Work**

1. Viết test SQL migration và test index trên PostgreSQL trước khi thay schema.
2. Thêm migration mới sau head hiện hành. Head đã kiểm tra là `0008_user_llm_settings`; kiểm tra lại trước khi tạo.
3. Tên file đề xuất: `0009_users_email_lower_unique.py`.
4. Tạo unique index `uq_users_email_lower` trên `lower(email)`.
5. Bổ sung index tương ứng vào model User.
6. Giữ constraint email hiện có. Không sửa data tài khoản.
7. Kiểm tra dữ liệu hợp lệ nâng cấp được; dữ liệu khác nhau chỉ ở hoa/thường làm nâng cấp thất bại.
8. Kiểm tra downgrade chỉ bỏ index mới. Kiểm tra chuỗi upgrade → downgrade → upgrade trên database test.
9. Xác nhận SQL offline có CREATE UNIQUE INDEX tương ứng.

**Where**

- Sửa: `backend/ruvie/models/auth.py::User`.
- Tạo: `backend/migrations/versions/0009_users_email_lower_unique.py` hoặc số kế tiếp nếu head thay đổi.
- Tạo: `tests/test_f009_002_email_uniqueness.py`.
- Tái sử dụng cách xuất SQL trong `tests/test_f002_002_migration.py` và PostgreSQL fixture của `tests/test_f005_007_e2e.py`.

**Done**

- Đạt AC-08, AC-10.
- Test PostgreSQL chứng minh unique index chặn email khác hoa/thường.
- Migration không thay đổi tài khoản cũ hoặc chạm database phát triển khi chạy test.

### F009-003 - Hợp đồng và service đăng ký

- [x] **F009-003**

**Work**

1. Viết test trường bắt buộc, type, độ dài, normalize, password Unicode và trường thừa.
2. Thêm `RegisterRequest` vào contracts auth với extra forbidden.
3. Thêm kiểm tra định dạng email rõ ràng, dùng thư viện chuẩn/Pydantic hiện có khi đủ. Không thêm dependency chỉ để dựng form.
4. Thêm structured result đăng ký và lỗi nghiệp vụ email trùng.
5. Thêm `AuthService.register`: chuẩn hóa → kiểm tra trùng → băm → thêm User → thêm session → flush/commit.
6. Tách helper thêm session chưa commit từ `create_session`. Login giữ hành vi public hiện có.
7. Rollback mọi lỗi ghi dữ liệu. Nhận diện đúng constraint email khi xử lý IntegrityError.
8. Không tạo membership, role, grant hoặc cấu hình provider cho tài khoản mới.
9. Thêm test tài khoản bị khóa không bị ghi đè khi email trùng.
10. Thêm test tạo session thất bại và commit thất bại không để lại user/session dở.

**Where**

- Sửa: `backend/ruvie/contracts/auth.py`.
- Sửa: `backend/ruvie/services/auth.py::AuthService`.
- Reuse: `hash_password`, `verify_password`, `CreatedSession`, User/AuthSession.
- Tham khảo: `references/backend/ruvie/routers/auths.py::signup_handler`; `references/backend/ruvie/models/auths.py::SignupForm`.
- Tạo: `tests/test_f009_003_registration_service.py`.
- Giữ hồi quy: `tests/test_f005_003_auth.py`.

**Done**

- Đạt AC-04, AC-05, AC-07, AC-09 và phần service của AC-12.
- Service không import HTTPException để biểu diễn lỗi nghiệp vụ.
- Không có commit user tách khỏi commit session.
- Mật khẩu cũ vẫn xác thực được; mật khẩu mới không bị trim/cắt.

### F009-004 - API đăng ký và cookie

- [x] **F009-004**

**Work**

1. Viết test request/response HTTP, Origin, validation và cookie.
2. Thêm `POST /auth/register` vào router đã có.
3. Dùng `check_origin` trước thao tác nghiệp vụ.
4. Gọi service, chuyển lỗi nghiệp vụ thành 409 và serialize lỗi khác an toàn.
5. Bảo đảm lỗi input register đi qua serializer an toàn, kể cả validation xảy ra trước handler. Không trả input password từ Pydantic.
6. Dùng AuthResponse và helper cookie chung với login để tránh hai cấu hình lệch nhau.
7. Chỉ đặt cookie sau khi service commit thành công.
8. Kiểm tra 201 → GET session → POST logout với CSRF; phiên đã logout trả 401.
9. Kiểm tra request thừa role/project/id không tạo dữ liệu quyền.
10. Giữ main.py chỉ đăng ký router; không thêm business logic.

**Where**

- Sửa: `backend/ruvie/api/auth.py`.
- Reuse: `_auth_response`, `check_origin`, `verify_csrf`.
- Contracts lỗi an toàn có thể đặt cùng `contracts/auth.py`.
- Tạo: `tests/test_f009_004_registration_api.py`.
- Tham khảo quy trình của `references/backend/ruvie/routers/auths.py::signup`; không sao chép router legacy.

**Done**

- Đạt AC-06, AC-11, AC-15 cho backend.
- Các status và payload khớp Flow.
- JSON lỗi không chứa password/hash/token/SQL/traceback.
- Không có cookie phiên mới khi service thất bại.

### F009-005 - Hai trang auth và kết nối frontend

- [x] **F009-005**

**Work**

1. Viết test client register và mapping lỗi.
2. Tạo AuthPage làm layout chung với assets F009-001.
3. Sửa LoginForm giữ callback login hiện có; bổ sung hiện/ẩn password và liên kết mode.
4. Tạo RegisterForm cho bốn trường giao diện, xác nhận mật khẩu trên client, validation UX, lỗi gần trường và callback register gửi ba trường API.
5. Port tương tác phù hợp từ auth page và SensitiveInput legacy sang Svelte 5.
6. Thêm `register` vào `auth-api.ts`; parse code/field bằng whitelist và giữ fetch same-origin.
7. Thêm `submitRegister` ở App. Reuse bước nhận user/CSRF và tải project.
8. Thực hiện query mode, History API, Back/Forward và xóa query sau thành công.
9. Xóa password/error/show state khi đổi mode hoặc unmount. Khóa thao tác trong lúc busy.
10. Đặt bộ chọn ngôn ngữ và bổ sung translation key đủ ba locale.
11. Dùng CSS cục bộ cho auth; thay phần topbar auth hiện tại để theo layout Figma. Giữ workspace sau login.
12. Thêm test render/interaction phù hợp; không test chỉ để so khớp chuỗi mã nguồn.
13. Kiểm tra cùng phiên trên reload và lỗi loadProjects sau đăng ký.

**Where**

- Tạo: `frontend/src/lib/components/AuthPage.svelte`, `RegisterForm.svelte`.
- Sửa: `frontend/src/lib/components/LoginForm.svelte`.
- Sửa: `frontend/src/lib/auth-api.ts`, `frontend/src/App.svelte`.
- Sửa auth-related CSS trong `frontend/src/app.css` khi cần; không đổi token theme workspace.
- Reuse: `LanguageSelector.svelte`, `UiMessage`, `i18n`.
- Sửa: `frontend/src/lib/i18n/locales/{vi-VN,en-US,ru-RU}/translation.json`.
- Mở rộng: `frontend/tests/auth-api.test.mjs`. Thêm `frontend/tests/registration.test.mjs` cho validation; tái sử dụng `frontend/tests/i18n.test.mjs` để kiểm tra catalog và thông báo.
- Tham khảo: các file frontend legacy ghi trong Scope.

**Done**

- Đạt AC-01–AC-04 ở frontend; AC-13–AC-18 và AC-20.
- Login/register có cùng layout và logo đúng.
- Đăng ký thành công vào workspace; lỗi project không biến thành lỗi đăng ký.
- Không có package router/UI mới hoặc token auth trong browser storage.
- Locale đầy đủ, UI không lộ code lỗi hoặc raw server message.

### F009-006 - Kiểm tra tích hợp, layout và tài liệu

- [x] **F009-006**

**Work**

1. Thêm browser checks dùng fake API cho mode, validation, busy, lỗi và layout.
2. Kiểm tra viewport trong AC-19, cả ba locale, keyboard, zoom và fallback blur.
3. Kiểm tra asset từng slot: file cục bộ, request tải thành công, callsite và kích thước render đúng.
4. So giao diện login desktop với screenshot Figma. So register với cùng layout đã điều chỉnh chiều cao.
5. Thêm E2E browser → active backend trên PostgreSQL dùng riêng cho test.
6. Kiểm tra register → workspace → reload → logout → login.
7. Gửi hai request đăng ký đồng thời bằng hai session database độc lập. Xác nhận một 201, một 409 và một tài khoản.
8. Gây lỗi tạo session/commit; xác nhận transaction không để lại dữ liệu dở.
9. Đăng ký user không có membership/grant; xác nhận project list rỗng và dữ liệu user khác bị từ chối.
10. Kiểm tra retrieval/chat không đưa tài liệu trái quyền vào context hoặc citation.
11. Chạy backend suite, frontend test/build và SQL migration theo README.
12. Chạy hồi quy workspace, upload, LLM và locale liên quan.
13. Cập nhật README: thay thông tin “no public signup”; vẫn giữ password CLI cho việc cấp/reset thủ công; ghi rõ tài khoản mới chưa được cấp quyền.
14. Bổ sung lệnh auth browser test vào README; không nhân bản run commands vào spec.
15. Báo cáo nguồn legacy đã dùng, file sản phẩm đã đổi và kết quả pass/fail/skip thực tế.

**Where**

- Tạo: `frontend/tests/auth-browser.mjs`.
- Nối vào browser harness hiện có khi phù hợp.
- Tạo: `tests/test_f009_006_registration_e2e.py`.
- Reuse harness: `tests/test_f005_007_e2e.py`, `tests/test_f006_008_browser_e2e.py`.
- Reuse check liên quan: `frontend/tests/layout-browser.mjs`, `i18n-browser.mjs`.
- Sửa: `README.md`; bổ sung ghi chú migration trong `docs/database-setup.md` nếu cần.
- Chỉ đánh dấu task trong spec sau khi các kiểm tra của task đó đạt.

**Done**

- Đạt AC-08, AC-10, AC-12, AC-13 và AC-19–AC-23.
- PostgreSQL/browser test không dùng database phát triển, .env credentials hoặc provider thật.
- Test bị skip do thiếu Docker/Playwright/browser phải được báo và để tiêu chí phụ thuộc chưa hoàn tất.
- Không sửa, chạy hoặc import mã legacy; không commit secrets hoặc generated frontend build.


## Điều chỉnh được yêu cầu sau triển khai (2026-10-12)

- Yêu cầu trực tiếp của người dùng bổ sung xác nhận mật khẩu và thay thế phần scope cũ không có ô này. API/backend không thêm trường hoặc thay đổi chính sách mật khẩu.
- Tái sử dụng `references/src/routes/auth/+page.svelte::signUpHandler`: so sánh hai giá trị trước `userSignUp`. Active dùng lỗi inline/focus, luôn yêu cầu xác nhận, không port cờ config/toast/avatar hoặc token legacy.
- Tái sử dụng `PasswordField` active cho hai ô mật khẩu với ID và trạng thái hiện/ẩn độc lập. Tái sử dụng `LanguageSelector` active qua prop compact.
- Khung co theo viewport, giảm khoảng cách trên desktop thấp, giữ input/nút 44 px. Canvas gradient/PNG cùng scale theo kích thước thực để không tạo dải màu ở mép.

- Điều chỉnh padding theo yêu cầu tiếp theo: desktop 24/32 → 48/64 px (dọc/ngang); desktop thấp 12/28 → 24/56 px; mobile 20 → 40 px. Nới card tương ứng trên desktop và giảm khoảng đệm ngoài trên viewport thấp.

## Port toast từ references theo yêu cầu (2026-10-12)

- Dùng `svelte-sonner` 1.2.1 phù hợp Svelte 5. Port cấu hình Toaster từ `references/src/routes/+layout.svelte`: richColors, top-right, closeButton; chuyển class Tailwind của nút đóng thành CSS active.
- Port cách gọi toast.error/toast.success từ `references/src/routes/auth/+page.svelte::signInHandler`, `signUpHandler`, `setSessionUser`. Chỉ dùng UiMessage an toàn; không port localStorage token, socket, avatar hoặc raw error string.
- AuthToastLayer đặt ở root App để toast thành công tồn tại sau chuyển sang workspace. Một ID toast cố định thay thế thông báo cũ, tránh chồng thông báo trùng. Notice lưu key và cập nhật nội dung khi đổi locale.
- Phản hồi server của login/register và lỗi kiểm tra phiên hiển thị qua toast; lỗi local validation vẫn cạnh trường. Lỗi server theo trường vẫn đặt aria-invalid/focus, nhưng nội dung được thông báo qua toast.
- Session 401 vì chưa đăng nhập không tạo toast. Lỗi mạng có hành động Thử lại để kiểm tra lại session, không tự gửi lại đăng ký. Toast có nút đóng và tự ẩn sau 5 giây; hover/focus theo hành vi Sonner.
- Toast offset top 76px để tránh dropdown; mobile lề 16px. Thêm margin-top 16px trước nút đăng nhập/đăng ký. Không thay đổi padding trong nút hoặc card.
- Xóa password-hint và aria-describedby tham chiếu tới hint. Giữ nguyên validation 12–128 ký tự và xác nhận mật khẩu.
