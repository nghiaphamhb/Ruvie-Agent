# Thiết lập proxy LLM cho quản trị viên

Trạng thái: To-be, chưa triển khai giao diện quản trị.
Ngày ghi nhận: 2026-10-09.

## Hiện trạng

- Backend hỗ trợ `LLM_PROXY_URL` trong `.env`.
- Để trống biến này: backend gọi nhà cung cấp trực tiếp.
- Có cấu hình SOCKS5: backend dùng proxy cho lấy model và gọi chat LLM.
- Proxy mất kết nối: yêu cầu thất bại; backend không tự chuyển sang trực tiếp.
- Hiện hỗ trợ `socks5://host:port`, chưa hỗ trợ HTTP/HTTPS proxy hoặc thông tin
  xác thực proxy.
- Chưa có giao diện bật/tắt proxy hay quyền quản trị cho thiết lập này.

## Định hướng đã ghi nhận

Cho quản trị viên backend lựa chọn hai chế độ:

| Chế độ | Hành vi |
| --- | --- |
| Trực tiếp, mặc định | Backend gọi nhà cung cấp không qua proxy. |
| Qua proxy | Backend dùng proxy do quản trị viên cấu hình. |

Không cho người dùng web thông thường tự nhập hoặc thay đổi proxy.
Thiết lập áp dụng chung cho backend, không theo tài khoản người dùng.

Ứng dụng cá nhân chạy tại máy người dùng: chủ máy có thể đồng thời là quản trị
viên. Ứng dụng dùng chung: quản trị viên server quản lý đường kết nối.
`127.0.0.1` trong URL proxy luôn chỉ máy chạy backend, không chỉ máy của người
đang mở web. Người dùng web không cần cài Hiddify trên máy họ.

## Task cần làm

- [ ] PROXY-01: Thiết kế giao diện cài đặt quản trị để chọn Trực tiếp/Qua proxy,
  hiển thị chế độ đang áp dụng và kiểm tra kết nối an toàn.
- [ ] PROXY-02: Bổ sung hoặc tái sử dụng cơ chế xác định quyền quản trị đáng tin
  cậy trên backend trước khi cho phép thay đổi cấu hình.
- [ ] PROXY-03: Chốt nguồn cấu hình có hiệu lực, cách lưu và cách áp dụng thay
  đổi, bao gồm quan hệ với `.env` và việc cần khởi động lại backend hay không.
- [ ] PROXY-04: Báo rõ lỗi proxy mất kết nối bằng thông tin an toàn. Không âm
  thầm chuyển đường mạng; chế độ tự chuyển, nếu cần, phải được quyết định riêng.
- [ ] PROXY-05: Thêm test quyền quản trị, hai chế độ, lỗi proxy và các kiểm tra
  bảo vệ mạng hiện có.

## Tiêu chí hoàn thành

- Người dùng không có quyền quản trị không đọc được thông tin cấu hình nhạy
  cảm và không thay đổi được proxy qua API hoặc giao diện.
- Chế độ Trực tiếp hoạt động khi mạng backend truy cập được nhà cung cấp.
- Chế độ Qua proxy dùng đúng proxy đã cấu hình cho cả lấy model và gọi chat.
- Giao diện cho biết chế độ đang áp dụng và thông báo rõ khi proxy lỗi.
- Giữ kiểm tra địa chỉ đích, ghim DNS/IP, xác minh TLS, chặn redirect và chặn
  địa chỉ bị cấm. Cấu hình proxy không cấp quyền truy cập mạng nội bộ.
- Không hiển thị API key, thông tin xác thực proxy hoặc nội dung phản hồi
  riêng tư của nhà cung cấp trong lỗi, log hoặc kiểm tra kết nối.

## Mã hiện tại để tái sử dụng

- `backend/ruvie/config.py`: đọc và kiểm tra `LLM_PROXY_URL`.
- `backend/ruvie/adapters/llm.py`: transport được bảo vệ và adapter dùng proxy.
- `backend/ruvie/services/llm.py`: truyền thiết lập server vào adapter.
- `tests/test_llm_proxy.py`: kiểm tra SOCKS, IP/TLS, redirect và lỗi proxy.

