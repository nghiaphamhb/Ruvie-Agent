# F018 - Admin cấu hình kết nối mạng cho dịch vụ AI

Ngày lập: 2026-10-31.
Trạng thái: Đã chuẩn bị triển khai trên admin-proxy; chưa xác nhận nghiệm thu bằng test.
Kế thừa: [F016](F016-centralized-llm-management.md) và [F017](F017-ai-connections-and-embedding.md).
Tên module, trường dữ liệu và mã lỗi mới dưới đây là đề xuất triển khai.
Việc tạo spec không xác nhận các acceptance criteria đã đạt.

## Goal

Admin chọn kết nối trực tiếp hoặc qua proxy cho từng dịch vụ AI trong Ruvie Agent.
Lựa chọn xuất hiện ở cả Model trả lời và Model embedding.
Mỗi dịch vụ lưu cấu hình mạng riêng trong PostgreSQL.
Admin đổi cấu hình qua UI mà không phải sửa `.env` hoặc khởi động lại process.

Proxy là máy chủ trung gian nhận kết nối từ backend hoặc worker.
Endpoint proxy là địa chỉ và cổng của máy chủ đó, ví dụ `socks5://127.0.0.1:12334`.
Hiddify, Xapp và Karing là các ứng dụng có thể cung cấp endpoint.
Ruvie Agent cấu hình endpoint; không điều khiển các ứng dụng này.

### Code currently does

| Nguồn active đã kiểm tra | Hành vi hiện tại | Khoảng cách |
| --- | --- | --- |
| `backend/ruvie/config.py::Settings`, `load_settings` | Đọc `LLM_PROXY_URL` và `EMBEDDING_PROXY_URL`; chỉ nhận SOCKS5 không có thông tin xác thực | Cấu hình theo process; chưa có metadata/draft proxy trong DB |
| `services/llm.py::LlmConnectionService._adapter` | Truyền proxy từ settings vào adapter trả lời | Chưa lấy tuyến từ snapshot tổ chức |
| `services/embedding.py::EmbeddingConnectionService._adapter`, `resolve_embedder` | Provider/profile lấy từ DB; proxy vẫn lấy từ settings | Backend và worker cần snapshot cả tuyến từ DB |
| `adapters/llm.py::PinnedLlmTransport`, `OpenAICompatibleLlmAdapter._request_client` | Proxy tường minh; `trust_env=False`; kiểm tra đích provider, DNS pinning, TLS và redirect | Tái sử dụng; không thay bằng client mạng không được bảo vệ |
| `models/llm.py::OrganizationLlmSettings`, `models/embedding.py::OrganizationEmbeddingSettings` | Hai cấu hình singleton có version riêng | Chưa có trường phương thức và địa chỉ proxy |
| `contracts/llm.py::OrganizationConnectionDraft`, `contracts/embedding.py::EmbeddingConnectionDraft` | Draft embedding kế thừa draft trả lời; key write-only, expected_version | Cần bổ sung contract mạng dùng chung |
| `features/ai-connections/AiConnectionForm.svelte` | Form chung, bước kết nối, kiểm tra, model và áp dụng | Thêm lựa chọn mạng tại bước 1 cho cả hai form |
| Hai owner `organization-llm-state.svelte.ts`, `embedding-state.svelte.ts` | Draft riêng; invalidation, dirty, generation và reload confirmation | Bổ sung trường mạng vào cùng vòng đời |

Địa chỉ proxy hiện không bị ghi cứng trong code. Giá trị đến từ môi trường lúc
khởi động. Để trống nghĩa là trực tiếp. Thay đổi cần restart backend/worker.
Không đọc hoặc ghi `.env` thật để lập hoặc nghiệm thu spec này.

### Spec requires

- PostgreSQL là nguồn cấu hình mạng duy nhất sau bước chuyển đổi.
- Một cấu hình mạng cho model trả lời; một cấu hình mạng cho embedding.
- Catalog, kiểm tra model, áp dụng và runtime dùng đúng tuyến của dịch vụ tương ứng.
- Không tự chuyển trực tiếp khi proxy lỗi.
- Không lấy proxy từ request chat, truy xuất tài liệu hoặc browser storage.

### Proposed implementation và nguồn tái sử dụng

- Giữ `AiConnectionForm`; thêm phần mạng một lần trong component chung.
- Mở rộng API client và owner của từng dịch vụ. Không gộp hai owner thành state chung.
- Giữ snapshot, kiểm tra admin, version conflict và audit nguyên tử trong hai service.
- Giữ `PinnedLlmTransport` và adapter embedding hiện có. Truyền proxy từ snapshot
  hoặc draft tường minh, không dùng biến môi trường làm fallback runtime.
