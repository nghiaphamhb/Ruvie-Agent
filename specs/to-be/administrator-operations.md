# Các hoạt động quản trị còn lại của Ruvie Agent

Trạng thái: To-be, ghi nhận ngắn gọn; chưa thiết kế chi tiết hoặc triển khai.
Ngày ghi nhận: 2026-10-20.

## Mục tiêu và ưu tiên

Ưu tiên hiện tại là [admin tạo tài khoản](admin-managed-accounts.md), cho phép chọn vai trò `user` hoặc `admin`. Tài liệu này gom các hoạt động còn lại để lập kế hoạch sau; không chốt thiết kế code, API, schema hoặc mở rộng phạm vi đang làm.

## Khởi tạo admin và đóng đăng ký công khai

- Chỉ khi database có 0 user, hệ thống mở form tạo admin đầu tiên với tên, email, mật khẩu và xác nhận mật khẩu. Thành công thì đăng nhập admin và đóng đăng ký công khai. Khởi tạo đồng thời chỉ tạo được một admin đầu tiên.
- Thất bại thì cho thử lại nếu vẫn có 0 user. Khi đã có user, chỉ cung cấp đăng nhập; URL đăng ký hoặc form mở từ trước cũng không tạo được tài khoản.
- Khởi động lại, đăng xuất hoặc đổi trình duyệt không mở lại đăng ký. Không có lựa chọn bật lại đăng ký công khai khi database vẫn có user.

## Khôi phục khi không còn admin

Đã có user nhưng không còn admin: cần quy trình khôi phục quyền quản trị. Không dùng tình huống này để mở lại đăng ký công khai. Chỉ ghi nhận backlog; chưa mô tả cách khôi phục.

## Người dùng tự đổi mật khẩu

User và admin tự đổi mật khẩu tại **Cài đặt → Tài khoản → Đổi mật khẩu** bằng mật khẩu hiện tại, mật khẩu mới và xác nhận. Chỉ đổi cho chính mình; mật khẩu hiện tại phải đúng, xác nhận phải khớp và mật khẩu mới đạt chính sách. Thành công thì xóa các trường mật khẩu; lần đăng nhập sau chỉ dùng mật khẩu mới. Thất bại giữ nguyên mật khẩu đã lưu. Chưa bắt buộc đổi ở lần đăng nhập đầu.

## Các hoạt động cần lập kế hoạch tiếp

| Hoạt động | Định hướng ngắn gọn |
| --- | --- |
| Vòng đời tài khoản | Xem/tìm kiếm, sửa thông tin, tạm ngừng/kích hoạt; chốt riêng việc xóa và ảnh hưởng đến dữ liệu liên quan |
| Thay đổi quyền admin của tài khoản đã có | Chốt cấp/thu hồi/chuyển giao và tránh mất toàn bộ quyền quản trị; việc tạo admin mới đã nằm trong luồng tạo tài khoản |
| Quyền sử dụng | Quản lý membership project, vai trò nghề nghiệp và cấp/thu hồi quyền tài nguyên theo chính sách; không đồng nhất với vai trò admin hệ thống |
| LLM và model | Admin quản lý provider, API key, model mặc định và model được cấp; nhân viên chỉ chọn model được phép |
| Đường kết nối | Direct/SOCKS5 riêng cho LLM và embedding; thử trước khi áp dụng, hiển thị cấu hình hiệu lực và lỗi an toàn; không tự chuyển sang direct khi proxy lỗi |
| Ngôn ngữ tổ chức | Chọn vi-VN/en-US/ru-RU hoặc không đặt mặc định; lựa chọn cá nhân được ưu tiên, không thay ngôn ngữ trả lời LLM |
| Vận hành kho tri thức | Theo dõi tiếp nhận/xử lý tài liệu, phát hiện lỗi và phối hợp người phụ trách nội dung; không mặc nhiên đọc mọi tài liệu |
| Sự cố dịch vụ | Nhận báo cáo, gộp sự cố, đánh giá ảnh hưởng, cập nhật xử lý và thông báo khôi phục; luồng báo cáo vẫn hoạt động khi LLM lỗi |
| Giám sát và truy vết | Theo dõi trạng thái, thống kê tổng hợp và lịch sử thao tác; không ghi mật khẩu, API key hoặc mặc nhiên mở quyền xem mọi hội thoại |
| Skills, công cụ và tích hợp | Chốt quyền sử dụng, phạm vi dữ liệu được chia sẻ và điều kiện xác nhận trước thao tác bên ngoài khi nghiệp vụ được xác định |

Administrator xử lý sự cố vận hành Ruvie Agent. IT Support xử lý vấn đề sử dụng phần mềm của nhân viên. Một người có thể kiêm hai vai trò; trách nhiệm và quyền tài nguyên của mỗi vai trò vẫn cần được xác định riêng.

Quên mật khẩu, reset mật khẩu thay user, mời qua email và nhập tài khoản hàng loạt chưa thuộc phạm vi đã chốt. Các hoạt động ngoài luồng tạo tài khoản cần được phân tích và duyệt trước khi triển khai.

## Tài liệu và references liên quan

- [Quản trị LLM và báo sự cố](admin-managed-llm.md).
- [Proxy và ngôn ngữ tổ chức](llm-proxy-admin-settings.md).
- [Định hướng locale](ui-localization-evolution.md).
- [Luồng xác thực legacy](../../references/backend/ruvie/routers/auths.py): tham khảo `signup_handler`, `signup` và `update_password`.
- [Quản lý người dùng legacy](../../references/backend/ruvie/routers/users.py): tham khảo sửa thông tin và bảo vệ admin đầu tiên.
- [Nhóm quản trị legacy](../../references/src/lib/components/admin/Users.svelte) và [thiết lập legacy](../../references/src/lib/components/admin/Settings.svelte): tham khảo cách phân nhóm trách nhiệm, không mặc nhiên nhận toàn bộ tính năng.

References có thể cho đăng ký sau khởi tạo theo cấu hình. Định hướng Ruvie Agent chỉ cho đăng ký khi có 0 user. Hành vi legacy không thay thế quy tắc này hoặc quyền đọc tài liệu default-deny, nội dung revision bất biến và lưu trữ riêng tư.
