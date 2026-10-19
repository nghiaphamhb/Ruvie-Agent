# Quản trị LLM tập trung và báo sự cố

Trạng thái: To-be, chưa triển khai các yêu cầu trong tài liệu này.
Ngày ghi nhận: 2026-10-20.

## Mục tiêu

Ruvie Agent dùng mô hình công ty cấp tài khoản cho nhân viên. Admin quản lý
kết nối LLM dùng chung; nhân viên chọn model được cấp và báo sự cố khi không
sử dụng được dịch vụ.

Định hướng này thay thế thiết lập provider/API key cá nhân hiện tại. Khi triển
khai, cần chốt cách chuyển đổi cấu hình cũ; không tiếp tục dùng ngầm cấu hình cá nhân.

## Yêu cầu tương lai

### 1. Admin quản lý provider và model

- Chỉ admin được thiết lập provider, API key, model mặc định và danh sách model
  nhân viên được phép dùng.
- Nhân viên chỉ chọn model trong danh sách được cấp; không xem API key hoặc
  thay đổi provider, API key và cấu hình mạng.
- Backend xác minh quyền admin và model được phép dùng, kể cả khi gọi API trực tiếp.
- API key chỉ được xử lý phía server; không trả về trình duyệt.

### 2. Admin quản lý đường kết nối

- Admin chọn kết nối trực tiếp hoặc SOCKS5, cấu hình địa chỉ/cổng proxy và kiểm tra
  kết nối từ máy chạy backend. Không phụ thuộc ứng dụng Hiddify hay Karing.
- Giao diện hiển thị cấu hình đang có hiệu lực, nguồn cấu hình và việc có cần
  khởi động lại backend hay không. Địa chỉ localhost luôn chỉ máy chạy backend.
- Cho phép thử cấu hình trước khi áp dụng; cấu hình không hợp lệ không thay thế
  cấu hình đang dùng. Không tự chuyển sang trực tiếp khi proxy lỗi.
- Phân biệt lỗi DNS, proxy, TLS, xác thực và lỗi phía provider bằng thông báo an toàn.
- Admin được cấu hình proxy riêng cho LLM (`LLM_PROXY_URL`) và embedding
  (`EMBEDDING_PROXY_URL`), gồm chế độ trực tiếp/SOCKS5, địa chỉ và cổng.
- Kiểm tra và hiển thị trạng thái riêng cho LLM và embedding; proxy embedding áp
  dụng cho cả truy vấn chat/tìm kiếm và worker xử lý tài liệu. Nhân viên không
  được thay đổi hai cấu hình này.
- Giữ kiểm tra địa chỉ đích và TLS; không nhầm lỗi embedding với lỗi LLM.
  Hiện tại hai proxy được cấu hình phía server; giao diện admin vẫn là To-be.

### 3. Nhân viên báo sự cố cho admin

- Khi LLM không hoạt động, hiển thị trạng thái và nút “Báo sự cố cho quản trị viên”.
- Nhân viên xem báo cáo, bổ sung mô tả rồi xác nhận gửi để tạo ticket.
- Ticket kèm thời điểm, model, bước thất bại và mã đối chiếu log nếu có; không tự
  đính kèm câu hỏi, câu trả lời hoặc tài liệu nội bộ.
- Không đưa API key, thông tin xác thực proxy hoặc dữ liệu nhạy cảm vào ticket/log.
- Admin nhận thông báo và cập nhật trạng thái xử lý; người báo xem được ticket
  của mình và nhận thông báo khi dịch vụ được khôi phục.
- Gộp các báo cáo cùng sự cố, ghi nhận số người bị ảnh hưởng.
- Sự cố làm toàn bộ dịch vụ LLM ngừng hoạt động có mức ưu tiên vận hành cao nhất.
  Lỗi một model khi còn model thay thế được phân mức theo phạm vi ảnh hưởng.
- Luồng tạo và xử lý ticket vẫn hoạt động khi LLM bị lỗi; không phụ thuộc LLM.

## Thứ tự phát triển

1. Cấu hình provider/API key tập trung, phân quyền và danh sách model được cấp.
2. Thiết lập đường kết nối, kiểm tra kết nối và trạng thái lỗi rõ ràng.
3. Ticket sự cố, gộp báo cáo và thông báo khôi phục.

Cấu hình bền vững và ticket dùng PostgreSQL; chốt schema, quan hệ với `.env`
và cách áp dụng thay đổi khi lập spec triển khai. Tài liệu này chỉ ghi định hướng,
chưa chốt API, schema hoặc hệ thống ticket cụ thể.

## Tài liệu liên quan

- [Backlog proxy admin](llm-proxy-admin-settings.md): chi tiết nền tảng direct/proxy;
  tài liệu này bổ sung quản trị provider/model và báo sự cố.
- [Tài khoản do admin cấp](admin-managed-accounts.md): định hướng quyền admin
  và tài khoản nhân viên.