- Legacy đã đối chiếu: `references/backend/ruvie/routers/openai.py::get_models`
  tạo `aiohttp.ClientSession(trust_env=True)`. `references/backend/ruvie/config.py`
  có cấu hình proxy cho công cụ khác, không có contract phù hợp cho feature này.
  Không port `trust_env=True`, cookie forwarding hoặc proxy route legacy.
- Ưu tiên code active. Không import hoặc chạy runtime trong `references/`.
  Không đọc bất kỳ thư mục tên `archive`, không phân biệt hoa/thường.

## User Story

- Là admin, tôi muốn chọn kết nối trực tiếp khi provider truy cập được bình thường.
- Là admin, tôi muốn dùng endpoint từ ứng dụng proxy đang chạy trên máy chủ.
- Là admin, tôi muốn model trả lời dùng proxy nhưng embedding vẫn đi trực tiếp.
- Là admin, tôi muốn kiểm tra đúng tuyến trước khi áp dụng cho tổ chức.
- Là admin, tôi muốn biết lỗi thuộc proxy hay provider khi có bằng chứng phân biệt.
- Là người vận hành, tôi muốn chuyển cấu hình môi trường cũ mà không mất tuyến mạng.
- Là nhân viên, tôi muốn cấu hình mới có hiệu lực cho yêu cầu tiếp theo.

## Scope

### In

- Hai lựa chọn: `direct` và `proxy`. Cài đặt mới mặc định `direct`.
- Proxy SOCKS5 không username/password. Một endpoint cho mỗi dịch vụ.
- Form mạng lặp lại ở Model trả lời và Model embedding, tại bước 1.
- Admin GET/catalog/verify/probe/apply và runtime dùng cùng cấu trúc cấu hình mạng.
- Lưu DB, migration mới, version conflict, audit và snapshot theo request/job.
- Chuyển cấu hình cũ có chủ đích trước khi đưa phiên bản mới vào phục vụ.
- Nội dung Việt/Anh/Nga, bàn phím, focus và giao diện theo tokens của app.
- Kiểm thử direct/proxy bằng provider và proxy giả trong môi trường test.

### Out

- HTTP/HTTPS proxy, xác thực proxy, PAC, tự phát hiện proxy hệ điều hành.
- Chế độ tự động, thử proxy rồi direct, nhiều endpoint, failover hoặc cân bằng tải.
- Quản lý hồ sơ proxy theo tên ứng dụng, cài đặt hoặc khởi chạy ứng dụng proxy.
- Nhập subscription, cấu hình VPN/TUN hoặc đồng bộ cổng từ Hiddify/Xapp/Karing.
- Một proxy cá nhân cho mỗi nhân viên hoặc tùy chọn proxy trong màn hình chat.
- Proxy cho mọi HTTP request của ứng dụng hoặc thay đổi tuyến hệ điều hành.
- Thay embedding profile, reindex, thay ACL tài liệu hoặc sửa migrations đã áp dụng.
- Thay đổi UI quản trị khác đã được chỉnh trong phiên này.

## Flow

### 1. Hai form và vị trí điều khiển

Trong cả hai form, thứ tự bước 1 là Base URL → API key → Kết nối mạng → Kiểm tra
kết nối. Phần chọn mạng có cùng bố cục, nhãn và hành vi.

```text
1  Kết nối dịch vụ
   Địa chỉ API (Base URL)   [ ... ]
   API key                 [ Giữ key hiện tại ▾ ]

   Kết nối mạng
   Phương thức             [ Kết nối trực tiếp ▾ ]

   Khi chọn Qua proxy:
   Địa chỉ proxy           [ socks5://127.0.0.1:12334 ]
   Proxy phải truy cập được từ máy chạy backend và, với embedding, từ worker.

                                      [ Kiểm tra kết nối ]
```

- Dropdown chỉ có “Kết nối trực tiếp” và “Qua proxy”. Không có lựa chọn ứng dụng.
- Chọn trực tiếp ẩn ô proxy và bỏ yêu cầu nhập địa chỉ.
- Chọn proxy hiện ô có label và placeholder; địa chỉ là bắt buộc.
- Có thể giữ địa chỉ chưa lưu trong bộ nhớ của panel khi đổi qua lại để tiện chỉnh.
  Khi gửi `direct`, payload phải là `proxy_url: null`. Apply direct xóa endpoint
  đã lưu. Reload hoặc mở phiên settings mới không khôi phục endpoint đã xóa.
- Dùng dropdown theo style app; viền, góc bo, hover và focus theo component/tokens
  hiện có. Không thêm thư viện chỉ cho lựa chọn hai giá trị.
- IDs input, mô tả và lỗi phải khác nhau giữa hai form. Label hoạt động bằng bàn phím.
- Không ép câu hướng dẫn thành `nowrap`. “Một dòng hướng dẫn” nghĩa là một đoạn
  nội dung không lặp; cho phép xuống dòng trên màn hình hẹp hoặc khi dịch dài.

