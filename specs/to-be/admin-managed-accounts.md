# Khởi tạo admin và tài khoản do admin cấp

Trạng thái: To-be, chưa triển khai.
Ngày ghi nhận: 2026-10-13.

## Mục tiêu

Ruvie Agent dùng mô hình tài khoản do công ty quản lý. Trang đăng ký chỉ mở
khi database chưa có user nào. User đầu tiên được tạo sẽ là admin. Khi database
đã có user, admin tạo tài khoản cho nhân viên; nhân viên đăng nhập và có quyền
tự đổi mật khẩu.

Định hướng này thay thế hành vi hiện tại: đăng ký công khai luôn có thể truy cập,
tài khoản đầu tiên không trở thành admin. Quyền admin hệ thống tách riêng với
vai trò nghề nghiệp trong từng project.

## 1. Khởi tạo admin lần đầu

- Điều kiện mở trang đăng ký: database có **0 user**. Người mở app được hiển
  thị trang **Tạo tài khoản quản trị viên**.
- Trạng thái này dựa trên dữ liệu trong database, áp dụng nhất quán cho giao
  diện và máy chủ. Database đã có user nhưng chưa có admin vẫn không mở đăng ký.
- Form gồm tên hiển thị, email, mật khẩu và xác nhận mật khẩu.
- Tạo thành công: user đầu tiên có quyền admin và được đăng nhập vào app.
  Database đã có user nên đăng ký công khai được đóng.
- Tạo thất bại và database vẫn có 0 user: hiển thị lỗi và cho phép thử lại.
- Nếu nhiều người gửi form đồng thời, chỉ một yêu cầu được tạo admin đầu tiên.
  Các yêu cầu còn lại không tạo thêm tài khoản và được đưa về đăng nhập.

## 2. Đăng nhập sau khi khởi tạo

- Khi database có ít nhất **1 user**, người chưa đăng nhập chỉ thấy trang
  **Đăng nhập**. Bỏ liên kết, nút và lời mời chuyển sang đăng ký trên giao diện
  login/register.
- Truy cập trực tiếp URL đăng ký, dùng lịch sử trình duyệt hoặc gửi form đăng
  ký đã mở từ trước đều không tạo được tài khoản; giao diện đưa về đăng nhập.
- Hệ thống chặn đăng ký công khai cả phía máy chủ, kể cả khi bỏ qua giao diện.
- Khi database vẫn có user, đóng/mở app, khởi động lại server, đăng xuất hoặc
  đổi trình duyệt không mở lại đăng ký. Không có lựa chọn bật lại đăng ký công
  khai khi database đã có user.

## 3. Admin cấp tài khoản cho nhân viên

- Admin mở **Quản trị → Người dùng → Tạo tài khoản**.
- Admin nhập tên hiển thị, email và mật khẩu ban đầu; tài khoản được tạo có
  quyền user thông thường.
- Email trùng hoặc dữ liệu không hợp lệ được báo rõ; không ghi đè tài khoản cũ.
- Admin bàn giao thông tin đăng nhập cho nhân viên qua kênh nội bộ phù hợp.
- Nhân viên đăng nhập bằng tài khoản được cấp. Tạo user không thay phiên đăng
  nhập hiện tại của admin và không tự cấp quyền đọc tài liệu/project.
- Chỉ admin được tạo tài khoản; user thông thường không thực hiện được thao
  tác này dù truy cập trực tiếp chức năng tạo user.

## 4. Người dùng tự đổi mật khẩu

- User và admin đã đăng nhập mở **Cài đặt → Tài khoản → Đổi mật khẩu**.
- Nhập mật khẩu hiện tại, mật khẩu mới và xác nhận mật khẩu mới.
- Chỉ đổi mật khẩu của chính tài khoản đang đăng nhập; mật khẩu hiện tại phải
  đúng, xác nhận phải khớp và mật khẩu mới phải đạt chính sách hiện hành.
- Thành công: thông báo rõ, xóa các trường mật khẩu; lần đăng nhập tiếp theo
  dùng mật khẩu mới, mật khẩu cũ không còn đăng nhập được.
- Thất bại: giữ nguyên mật khẩu đã lưu và báo lỗi phù hợp.

## Phạm vi

Tập trung ba luồng trên và việc điều chỉnh giao diện login/register. Chưa bao
gồm quên mật khẩu, reset mật khẩu thay user, lời mời qua email, nhập user hàng
loạt hoặc bắt buộc đổi mật khẩu ở lần đăng nhập đầu.

## Tham khảo references

- `references/backend/ruvie/main.py`: nhận biết onboarding khi chưa có user.
- `references/src/routes/auth/+page.svelte`: onboarding, chọn chế độ đăng
  nhập/đăng ký và hiển thị liên kết theo trạng thái cho phép đăng ký.
- `references/backend/ruvie/routers/auths.py`: `signup_handler` tạo admin đầu
  tiên; `signup` kiểm tra điều kiện đăng ký; `add_user` dành cho admin;
  `update_password` xác minh mật khẩu hiện tại trước khi đổi.
- `references/src/lib/components/admin/Users/UserList/AddUserModal.svelte`:
  form admin tạo user với tên, email và mật khẩu.
- `references/src/lib/components/chat/Settings/Account/UpdatePassword.svelte`:
  form mật khẩu hiện tại, mật khẩu mới, xác nhận và phản hồi kết quả.

References nhận biết khởi tạo bằng điều kiện chưa có user trong database và
gán user đầu tiên làm admin; đăng ký về sau phụ thuộc cấu hình. Định hướng mới
chỉ mở đăng ký công khai khi database có 0 user và đóng khi đã có user. Tận dụng
luồng và tương tác đã có; giữ xác thực hiện tại và kiểm tra quyền tài liệu của
Ruvie Agent.