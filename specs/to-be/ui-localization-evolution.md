# Phát triển locale sau F008

Trạng thái: To-be, chưa triển khai các yêu cầu trong tài liệu này.
Ngày ghi nhận: 2026-10-10.

## Hiện trạng

F008 đã cung cấp Tiếng Việt (`vi-VN`), English (`en-US`) và Русский (`ru-RU`).
Active app chọn locale theo thứ tự: lựa chọn thủ công đã lưu trong
`ruvie.ui.locale` → ngôn ngữ trình duyệt → Tiếng Việt.
Chỉ thao tác chọn của người dùng được lưu. Catalog được nạp tĩnh.
Fallback cho khóa dịch thiếu/rỗng là English, độc lập với locale khởi tạo.

Mã active để tái sử dụng:

- `frontend/src/lib/i18n/locale.ts`: registry validation và resolver.
- `frontend/src/lib/i18n/index.ts`: init, đổi locale, store, storage và format số.
- `frontend/src/lib/i18n/messages.ts`: thông báo theo key/tham số.
- `frontend/src/lib/components/LanguageSelector.svelte`: bộ chọn native.
- `frontend/tests/i18n.test.mjs`, `frontend/tests/i18n-browser.mjs`: coverage F008.
- [Spec F008](../feat/archive/F008-ui-localization.md): hành vi đã triển khai.

## Yêu cầu tương lai và thứ tự ưu tiên

### 1. Ngôn ngữ mặc định của tổ chức — ưu tiên tiếp theo

- Server cung cấp một locale mặc định tùy chọn cho tổ chức sử dụng Ruvie Agent.
- Với mô hình hiện tại, dự kiến áp dụng chung cho một deployment. Không tự thêm
  tenant hoặc bảng tổ chức. Nếu có multi-tenant sau này, phải chốt lại phạm vi.
- Khi chưa có URL override, thứ tự lựa chọn mới là:
  lựa chọn thủ công đã lưu → mặc định tổ chức → trình duyệt → `vi-VN`.
- Chỉ nhận locale trong registry được hỗ trợ. Cho phép bỏ mặc định tổ chức để
  quay về quy tắc trình duyệt. Không mặc nhiên đặt vi-VN ở server, vì như vậy
  browser detection sẽ không còn được dùng.
- Mặc định tổ chức không ghi vào `ruvie.ui.locale` và không thay lựa chọn đã lưu.
- Thay mặc định có hiệu lực khi khởi tạo/reload tiếp theo; không đổi ngôn ngữ
  hoặc remount những phiên đang mở.
- Giai đoạn đầu có thể cấu hình trên server. Khi có trang quản trị, thêm bộ
  chọn ở nhóm “Giao diện và ngôn ngữ”, dùng tên bản địa của ba locale.
- Frontend trước đăng nhập chỉ cần đọc locale mặc định an toàn. Không trả kèm
  cấu hình proxy, API key, endpoint provider hoặc quyền quản trị.
- Khi đọc cấu hình thất bại, app vẫn khởi tạo bằng lựa chọn đã lưu hoặc quy tắc
  trình duyệt/fallback. Chốt timeout và luồng khởi tạo để tránh nhấp nháy locale.
- Chốt nguồn cấu hình, nơi lưu và cách áp dụng trước implementation. Nếu lưu
  persistent settings, dùng PostgreSQL và Alembic khi cần thay schema.

Phần giao diện/quyền quản trị được ghi tại
[kế hoạch trang quản trị hiện có](llm-proxy-admin-settings.md).

### 2. Định dạng ngày giờ — khi UI có dữ liệu thời gian

- Dùng helper chung dựa trên `Intl.DateTimeFormat` cho ngày tải tài liệu,
  lịch sử chat và thời điểm xử lý khi các màn hình này có timestamp.
- Locale quyết định cách trình bày ngày giờ. Múi giờ là quyết định riêng;
  không suy ra múi giờ từ ngôn ngữ hoặc tự thêm thiết lập timezone trong task này.
- Giữ timestamp gốc và hợp đồng API; format ở lúc render, không lưu chuỗi đã
  format vào state lâu dài. Đổi locale phải cập nhật thời gian đang hiển thị.
- Chốt timezone dùng để hiển thị, xử lý timestamp thiếu/sai và test thời điểm
  đổi ngày theo timezone khi tạo spec chi tiết.
- Dùng API Intl có sẵn; không thêm dayjs chỉ để định dạng.

### 3. Locale qua URL — khi cần chia sẻ link/hướng dẫn

- Hỗ trợ `?lang=vi-VN`, `?lang=en-US`, `?lang=ru-RU` khi khởi tạo giao diện.
- Giá trị hợp lệ áp dụng tạm thời cho lần mở đó, ưu tiên trước lựa chọn đã lưu.
  Khi không có giá trị hợp lệ, dùng thứ tự của mục 1.
- URL không ghi đè storage. Thao tác chọn bằng selector sau khi mở app thắng
  lựa chọn từ URL và mới được lưu như hành vi hiện tại.
- Query không hợp lệ hoặc nhiều giá trị phải có quy tắc rõ trước triển khai;
  không dùng query để tạo đường dẫn import catalog tùy ý.