`127.0.0.1` là máy hoặc container chạy process gọi mạng, không phải máy mở browser.
Nếu backend và worker ở hai máy/container khác nhau, endpoint phải truy cập được
từ cả hai nơi; loopback có thể không phù hợp. Kiểm tra từ backend không chứng minh
worker ở máy khác truy cập được. UI không được thông báo ngược lại.

“Trực tiếp” chỉ có nghĩa Ruvie không cấu hình proxy riêng. VPN/TUN hoặc định tuyến
hệ điều hành vẫn có thể tác động. Không cam kết bỏ qua VPN.

### 2. Bản nháp, kiểm tra và áp dụng

1. Admin mở một form. GET đọc cấu hình mạng đã lưu cùng metadata provider.
2. Admin sửa phương thức hoặc endpoint. Owner đánh dấu dirty, hủy hiệu lực catalog/
   kết quả kiểm tra tuyến cũ, khóa apply và bỏ response cũ bằng generation hiện có.
   Giữ model đã chọn để hiển thị, không coi model đó đã được xác minh trên tuyến mới.
3. Đổi proxy không tự xóa key provider đang lưu hoặc đổi `key_action`. Base URL
   thay đổi vẫn tuân thủ quy tắc key của F016/F017. Không gửi API key tới endpoint
   như một request kiểm tra proxy riêng.
4. Kiểm tra kết nối gửi draft provider và mạng tới endpoint catalog hiện có.
   Backend xác thực admin, chuẩn hóa input và gọi provider qua đúng tuyến draft.
   Chỉ xác nhận catalog tải thành công. Không lưu DB hoặc đánh dấu apply thành công.
5. Kiểm tra model dùng cùng draft mạng. Embedding tiếp tục kiểm tra vector thật,
   đúng `baai/bge-m3`, 1024 chiều và cosine theo F017.
6. Apply không tin trạng thái verified do client gửi. Server kiểm tra provider/model
   lại qua tuyến draft theo contract hiện có. Không giữ transaction/lock qua mạng.
7. Sau probe, server kiểm tra lại actor và expected_version trong transaction.
   URL/key, policy hoặc profile, mạng, version và audit commit nguyên tử.
8. Thành công cập nhật metadata của panel đó, xóa dirty và invalidation cũ.
   Lỗi không đổi cấu hình active. Kết quả commit không rõ giữ cơ chế uncertain;
   không tự gửi lại PUT và không báo đã lưu chỉ vì GET đọc được một version mới.

Đổi tuyến sang proxy là quyết định tin cậy endpoint của admin. TLS với provider
vẫn được xác minh. Không tắt kiểm tra certificate để làm proxy hoạt động.

Chuyển giữa hai form giữ hai draft độc lập trong bộ nhớ settings. Reload có thay
đổi chưa lưu dùng hộp xác nhận hiện có. Rời settings/logout/mất quyền xử lý draft
và response muộn như F017; không lưu cấu hình mạng vào localStorage.

### 3. Contract API đề xuất

Giữ các endpoint hiện có ở `backend/ruvie/api/llm.py` và `api/embedding.py`.
Không thêm API cấu hình mạng riêng hoặc tham số chọn tuyến ở API nhân viên.

Mở rộng `OrganizationConnectionDraft` và các draft kế thừa bằng object `network`:

```json
{
  "network": {
    "mode": "proxy",
    "proxy_url": "socks5://127.0.0.1:12334"
  }
}
```

| Trường | Ràng buộc |
| --- | --- |
| `network` | Bắt buộc trên draft catalog, verify, probe và apply sau cutover |
| `mode` | Chính xác `direct` hoặc `proxy`; không nhận giá trị thứ ba |
| `proxy_url` | `null` khi direct; URL hợp lệ và không rỗng khi proxy |

Metadata GET và kết quả apply của admin trả cùng object mạng đã chuẩn hóa.
Không trả cấu hình mạng trong `/models`, chat hoặc metadata dành cho nhân viên.
Trường mới không thay nghĩa `expected_version`, `key_action` hoặc `configured`.
Client cũ thiếu `network` nhận lỗi validation; không âm thầm chuyển direct.
Triển khai frontend/backend cùng đợt; hướng dẫn reload browser sau nâng cấp.

Quy tắc endpoint:

- Chỉ scheme `socks5`; có hostname hoặc IP hợp lệ và cổng trong 1–65535.
- Cho phép loopback và địa chỉ mạng nội bộ vì proxy có thể chạy cùng máy/LAN.
- IPv6 dùng dấu ngoặc theo cú pháp URL. Chuẩn hóa scheme/hostname và dấu `/` cuối.
- Không username/password, query, fragment, API path, ký tự điều khiển hoặc backslash.
- Từ chối địa chỉ đích không thể dùng làm endpoint unicast: unspecified, multicast,
  broadcast và link-local/metadata. Kiểm tra DNS endpoint ở lúc kết nối để tránh
  đổi IP sau validation; không áp nguyên chính sách chặn private của provider cho
  proxy loopback/LAN. Chi tiết triển khai phải có test DNS rebinding cho endpoint.