Đây là ghi chú công việc tương lai, không phải yêu cầu triển khai ngay.

## Mở rộng trang quản trị: Ngôn ngữ mặc định của tổ chức

Ngày bổ sung: 2026-10-10. Trạng thái: To-be, chưa triển khai.

Ngoài thiết lập proxy, kế hoạch trang quản trị cần có nhóm “Giao diện và ngôn
ngữ”. Nhóm này cho quản trị viên chọn ngôn ngữ mặc định của tổ chức. Đây là
thiết lập riêng; không gắn lựa chọn locale với chế độ proxy hoặc cấu hình LLM.

Yêu cầu chi tiết và thứ tự ưu tiên được quản lý tại
[backlog locale sau F008](ui-localization-evolution.md).

- Bộ chọn hiển thị Tiếng Việt (`vi-VN`), English (`en-US`), Русский (`ru-RU`)
  và lựa chọn “Không đặt mặc định — dùng ngôn ngữ trình duyệt”.
- Dự kiến áp dụng chung cho deployment hiện tại. Nếu có multi-tenant, chốt
  phạm vi tổ chức trong spec trước khi thêm data model hoặc API.
- Lựa chọn thủ công đã lưu của người dùng thắng mặc định tổ chức. Mặc định
  tổ chức thắng browser detection; fallback cuối cùng vẫn là vi-VN.
- Mặc định không thay ngôn ngữ trả lời LLM và không ghi đè browser storage.
- Hiển thị giá trị đang áp dụng, trạng thái lưu, lỗi an toàn và thời điểm có
  hiệu lực. Lưu thành công áp dụng cho khởi tạo/reload tiếp theo; không ép đổi
  locale hoặc remount các phiên đang mở.
- Backend xác minh quyền quản trị từ identity đáng tin cậy. Không tin role hoặc
  quyền tự khai từ request. Read/write admin settings được bảo vệ trên server.
- Luồng đọc trước đăng nhập chỉ trả locale mặc định cần cho UI. Không dùng
  endpoint đọc locale để trả cả proxy, API key hoặc cấu hình provider.
- Chốt nguồn cấu hình có hiệu lực, lưu trữ và quan hệ với cấu hình server trước
  khi code. Nếu có schema mới, dùng Alembic và giữ PostgreSQL là system of record.

### Task quản trị locale

- [ ] ADMIN-LOCALE-01: Thêm trường mặc định tổ chức và clear default vào thiết kế
  trang quản trị; dùng registry và LanguageSelector active khi phù hợp.
- [ ] ADMIN-LOCALE-02: Tái sử dụng cơ chế quyền quản trị từ PROXY-02, thiết kế
  read/write settings có validation locale và bảo vệ session/CSRF phù hợp.
- [ ] ADMIN-LOCALE-03: Chốt và implement lưu/áp dụng cấu hình; phối hợp LOCALE-01/
  LOCALE-02 để frontend trước đăng nhập chọn đúng default, không lộ secret.
- [ ] ADMIN-LOCALE-04: Test quyền, ba locale, clear default, input giả, lưu lỗi,
  ưu tiên stored choice và reload; cập nhật hướng dẫn quản trị.

### Tiêu chí hoàn thành phần quản trị locale

- Chỉ quản trị viên sửa được mặc định; gọi API trực tiếp không vượt quyền.
- Lưu/clear có kết quả rõ ràng; input không hợp lệ không thay giá trị đang áp dụng.
- Người mới không có stored choice thấy org default; người đã chọn giữ lựa chọn.
- Clear org default khôi phục browser detection, rồi fallback vi-VN.
- Proxy/direct vẫn hoạt động độc lập; không có cấu hình nhạy cảm trong response
  locale public, UI error hoặc log.

Các task PROXY hiện có giữ nguyên trạng thái. Bổ sung này chỉ ghi kế hoạch,
không triển khai trang quản trị hoặc thay đổi behavior F008 hiện tại.