- Không đưa lang vào payload chat/retrieval hoặc dùng nó làm ranh giới quyền.

### 4. Nạp catalog theo nhu cầu — khi số lượng/kích thước tăng

- Với ba catalog nhỏ hiện tại, giữ nạp tĩnh. Chỉ triển khai khi số locale hoặc
  kích thước catalog tăng và có số đo cho thấy cần giảm bundle ban đầu.
- Khi cần, nạp catalog qua mapping locale/namespace được cho phép, không import
  trực tiếp từ chuỗi query hoặc storage chưa kiểm tra.
- Nạp locale đang dùng và fallback English; cache catalog đã nạp trong phiên.
- Bổ sung trạng thái tải/lỗi/thử lại, giữ giao diện usable khi tải thất bại.
  Chốt cách giữ locale cũ hoặc fallback, không để label rỗng hoặc mất form state.
- Yêu cầu lựa chọn mới nhất thắng khi người dùng đổi nhanh nhiều locale.
  Việc tải catalog không được gửi lại hoặc hủy request nghiệp vụ đang chạy.

## Quy tắc giữ nguyên và phạm vi riêng

- Không tự lưu locale do trình duyệt, tổ chức hoặc URL phát hiện. Storage chỉ
  phản ánh lựa chọn thủ công để phân biệt rõ nguồn lựa chọn.
- Ngôn ngữ giao diện không quyết định ngôn ngữ trả lời LLM. Cần ghi rõ điều này
  trong nội dung trợ giúp cạnh thiết lập ngôn ngữ khi phù hợp.
- Nếu cần chọn ngôn ngữ trả lời LLM, tạo feature/spec riêng. Chưa chốt prompt,
  API hoặc UI của feature đó trong backlog này.
- Giữ dữ liệu ngoài nguyên văn; không dịch tên tài liệu/model/project/file,
  nội dung câu hỏi/câu trả lời hoặc citation.
- Giữ ACL, immutable revisions, private storage và server-side provider settings.

## Task cần làm

- [ ] LOCALE-01: Thiết kế nguồn cấu hình mặc định tổ chức, luồng đọc an toàn trước
  đăng nhập và resolver mới; phối hợp ADMIN-LOCALE trong kế hoạch quản trị.
- [ ] LOCALE-02: Implement mặc định tổ chức, validation và fallback; kiểm tra
  stored choice thắng org default, clear default và failure khi đọc cấu hình.
- [ ] LOCALE-03: Thêm helper ngày giờ khi UI có timestamp; chốt timezone và test
  đổi locale trên cùng timestamp, không sửa dữ liệu nguồn.
- [ ] LOCALE-04: Thiết kế/implement URL override khi cần share link; test giá trị
  hợp lệ/sai, ưu tiên, không ghi storage và thao tác chọn sau khởi tạo.
- [ ] LOCALE-05: Đo bundle/catalog trước khi quyết định lazy loading. Nếu cần,
  thêm cache, loading/error/retry, fallback và kiểm tra race khi đổi nhanh.
- [ ] LOCALE-06: Thêm trợ giúp phân biệt UI locale với ngôn ngữ trả lời LLM;
  cập nhật README và regression tests theo từng phần đã triển khai.

## Tiêu chí kiểm tra khi triển khai

- Stored choice vẫn thắng org default; browser được dùng khi org default trống.
- Mỗi nguồn locale chỉ nhận ba mã hỗ trợ; giá trị giả không làm app crash.
- Org default dùng được ở màn hình đăng nhập mà không lộ cấu hình nhạy cảm.
- Người không có quyền quản trị không sửa được org default, kể cả gọi API trực tiếp.
- URL override tạm thời, không ghi storage; chọn thủ công sau đó có hiệu lực.
- Ngày giờ dùng locale hiện tại và timezone đã chốt, giữ timestamp gốc.
- Lazy loading có hành vi xác định khi lỗi/race, không làm mất state/request.
- Hồi quy F008 tiếp tục qua: keyboard, storage lỗi, safe errors, plural, layout,
  state và request/SSE đang chạy. Chạy các lệnh test theo README cho phạm vi đổi.

## Legacy để tham khảo

| Nguồn read-only | Hành vi tham khảo | Điều cần thích nghi |
| --- | --- | --- |
| `references/src/routes/+layout.svelte` | `backendConfig.default_locale`, browser matching và `dayjs.locale(lang)` khi khởi tạo | Stored choice rõ ràng; Intl cho ngày giờ; không port toàn bộ layout/config legacy. |
| `references/src/lib/i18n/index.ts` | `lookupQuerystring: 'lang'`, dynamic resources và loading/failure events | URL tạm thời, allowlist import, fallback English và giữ request/state active. |
| `references/src/lib/components/chat/Settings/General.svelte` | Native language select và tên bản địa | Dùng registry/component active trước; bổ sung trường mặc định tổ chức trong trang quản trị. |

Đây là backlog phát triển tương lai, không phải yêu cầu triển khai ngay.
Các task chưa được đánh dấu hoàn thành. F008 đã hoàn tất giữ nguyên phạm vi.