- Không hỗ trợ `socks5h`: DNS provider vẫn được kiểm tra và pin phía server.
  Proxy không khắc phục được mọi lỗi DNS cục bộ; báo lỗi đúng giới hạn này.
- Độ dài URL giới hạn 2048 ký tự. Không echo input không hợp lệ hoặc exception thô.

### 4. Persistence và hiệu lực runtime

Đề xuất thêm `network_mode` và `proxy_url` vào cả hai bảng singleton hiện có.
Không tạo bảng profile proxy dùng chung vì mỗi loại chỉ cần một endpoint.
Migration kế tiếp dự kiến `0014_ai_network_connections.py`; xác minh Alembic head
khi triển khai. Giữ nguyên migrations 0012 và 0013.

Trạng thái bình thường có ràng buộc DB:

- `direct` đi cùng `proxy_url IS NULL`.
- `proxy` đi cùng `proxy_url IS NOT NULL` và chuỗi không rỗng.
- Có trạng thái chuyển đổi `network_mode IS NULL AND proxy_url IS NULL`, chỉ để
  đánh dấu row cũ chưa được người vận hành xác nhận; không phải lựa chọn UI.

Sau chuyển đổi, DB không còn row pending. Có thể giữ constraint cho trạng thái
pending để migration hỗ trợ triển khai an toàn; service phải từ chối sử dụng nó.
Các row tạo mới sau migration mặc định direct. Không lấy môi trường làm default DB.

Mở rộng `OrganizationSnapshot` và `EmbeddingSnapshot` bằng hai trường mạng.
Resolver truyền `None` vào transport khi direct, endpoint đã kiểm tra khi proxy.
Mỗi thao tác đóng băng URL/key/model/profile/tuyến/version cùng một snapshot.
Không giữ client toàn cục với proxy cũ sau apply.

| Consumer | Nguồn tuyến |
| --- | --- |
| Catalog/kiểm tra/apply trả lời | Draft trả lời của admin |
| Catalog nhân viên, chọn model và chat | Snapshot DB trả lời |
| Catalog/kiểm tra/apply embedding | Draft embedding của admin |
| Embedding truy vấn chat/tìm tài liệu | Snapshot DB embedding |
| Embedding nhập tài liệu | Snapshot DB embedding tại lúc bắt đầu xử lý job |

Job đang chạy giữ cùng tuyến cho các lô của job. Lần thử xử lý job mới lấy snapshot
mới. Đổi proxy không sửa revision, chunk hoặc citation và không đòi reindex.

### 5. Chuyển cấu hình môi trường cũ

Không đọc biến môi trường trong Alembic. Không tự import khi backend hoặc worker
khởi động. Không bỏ proxy đang dùng rồi âm thầm gửi request direct.

Đề xuất CLI vận hành `backend/ruvie/network_settings_cli.py` có chế độ kiểm tra
không ghi và chế độ xác nhận chuyển đổi. Đây là tên dự kiến, chưa tồn tại.
CLI đọc hai giá trị cũ bằng parser settings hiện có, chỉ trong bước chuyển đổi.
Giá trị có endpoint hợp lệ → proxy; giá trị trống → direct, sau xác nhận của operator.
Operator phải chạy ở môi trường có đúng cấu hình cũ của deployment.

Trình tự triển khai:

1. Kiểm tra backend và worker đang dùng cùng giá trị cũ cho embedding.
2. Dừng nhận request/job mới và để thao tác đang chạy hoàn tất; dừng các process cũ.
   Không chạy đồng thời phiên bản cũ dùng env và phiên bản mới dùng DB.
3. Áp migration: rows đã tồn tại nhận trạng thái pending. Không sửa provider/key/profile.
4. CLI kiểm tra cả hai row, endpoint và version. Kết quả chỉ hiện loại kết nối,
   phương thức và số lượng row dự kiến; không in key hay endpoint nội bộ ra log.
5. Operator xác nhận. CLI kiểm tra actor là admin active trong DB; chuyển cả hai row
   trong một transaction với expected versions, ghi audit cho từng loại.
   Row configured tăng version. Row version 0 vẫn chưa cấu hình provider và không
   bị biến thành configured chỉ vì đã chuyển tuyến mạng.
6. Bất kỳ lỗi validation/quyền/conflict nào rollback cả hai row. Chạy lại với row
   đã chuyển chỉ báo đã hoàn tất; không ghi đè cấu hình admin đã lưu sau đó.
7. Khởi động backend/worker mới. Kiểm tra hai form; thực hiện một yêu cầu embedding
   qua worker bằng môi trường kiểm chứng phù hợp trước khi mở lại nhận job.
