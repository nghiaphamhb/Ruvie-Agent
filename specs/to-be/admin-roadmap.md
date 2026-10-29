# Kế hoạch quản trị Ruvie Agent

Cập nhật: 2026-10-26. Trạng thái: Backlog; các hành vi dưới đây chưa triển khai hoặc mới có một phần.

## Các hành vi cần bổ sung

| Mục | Hành vi mong muốn |
| --- | --- |
| Xóa tài khoản | Admin xóa tài khoản theo chính sách lưu giữ dữ liệu đã thống nhất; xử lý rõ quyền, phiên và dữ liệu liên quan. |
| Khôi phục quyền quản trị | Có quy trình khôi phục khi không còn admin sử dụng được; không mở lại đăng ký công khai khi đã có tài khoản. |
| Quản lý quyền tài nguyên | Admin cấp/thu hồi membership project, vai trò nghề nghiệp và quyền tài liệu. Quyền admin hệ thống không mặc nhiên cho phép đọc mọi tài liệu. |
| LLM tập trung | Admin quản lý provider, API key dùng chung, model mặc định và danh sách model được cấp. Nhân viên chỉ chọn model được phép; không đọc API key hoặc sửa cấu hình qua API trực tiếp. |
| Proxy LLM/embedding | Admin chọn direct hoặc SOCKS5 riêng cho LLM và embedding, thử trước khi áp dụng và xem cấu hình hiệu lực. Áp dụng đúng cho backend/worker; proxy lỗi không tự chuyển direct, lỗi không lộ secret và vẫn giữ bảo vệ mạng/TLS. |
| Ngôn ngữ tổ chức | Admin chọn vi-VN/en-US/ru-RU hoặc bỏ mặc định. Lựa chọn cá nhân đã lưu ưu tiên hơn tổ chức, sau đó đến trình duyệt và fallback vi-VN; không thay ngôn ngữ trả lời LLM hoặc ép đổi phiên đang mở. |
| Vận hành kho tri thức | Admin theo dõi tiếp nhận, xử lý và lỗi tài liệu để phối hợp người phụ trách; không vượt quyền đọc nội dung. |
| Sự cố dịch vụ | Nhân viên xác nhận gửi báo cáo; admin nhận, gộp sự cố, theo dõi ảnh hưởng và cập nhật xử lý/khôi phục. Luồng vẫn hoạt động khi LLM lỗi; không tự đính kèm hội thoại, tài liệu hoặc secret. |
| Giám sát và truy vết | Admin xem trạng thái, thống kê tổng hợp và lịch sử thao tác phù hợp quyền; không ghi secret hoặc mặc nhiên xem mọi hội thoại. |
| Skills, công cụ và tích hợp | Admin quản lý quyền sử dụng và phạm vi dữ liệu chia sẻ; chốt điều kiện xác nhận trước thao tác bên ngoài theo từng nghiệp vụ. |

## Nền tảng đã có

Đã có khởi tạo admin đầu tiên và đóng đăng ký công khai; tạo, xem, tìm kiếm và sửa tài khoản; cấp/thu hồi vai trò admin với bảo vệ admin hoạt động cuối cùng; reset mật khẩu, tự đổi mật khẩu và trạng thái hoạt động tài khoản. Admin có thể [khóa hoặc mở lại tài khoản](../feat/F015-account-activation.md); khóa thu hồi các session, bảo vệ admin hoạt động cuối cùng và giữ dữ liệu.

Backend đã có kiểm tra quyền tài liệu, cấu hình proxy phía server và ghi audit cho một số thao tác. F016 đã bổ sung cấu hình LLM tổ chức và chính sách model chung trong working tree. Xem [spec F016](../feat/F016-centralized-llm-management.md).

## Ưu tiên đề xuất

1. LLM tập trung, sau đó proxy LLM/embedding và báo sự cố.
2. Quyền tài nguyên, ngôn ngữ tổ chức, vận hành kho tri thức và giám sát.
3. Chốt riêng quy trình khôi phục admin, xóa tài khoản và quản trị tích hợp trước khi triển khai.

Đây là kế hoạch hành vi ngắn gọn, chưa chốt thiết kế triển khai hoặc cho phép thay đổi code. Các chức năng quản trị phải được kiểm tra quyền phía server; thành công và lỗi hiển thị bằng toast an toàn.