8. Bỏ hai biến cũ khỏi cấu hình vận hành theo hướng dẫn. Runtime không đọc chúng;
   CLI chuyển đổi là nơi duy nhất còn xử lý chúng trong giai đoạn chuyển tiếp.

Nếu còn row pending, runtime/admin API trả mã `network_configuration_pending`
an toàn trước khi gọi provider. Không coi pending là direct. Công cụ vận hành là
cách giải quyết trạng thái này. Downgrade phải được lập kế hoạch vận hành riêng;
không hứa tự khôi phục proxy môi trường sau khi đã đổi qua UI.

### 6. Lỗi, quyền và bảo vệ dữ liệu

| Mã đề xuất | Khi dùng | Hành vi UI/runtime |
| --- | --- | --- |
| `invalid_network_configuration` | Draft sai schema hoặc endpoint không hợp lệ | 422; lỗi cạnh trường tương ứng; giữ draft |
| `proxy_unavailable` | Có bằng chứng lỗi kết nối/handshake với proxy | 503; hướng dẫn kiểm tra ứng dụng, địa chỉ và cổng; không direct fallback |
| `network_configuration_pending` | Row cũ chưa chuyển đổi | 503; hướng dẫn admin liên hệ người vận hành; không probe |
| `configuration_conflict` | Version đã thay đổi | 409; giữ cơ chế reload có xác nhận hiện tại |
| Mã provider/model hiện có | Provider từ chối key/model hoặc lỗi provider | Giữ phân loại và hành vi F016/F017 |

Không phải mọi timeout đều xác định được nguyên nhân. Khi không chắc, dùng lỗi
kết nối dịch vụ an toàn; không khẳng định proxy lỗi hoặc key sai.
Nút kiểm tra phải đi tới provider qua tuyến đã chọn. Không coi TCP port mở là thành công.

- Admin active được kiểm tra từ DB trước mạng và trước commit. POST/PUT giữ Origin/CSRF.
- Employee không đọc/sửa proxy kể cả tự gọi admin API. Giá trị client không cấp quyền.
- Không nới `LLM_ALLOWED_LOCAL_ORIGINS`, không bỏ DNS pinning/provider IP checks,
  không theo redirect, không bật `trust_env` hoặc tắt TLS.
- Giữ cookie stripping. Không đưa key vào URL, log, audit hoặc thông báo lỗi.
- Audit ghi actor, loại kết nối, version và mode; không ghi URL proxy hoặc provider.
- Endpoint không chứa credentials nên có thể lưu dạng text và trả cho admin. Không
  đưa endpoint vào response nhân viên, metrics labels hoặc log exception thô.
- Đổi mạng không làm thay đổi quyền đọc tài liệu, project hoặc chính sách model.

## Edge Cases

- Direct với URL proxy gửi kèm: từ chối thay vì lặng lẽ bỏ trường dư.
- Proxy URL trống, sai cổng, chứa password hoặc API path: từ chối trước mọi network I/O.
- Proxy chưa chạy hoặc đổi cổng: lỗi an toàn, giữ cấu hình active và draft.
- Proxy hoạt động nhưng provider không truy cập được: không báo kiểm tra thành công.
- TUN/VPN đang bật: direct vẫn chịu định tuyến OS; không coi đó là lỗi UI.
- Backend tới được loopback nhưng worker ở container khác không tới được: job thất bại
  bằng mã embedding an toàn; không dùng tuyến khác hoặc báo backend verify đã kiểm tra worker.
- DNS provider lỗi hoặc trả đích bị chặn: không chuyển việc resolve sang proxy để vượt guard.
- Đổi tuyến khi kiểm tra đang chạy: kết quả tuyến cũ không cập nhật verified/catalog.
- Hai admin apply cùng version: chỉ một commit; bên còn lại nhận conflict.
- Mất quyền trong thời gian probe: không commit cấu hình, không lộ kết quả quản trị mới.
- Apply đã commit nhưng response mất: không tự PUT lại; giữ reconciliation hiện có.
- Chuyển proxy một form: không sửa phương thức, model, key hoặc version của form kia.
- Embedding catalog đã tải nhưng đổi proxy trước probe model: phải tải/kiểm tra lại.
- Chuyển đổi thất bại một row: rollback cả hai; không chạy bản mới với cấu hình nửa vời.
- Provider chưa cấu hình: mặc định form direct hoặc mạng đã chuyển có chủ đích;
  vẫn không cho runtime sử dụng provider chưa cấu hình.

## Acceptance Criteria

- [ ] Cả hai form có phần Kết nối mạng đúng vị trí, cùng nhãn và hành vi.
- [ ] Mặc định cài mới direct; ô proxy chỉ xuất hiện và bắt buộc khi chọn proxy.
- [ ] Chọn direct gửi `proxy_url: null`; apply direct xóa endpoint DB đã lưu.
- [ ] Hai draft độc lập, hỗ trợ reload confirmation, mất quyền và response muộn.
- [ ] Đổi mode/endpoint đánh dấu dirty, bỏ kết quả kiểm tra cũ và khóa apply.
- [ ] Catalog, probe và apply dùng đúng draft mạng; kiểm tra không lưu DB.
- [ ] Metadata mạng chỉ hiện với admin; API nhân viên không chấp nhận hoặc trả endpoint.
- [ ] Schema và DB từ chối tổ hợp mode/endpoint sai; URL credential/path sai bị chặn.
- [ ] Proxy loopback/LAN hợp lệ được hỗ trợ; kiểm tra endpoint không bỏ chặn DNS/IP nguy hiểm.
- [ ] Guard đích provider, TLS, redirect, cookies và `trust_env=False` có test hồi quy.
- [ ] Proxy lỗi không phát sinh request direct thứ hai.
- [ ] Apply kiểm tra lại quyền/version; provider/policy/profile/mạng/audit commit nguyên tử.
- [ ] Đổi tuyến trả lời không thay đổi embedding và ngược lại.
- [ ] Request/job mới dùng DB mới không restart; thao tác đang chạy giữ snapshot cũ.
- [ ] Query embedding và ingestion worker dùng cùng cấu hình DB; profile vẫn 1024/cosine.
- [ ] Migration mới không đọc môi trường; row cũ pending không âm thầm trở thành direct.
- [ ] CLI chuyển đổi có dry-run, xác nhận, quyền admin, version checks, rollback và chạy lại an toàn.
- [ ] Sau cutover runtime bỏ qua hai biến proxy cũ và mọi ambient HTTP(S)/ALL_PROXY.
- [ ] Lỗi phân loại theo bằng chứng, không lộ endpoint/secret, không claim đã kiểm tra worker từ backend.
- [ ] Việt/Anh/Nga đầy đủ; keyboard, focus, màn hình hẹp và hai theme được kiểm tra render.
- [ ] Test migration/PostgreSQL, adapter, service/API, worker và frontend có kết quả thực tế.
  Skip hoặc kiểm tra chưa chạy được ghi riêng; không coi là pass.

## Tasks

Tất cả đường dẫn tạo mới dưới đây là đề xuất. Triển khai cần kiểm tra lại Alembic
head và quy tắc duyệt file. Không đánh dấu task hoàn thành chỉ vì đã viết spec.

- [ ] **F018-001 — Contract mạng và persistence**
  - **Work:** Định nghĩa object mạng, validation và metadata admin. Thêm cột,
    constraints, trạng thái pending cho rows cũ và default direct cho rows mới.
  - **Where:** Mở rộng `backend/ruvie/contracts/llm.py`, `contracts/embedding.py`,
    `models/llm.py`, `models/embedding.py`; đề xuất migration
    `backend/migrations/versions/0014_ai_network_connections.py`.
    Đề xuất test `tests/test_f018_001_network_schema.py`.
  - **Done:** Contract từ chối input sai; SQL migration được kiểm tra; PostgreSQL
    giữ provider/key/profile cũ; rows pending/direct/proxy tuân thủ constraint.

- [ ] **F018-002 — Transport mạng tường minh và endpoint guard**
  - **Work:** Tái sử dụng transport; thêm chuẩn hóa/kiểm tra endpoint dùng chung,
    pin đích proxy nếu cần; phân loại lỗi có bằng chứng. Không fallback direct.
  - **Where:** `backend/ruvie/adapters/llm.py`, `adapters/embedding.py`, `config.py`;
    đề xuất helper `backend/ruvie/adapters/network.py` nếu trách nhiệm cần tách.
    Đề xuất test `tests/test_f018_002_network_transport.py`; đối chiếu hồi quy
    `tests/test_llm_proxy.py`, `tests/test_embedding_proxy.py` trước khi quyết định sửa.
  - **Done:** Fake proxy chứng minh tuyến proxy/direct; chứng minh không fallback,
    không cookie leakage, không redirect/TLS bypass hoặc DNS rebinding.

- [ ] **F018-003 — Snapshot, service và admin API**
  - **Work:** Truyền mạng qua draft/snapshot/adapter; metadata và commit nguyên tử.
    Giữ key actions, version và quyền; bổ sung lỗi pending/proxy an toàn.
  - **Where:** `backend/ruvie/services/llm.py`, `services/embedding.py`,
    `api/llm.py`, `api/embedding.py`. Đề xuất test
    `tests/test_f018_003_network_api.py`.
  - **Done:** Catalog/probe/apply dùng đúng tuyến; conflict/mất quyền không ghi;
    employee không đọc/sửa được; payload lỗi không lộ cấu hình.

- [ ] **F018-004 — Runtime backend và ingestion worker**
  - **Work:** Resolve tuyến DB theo request/job; loại env fallback runtime;
    xác minh caller không giữ client proxy cũ qua các thao tác độc lập.
  - **Where:** Resolver trong `services/llm.py`, `services/embedding.py`;
    kiểm tra callers ở `services/chat.py`, `services/retrieval.py`,
    `services/documents/ingestion.py`, `worker_cli.py`, `main.py` trước khi sửa.
    Đề xuất test `tests/test_f018_004_network_runtime.py`; tái sử dụng fixture
    trong `tests/test_f017_005_embedding_runtime.py`, `test_f017_008_embedding_worker.py`.
  - **Done:** Backend/worker nhận thay đổi ở thao tác mới; đang chạy giữ snapshot;
    nội dung/citation/profile/ACL không thay đổi.

- [ ] **F018-005 — Hai form cấu hình mạng**
  - **Work:** Bổ sung control chung; mở rộng payload/metadata của hai client và owner;
    dirty/invalidation/reload; hướng dẫn địa chỉ máy chủ và lỗi dịch an toàn.
  - **Where:** `frontend/src/lib/features/ai-connections/AiConnectionForm.svelte`,
    `features/llm/organization-llm-api.ts`, `organization-llm-state.svelte.ts`,
    `features/embedding/embedding-api.ts`, `embedding-state.svelte.ts`;
    `frontend/src/lib/i18n/locales/{vi-VN,en-US,ru-RU}/translation.json`.
  - **Done:** Hai form giống bố cục, lưu độc lập; không tự gửi/lưu khi đổi dropdown;
    request cũ không bật apply; không lặp đoạn hướng dẫn.

- [ ] **F018-006 — Công cụ chuyển đổi và hướng dẫn vận hành**
  - **Work:** CLI dry-run/confirm chuyển hai env cũ theo quy trình; transaction và
    audit; chạy lại an toàn; báo pending khi chưa chuyển. Viết thứ tự triển khai.
  - **Where:** Đề xuất `backend/ruvie/network_settings_cli.py`,
    `tests/test_f018_006_network_cutover.py`; cập nhật `README.md`, `.env.example`,
    `docs/database-setup.md` ở giai đoạn triển khai. Không sửa `.env` thật.
  - **Done:** Test chuyển cả proxy/direct, row version 0, invalid input, conflict,
    rollback và no-overwrite; hướng dẫn không yêu cầu reset application DB.

- [ ] **F018-007 — Kiểm thử UI và tích hợp**
  - **Work:** Kiểm tra hai form, payload, lifecycle, bàn phím, focus, hai theme và
    màn hình hẹp; kiểm thử proxy/provider giả và PostgreSQL dùng một lần.
  - **Where:** Mở rộng `frontend/tests/f016-organization-llm-api.test.mjs`,
    `f016-organization-llm-state.test.mjs`, `f017-embedding-api.test.mjs`,
    `f017-embedding-state.test.mjs`, `f017-embedding-lifecycle.test.mjs`;
    đề xuất `frontend/tests/f018-network-browser.mjs`,
    `tests/test_f018_007_network_postgres.py`.
  - **Done:** Mọi AC có kiểm chứng phù hợp; full backend và frontend checks theo
    README/AGENTS được chạy. Không chạy hai backend suites cùng lúc. Không dùng
    provider keys thật hoặc cơ sở dữ liệu ứng dụng để chạy test.

- [ ] **F018-008 — Cập nhật kiến trúc và bàn giao**
  - **Work:** Cập nhật phần hiện trạng sau khi code được nghiệm thu; ghi kết quả
    test, skip, giới hạn và hướng dẫn cutover đã được kiểm chứng.
  - **Where:** `specs/02-architecture.md`, spec F018 này; cập nhật liên kết từ
    F017 nếu cần, không viết lại các ghi nhận lịch sử của feature cũ.
  - **Done:** Phân biệt rõ current/target; chưa hoàn thành không đánh dấu xong.
    Generated build, cache, logs và secrets không được commit.

## Báo cáo sau triển khai code — 2026-10-31

- Code đã được chuẩn bị cho F018-001…008: contract và metadata, hai cột DB,
  Alembic 0014, endpoint SOCKS5 DNS guard, route theo draft/snapshot, service/API,
  frontend dùng chung, i18n Việt/Anh/Nga, CLI cutover, bộ test và hướng dẫn.
- Đã đối chiếu qua GitHub connector với code active ở branch admin-proxy.
- **Chưa chạy:** full backend suite, frontend test/build/lint/format,
  test PostgreSQL/Docker, test browser Playwright, render giao diện hai theme
  hoặc kiểm chứng thực tế của backend/worker cùng kết nối proxy. Không được tính
  các test mới viết là pass; checkbox AC/tasks phía trên vẫn giữ chưa hoàn tất.
- **Triển khai vận hành chưa thực hiện:** Chưa apply migration trên DB ứng dụng,
  chưa chạy cutover CLI bằng môi trường cũ, chưa đổi env hệ thống, chưa restart
  backend/worker. Cần bảo trì theo docs/database-setup.md khi phát hành.
- Chú ý: bộ test F018 cần được chạy trong checkout có đầy đủ dependencies và
  PostgreSQL dùng một lần; chỉ sau khi kiểm chứng mới cập nhật trạng thái đạt.

## Sửa lỗi sau review — 2026-10-31

Phạm vi được duyệt: năm nhóm lỗi trong review F018; không triển khai lên DB ứng dụng.

- `backend/migrations/env.py` ghi nhận revision khởi đầu. Migration mới
  `0015_ai_network_constraints.py` chỉ khởi tạo direct khi chuỗi nâng cấp bắt đầu
  từ DB chưa có revision. Deployment cũ version 0 vẫn pending. Giữ nguyên 0012–0014.
- Hai model `models/llm.py`, `models/embedding.py` và migration 0015 dùng CHECK
  `IS TRUE`, từ chối cả SQL UNKNOWN cho tổ hợp mode NULL kèm endpoint.
- `dependencies.py::get_query_embedder` chuyển lỗi pending, endpoint sai và proxy
  không khả dụng thành 503 `embedding_unavailable`, không lộ thông tin mạng.
- `adapters/network.py::ProxyNetworkBackend` phân loại lỗi TCP tại kết nối proxy;
  `ProxyUnavailableError` thuộc nhóm HTTPX để các consumer runtime giữ xử lý lỗi
  an toàn. `adapters/llm.py::PinnedLlmTransport` dùng backend này cho SOCKS và
  chuẩn hóa lỗi handshake; lỗi DNS/TLS provider không bị gán nhầm cho proxy.
  HTTPX chưa cung cấp tham số network backend trên HTTPTransport nên hook nằm
  tại SOCKS pool nội bộ; test hồi quy bảo vệ hành vi này khi nâng dependency.
- Frontend production chỉ chuẩn hóa định dạng các file form/API/state F018.
  Fixture F016/F017 bổ sung network tường minh, giữ contract production bắt buộc.
  State test chuyển vào `f018-network.test.mjs` để lệnh test mặc định chạy được.
  `f018-network-browser.mjs` nay chạy Chromium thật cho hai form, keyboard,
  invalidation, payload direct/proxy, ba locale và hai theme.
- Tái sử dụng fixture PostgreSQL/provider active trong `test_f005_007_e2e.py`,
  adapter/transport active và fixture ingestion; không port thêm legacy runtime.
  Quy tắc default-deny, nội dung revision/chunk, profile và private blob giữ nguyên.

### Kiểm chứng

- Frontend: 122 pass, 0 fail, 0 skip; build, ESLint và Prettier check đạt.
- Browser standalone: F016 đạt 13 checks; F017 đạt 13 checks; F018 đạt 12 kịch bản
  (hai form × ba locale × hai theme). Ảnh kiểm tra nằm trong `logs/f018-browser/`.
- Backend full suite: 399 pass, 0 fail, 0 skip trong 1034.168 giây; browser E2E
  đã được bật bằng Playwright/Chromium. Log: `logs/f018-backend.txt`.
- Focused F018 cuối: 20 pass, 0 fail, 0 skip trong 43.219 giây. Có kiểm tra
  PostgreSQL mới/cũ, CHECK, rollback cutover, SOCKS/provider giả chạy TCP thật,
  worker đọc tuyến DB và adapter snapshot cũ sau apply. Log: `logs/f018-focused.txt`.
- Review độc lập không tìm thấy lỗi cần sửa thêm trong diff production.
  `git diff --check` đạt; migrations 0012–0014 không có diff.
- Lượt backend trước bị dừng do hết quota; không được tính là pass.
- Chưa apply migration/cutover trên DB ứng dụng, chưa restart backend/worker vận hành.
  Checkbox nghiệm thu toàn feature giữ nguyên; báo cáo này chỉ xác nhận phạm vi
  sửa lỗi và các kiểm tra có kết quả thực tế.

Lệnh kiểm tra theo README/AGENTS: backend `python -B -m unittest discover -v -s tests
-p 'test_*.py'`; frontend `npm --prefix frontend run build`, `npm --prefix frontend
test`, `npm --prefix frontend run lint`, `npm --prefix frontend run format:check`.
Focused: `.venv/Scripts/python.exe -B -m unittest discover -v -s tests -p 'test_f018_*.py'`.
Browser: `node frontend/tests/f016-organization-llm-browser.mjs`,
`node frontend/tests/f017-ai-connections-browser.mjs`,
`node frontend/tests/f018-network-browser.mjs` với Playwright/Chromium được cấu hình.
Generated build/logs/screenshots không commit.
