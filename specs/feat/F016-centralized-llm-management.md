# F016 - Quản lý LLM tập trung cho tổ chức

Ngày lập: 2026-10-29.
Trạng thái: Hoàn thành bàn giao chức năng theo xác nhận của người dùng ngày 2026-10-30; còn tồn đọng kiểm chứng được ghi bên dưới.
Commit bàn giao: `d0530fe` (`feat: admin sets up shared chat model`).
Feature tiếp theo: [F017 - Tách kết nối AI và quản lý kết nối embedding](F017-ai-connections-and-embedding.md).
Baseline đã kiểm tra: `96d1bb0` (`feat: admin deactive/reactive user account`).
Các phần hiện trạng, kế hoạch và tiến độ bên dưới giữ lại lịch sử tại thời điểm lập.
Không dùng các mô tả baseline đó để suy ra trạng thái code tại commit bàn giao.

### Chốt bàn giao ngày 2026-10-30

- Người dùng yêu cầu đóng F016 và chuyển sang F017. Chức năng quản lý model trả lời
  tập trung đã bàn giao tại commit nêu trên.
- Kiểm chứng mới nhất trong phiên làm việc: frontend suite 110 pass, 0 fail/skip;
  browser component 25 checks và browser tổ chức 13 checks đạt. Build/lint/format đạt.
  Sau chỉnh vị trí API key, test form 1/1 và browser tổ chức 13 checks tiếp tục đạt.
- Full backend gần nhất được ghi nhận vẫn là 355 test: 347 pass, 1 fail, 7 skip.
  Không chạy lại full suite trong lần đóng tài liệu này. Các regression workspace,
  LLM/i18n và bốn tệp đã bị từ chối sửa vẫn phải đối chiếu khi thực hiện F017.
- Trạng thái hoàn thành bàn giao không có nghĩa mọi acceptance/test đã xanh.
  Giữ các checkbox task/AC chưa đủ bằng chứng; không đánh dấu pass thay cho fail/skip.
- Migration 0012 đã có trên application DB qua bước vận hành sau đó; khác với ghi
  nhận lịch sử “không chạy migration” tại thời điểm kiểm chứng phía dưới.
- F017 tách UI thành Model trả lời/Model embedding. F017 không mở lại fallback LLM
  cá nhân hoặc môi trường và không tự thay đổi embedding profile của tài liệu.

Tiến độ ngày 2026-10-29: đã code migration 0012, secret, service/API tổ chức,
policy catalog/select/chat và UI tích hợp. Đã nhận commit Claude `da84c59` bằng
cherry-pick --no-commit; đã sửa controlled inputs, accessible names và mobile rows.
Chưa nghiệm thu toàn feature. Full backend suite sau cutover: 355 test, 347 pass, 1 fail, 7 skip.
Frontend unit đạt 108/108 (không skip), build/lint/format đạt; browser component
23 checks và browser luồng tổ chức 7 checks đạt; auth browser 64 checks đạt.
Đã được duyệt cập nhật thêm browser regression. Theme đạt 9 checks, admin đạt
34 groups, frontend UX đạt 42 checks. Real browser E2E hai tài khoản đạt 1/1 test.
Workspace còn fail trong `workspace-a11y-browser.mjs`; LLM/i18n browser còn các
assertions personal cần port tiếp. Không coi phần regression này đã hoàn tất. Giữ nguyên bốn tệp user đã từ chối sửa: `tests/test_f004_001_chat_contract.py`,
`tests/test_f004_002_model_adapters.py`, `tests/test_llm_proxy.py`, `backend/ruvie/database.py`.
Không chạy migration trên application DB. Chưa tạo commit cho thay đổi lead.

## Goal

Admin cấu hình một kết nối OpenAI-compatible dùng chung cho Ruvie Agent.
Admin cấp danh sách model và chọn một model mặc định. Nhân viên chỉ chọn model
được cấp. Nhân viên không nhập hoặc thay provider/API key qua UI hoặc API trực tiếp.

Một deployment đại diện cho một tổ chức. PostgreSQL là nguồn dữ liệu chính.
Không dùng cấu hình cá nhân hoặc môi trường để vượt qua chính sách tổ chức.

### Hiện trạng và khoảng cách

| Nguồn đã kiểm tra | Code hiện tại | Spec yêu cầu |
| --- | --- | --- |
| `backend/ruvie/services/llm.py::LlmConnectionService._resolve` | Ưu tiên URL/key cá nhân, sau đó `settings.llm` | Chỉ resolve cấu hình tổ chức trong DB |
| `save_connection` | Kiểm tra catalog trước khi lưu kết nối cá nhân | Admin kiểm tra draft và áp dụng cấu hình chung nguyên tử |
| `list_models`, `select_model`, `resolve_chat_adapter` | Kiểm tra catalog provider mới; chưa có allowlist tổ chức | Cùng dùng một chính sách model được cấp |
| `backend/ruvie/api/llm.py::require_write_access` | Kiểm tra đăng nhập, Origin, CSRF; không yêu cầu admin | Mọi sửa cấu hình chung phải yêu cầu admin hiện tại |
| `backend/ruvie/models/llm.py::UserLlmSettings` | Lưu URL, API key dạng Text, catalog và lựa chọn theo user | Tách cấu hình chung, key mã hóa và lựa chọn cá nhân |
| `backend/migrations/versions/0008_user_llm_settings.py` | Tạo bảng cấu hình cá nhân | Giữ migration đã áp dụng; thêm migration mới |
| `backend/ruvie/services/chat.py::ChatService.prepare` | Resolve model trước embedding/retrieval; trả `PreparedChat` giữ adapter riêng | Giữ thứ tự này; kiểm tra allowlist và snapshot cấu hình |
| `frontend/src/lib/features/llm/llm-state.svelte.ts::createLlmState` | Giữ catalog, lựa chọn và draft kết nối trong cùng owner | Tách owner admin khỏi catalog/lựa chọn của workspace |
| `frontend/src/lib/pages/WorkspacePage.svelte`, `features/settings/SettingsPanel.svelte` | Form LLM ở Admin > System settings; persistence vẫn theo user | Giữ vị trí UI; thay contract và owner phía dưới |

`specs/01-product-spec.md` là định hướng sản phẩm rộng. Không dùng nội dung cũ
trong tài liệu đó để suy ra trạng thái triển khai. `specs/02-architecture.md`
mô tả luồng cá nhân hiện tại. `specs/to-be/admin-roadmap.md` yêu cầu LLM tập trung.
Không có F016 trong nguồn không thuộc `archive` tại thời điểm kiểm tra.

### Nguồn tái sử dụng

| Nguồn | Hành vi tái sử dụng | Thích nghi |
| --- | --- | --- |
| Active `adapters/llm.py::normalize_llm_url`, `PinnedLlmTransport`, `OpenAICompatibleLlmAdapter` | Chuẩn hóa catalog, timeout, SSRF, DNS pinning, TLS, redirect và proxy server | Gọi từ cấu hình tổ chức; không thay transport bằng legacy |
| Active `api/llm.py::LlmRoute`, `contracts/llm.py` | Che input validation, `SecretStr`, metadata không chứa key | Mở rộng lỗi an toàn, contract admin và no-store |
| Active `dependencies.py::get_admin_user_id`, `services/admin.py::AdminAccountService.require_admin` | Identity tin cậy và đọc lại quyền admin | Kiểm tra trước probe và kiểm tra lại actor trong transaction ghi |
| Active `services/audit.py::AuditEventWriter.append` | Ghi audit trong transaction caller | Ghi sự kiện cấu hình chung không có secret |
| Active `ChatService.prepare`, `PreparedChat`, `AuthorizedRetrievalService` | Snapshot adapter và context đã kiểm tra quyền | Giữ ACL tài liệu; thay resolver LLM |
| `references/backend/ruvie/routers/openai.py::get_openai_runtime_config` | Đọc cấu hình dùng chung từ persistence | Singleton PostgreSQL, không nhiều URL/key |
| Legacy `openai.py::update_config` | Admin cập nhật cấu hình và sự kiện thay đổi | Verify trước commit, version conflict, audit nguyên tử; tuyệt đối không trả `OPENAI_API_KEYS` |
| Legacy `openai.py::verify_connection` | Thử kết nối bằng draft trước áp dụng | Dùng adapter active; không port `trust_env=True`, cookie forwarding hoặc lỗi provider thô |
| Legacy `get_all_models_responses`, `get_all_models` | Chuẩn hóa danh sách model | Một kết nối; không tạo model giả từ ID cấu hình; không suy luận khả năng chat bằng tên |
| Legacy `get_filtered_models` | Lọc model trước response | Allowlist tổ chức; không group ACL hoặc admin bypass |
| `references/backend/ruvie/routers/models.py::get_models`, `toggle_model_by_id`, `update_model_access_by_id` | Xem danh sách và quản lý model được cấp | Lưu trạng thái mong muốn nguyên tử; không quyền ghi của owner, group hoặc thao tác toggle |
| `references/src/lib/components/admin/Settings/Connections.svelte` | Khu vực cấu hình, pending và refresh | Svelte 5, cookie/CSRF, key write-only, lỗi dịch an toàn |
| `references/src/lib/components/admin/Settings/Models.svelte` | Danh sách, tìm kiếm, bật/tắt model | Callback chỉnh draft; không thông báo thành công trước commit |
| `references/src/lib/components/admin/Settings/Models/ModelSettingsModal.svelte` | Chọn model mặc định | Một mặc định thuộc allowlist; không pinned models/capabilities |

Ưu tiên active code. Không import hoặc chạy runtime legacy. Không port auth,
localStorage token, SQLite, raw provider errors hoặc admin bypass quyền tài liệu.
Không đọc hoặc sử dụng nội dung bất kỳ thư mục tên `archive` nào.

## User Story

- Là admin, tôi muốn cấu hình provider và key một lần để nhân viên dùng chung.
- Là admin, tôi muốn kiểm tra kết nối và chọn model được cấp trước khi áp dụng.
- Là nhân viên, tôi muốn chọn model được cấp và giữ lựa chọn sau khi đăng nhập lại.
- Là admin, tôi muốn được báo conflict khi người khác đã sửa cấu hình.
- Là người dùng, tôi muốn nhận thông báo an toàn khi model hoặc dịch vụ không còn khả dụng.

## Scope

### In

- Một kết nối OpenAI-compatible và nhiều model trong kết nối đó.
- Cấu hình chung trong PostgreSQL; migration Alembic mới.
- API key write-only với trình duyệt, kể cả admin; mã hóa trong DB.
- Admin verify draft rồi áp dụng URL/key/allowlist/default bằng một transaction ghi.
- Nhân viên chỉ lưu lựa chọn model của chính mình.
- Catalog, chọn model và chat dùng chung chính sách phía server.
- Đóng API ghi cấu hình cá nhân; bỏ fallback cá nhân và `LLM_*` cho catalog/chat.
- Chống ghi đè bằng version; ngăn response cũ cập nhật UI mới.
- Giao diện admin hiện có, theme sáng/tối, vi-VN/en-US/ru-RU, pending và lỗi an toàn.
- Audit thay đổi cấu hình; kiểm thử migration, authorization, concurrency, secret và browser.

### Out

- Nhiều provider, tenant, cân bằng tải, quota/billing, group model ACL.
- Custom model, marketplace, pinned models, import/export catalog.
- Proxy UI, secret viewer, audit viewer, secret manager bên ngoài hoặc rotation UI.
- API xóa kết nối chung trong bản đầu.
- Thay embedding profile, vector dimension, ingestion hoặc quyền đọc tài liệu.
- Hủy stream đã resolve khi cấu hình thay đổi; push/WebSocket đồng bộ cấu hình.

## Flow

### 1. Hợp đồng dữ liệu

Tên bảng mới đề xuất: `organization_llm_settings`. Tạo sẵn một hàng singleton
`id=1`; `version=0` biểu thị chưa cấu hình. Khóa chính và CHECK ngăn hàng có ID khác.

| Trường | Ý nghĩa/ràng buộc |
| --- | --- |
| `id` | Số nguyên; chỉ bằng 1 |
| `version` | Số nguyên không âm; mỗi lần apply thành công tăng đúng 1 |
| `base_url` | NULL khi chưa cấu hình; URL chuẩn hóa khi active |
| `api_key_ciphertext` | NULL nếu không dùng key; không phải field public |
| `allowed_model_ids` | JSON array các ID duy nhất; rỗng chỉ khi version=0 |
| `default_model_id` | NULL khi version=0; phải thuộc allowlist khi active |
| `updated_by` | FK user, có thể NULL khi chưa cấu hình; không xóa cấu hình nếu user bị xóa |
| `created_at`, `updated_at` | Thời gian server có timezone |

DB CHECK bảo vệ singleton, version và tính nhất quán trạng thái chưa cấu hình/active.
Kiểm tra array, ID duy nhất và membership mặc định tại contract/service; thêm CHECK
PostgreSQL phù hợp nếu không làm migration khó đọc. Không dùng client state làm nguồn quyền.
Không lưu catalog provider làm bằng chứng model hiện còn khả dụng.

Giữ tên bảng/class `UserLlmSettings`, `user_llm_settings` để giảm thay đổi caller.
Sau migration, bảng này chỉ giữ `user_id`, `selected_model_id`, timestamps.
Giữ FK user và cascade hiện tại. Bỏ `base_url`, `api_key`, `models` và constraint
key-requires-URL. `selected_model_id` là preference, không phải cấp quyền.

### 2. Migration và cutover

1. Thông báo thời điểm ngừng API cũ; sao lưu DB theo quy trình vận hành đã duyệt.
2. Dừng backend cũ trước khi migration/code mới cùng có hiệu lực. Không chạy rolling
   deployment với backend cũ còn đường ghi cá nhân.
3. Migration mới nối Alembic head thực tế; hiện head nguồn là `0011_user_presence`.
4. Tạo singleton chưa cấu hình; không chọn một admin làm nguồn và không seed từ môi trường.
5. Giữ nguyên selected ID cũ như preference chờ kiểm tra; xóa các cột URL/key/catalog cá nhân.
6. Khởi động backend mới. Catalog/chat không dùng `settings.llm` hoặc dữ liệu cá nhân cũ.
7. Admin cấu hình lại qua UI mới; lựa chọn cũ chỉ hợp lệ nếu ID thuộc chính sách hiện tại.

Downgrade có thể dựng lại cột cũ rỗng, nhưng không phục hồi URL/key/catalog đã bỏ.
Không tự đưa dữ liệu tổ chức vào từng user. Backup có thể còn plaintext key cũ;
không tuyên bố migration xóa secret khỏi backup/WAL. Không log dữ liệu bị loại.
Chỉ dùng disposable DB cho test, không reset application DB.

`LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` không còn là runtime fallback sau F016.
Cập nhật loader/config, README và `.env.example` để cấu hình môi trường cũ không
âm thầm khôi phục luồng đó hoặc chặn startup chỉ vì bộ fallback cũ không đầy đủ.
Giữ `LLM_ALLOWED_LOCAL_ORIGINS` và `LLM_PROXY_URL` phía server. Factory/caller cũ
cũng phải được kiểm tra để không tồn tại đường chat bypass policy.

### 3. Lưu và xử lý secret

Đề xuất module nhỏ `backend/ruvie/services/llm_secrets.py` dùng Fernet của thư viện
`cryptography`. Không tự viết cipher. Server cung cấp `LLM_SETTINGS_ENCRYPTION_KEY`
ngoài PostgreSQL/Git. Ciphertext có prefix định dạng `v1:` để nhận diện phiên bản.

- Chỉ mã hóa key không rỗng; không key lưu NULL.
- Server thiếu key mã hóa vẫn có thể đọc cấu hình không dùng API key. Thao tác cần
  mã hóa/giải mã phải thất bại an toàn nếu thiếu/sai key; không plaintext fallback.
- Kiểm tra cú pháp key server lúc startup nếu được cung cấp. Không in giá trị key.
- Không có key hoặc ciphertext trong response, validation, log, audit, repr công khai
  hoặc browser storage. `SecretStr` không thay thế mã hóa tại rest.
- SQL error handling không ghi bound parameters chứa secret. Không log body/header
  credential hoặc raw provider exception; audit dùng allowlist metadata.
- Browser chỉ giữ draft key trong bộ nhớ. Xóa draft khi rời form, logout, mất quyền,
  apply thành công hoặc request lỗi. Verify thành công được giữ key trong bộ nhớ
  để apply cùng draft; không tự ghi vào storage.
- Vận hành sao lưu key mã hóa riêng với DB. Mất key khiến ciphertext không giải mã được.
- Đổi key mã hóa cần maintenance: đọc bằng key cũ, mã hóa lại bằng key mới trong
  transaction, chuyển server key đồng bộ; không chỉ thay env rồi kỳ vọng đọc được.
  F016 không cung cấp tự động rotation hoặc UI cho bước này.

### 4. Hợp đồng API

Các request là strict: cấm field thừa, loại/range sai và giá trị không hợp lệ.
URL tối đa 2048 ký tự; API key tối đa 4096; model ID tối đa 4096, không rỗng.
Chuẩn hóa URL bằng adapter active. Model ID phân biệt hoa thường; không đổi tên ID.
`expected_version` là integer không âm, không nhận boolean.

Draft kết nối dùng union rõ ràng:

```json
{"base_url":"https://provider.example/v1","key_action":"keep","expected_version":2}
```

- `keep`: cấm `api_key`; chỉ hợp lệ khi đã cấu hình và URL chuẩn hóa không đổi.
  Có thể giữ trạng thái không key của kết nối hiện tại.
- `replace`: bắt buộc `api_key` không rỗng sau trim.
- `clear`: cấm `api_key`; kết nối không dùng key. Không có nghĩa xóa kết nối chung.
- URL mới buộc `replace` hoặc `clear`; không gửi key cũ sang URL khác.

| Method/path | Identity và input | Output/hành vi |
| --- | --- | --- |
| `GET /admin/llm/connection` | Admin hiện tại | Metadata DB, không probe: `configured`, `base_url`, `has_api_key`, `allowed_model_ids`, `default_model_id`, `version`, `updated_at`; trạng thái trống trả version 0 |
| `POST /admin/llm/connection/verify` | Admin, Origin, CSRF; draft trên | `models: [{id,name}]`, `version` tương ứng snapshot; không ghi DB/audit apply; không trả URL/key từ provider |
| `PUT /admin/llm/connection` | Admin, Origin, CSRF; draft + `allowed_model_ids`, `default_model_id` | Verify lại; commit nguyên tử; trả metadata chung cùng version mới, không trả key |
| `GET /models` | User đã đăng nhập | Catalog đã lọc, `selected_model_id`, `selection_required`, `configuration_version` |
| `PATCH /llm/connection/model` | User, Origin, CSRF; `{model_id}` | Kiểm tra policy mới, lưu preference chính user; trả `selected_model_id`, `configuration_version` |
| `GET /llm/connection` | User đã đăng nhập | Chỉ `configured`, `selected_model_id` đã kiểm tra allowlist DB, `configuration_version`; không URL/key metadata; không probe, không khẳng định provider đang khả dụng |
| `PUT /llm/connection` cũ | User/admin đã đăng nhập | User: 403 `admin_required`; admin: 410 `personal_llm_configuration_removed`; không provider call hoặc ghi DB |
| `DELETE /llm/connection` cũ | Như PUT cũ | Cùng lỗi và không side effect; không redirect sang sửa cấu hình chung |
| `POST /chat` | Contract message/model hiện có | Giữ SSE; kiểm tra policy chung trước embedding/retrieval |

Ví dụ catalog nhân viên:

```json
{
  "models":[{"id":"chat-a","name":"Chat A"}],
  "selected_model_id":"chat-a",
  "selection_required":false,
  "configuration_version":3
}
```

PUT chỉ nhận allowlist không rỗng, ID duy nhất, mọi ID có trong catalog probe mới,
default thuộc allowlist. Không tin catalog hoặc verify response do browser gửi lại.
Verify thành công không cung cấp token cho phép bỏ probe tại apply.
Verify chỉ chứng minh `/models` trả catalog dùng được; không chứng minh chat/quota.

Không serialize danh sách model chưa cấp hoặc provider URL/key cho nhân viên.
Admin chỉ có quyền catalog đầy đủ qua endpoint verify, không được bypass policy chat.
Mọi response cấu hình/catalog/preference và lỗi tương ứng dùng `Cache-Control: no-store`.

| HTTP/code | Điều kiện và xử lý UI |
| --- | --- |
| 401 `authentication_required` | Session không còn hợp lệ; dispose workspace |
| 403 `admin_required` | Mất quyền admin; rời admin, xóa secret draft; không tự logout |
| 403 `origin_invalid` / `csrf_invalid` | Từ chối request; không suy ra mất role |
| 409 `configuration_conflict` | Version đã đổi; không ghi; yêu cầu reload và kiểm tra lại |
| 410 `personal_llm_configuration_removed` | Client admin gọi mutation cá nhân cũ |
| 422 `invalid_llm_request` | Shape, URL, key action, allowlist/default sai; không echo input |
| 422 `model_not_allowed` / `model_selection_required` | Chặn lựa chọn/chat; reload catalog và cho chọn lại |
| 502 `llm_provider_unavailable` | Probe lỗi, timeout, payload rỗng/sai; không trả upstream body |
| 503 `llm_not_configured` | Chưa có cấu hình tổ chức; admin cần cấu hình |
| 503 `llm_settings_unavailable` | Storage/secret không khả dụng; không fallback |

Lỗi HTTP dùng `detail: {code}` và field codes allowlist nếu cần; không chứa dữ liệu
validation, SQL, URL upstream, credential hoặc nội dung provider. Với chat, lỗi
model trả HTTP 422 trước SSE; lỗi cấu hình/provider/secret/storage được chuyển
thành SSE `provider_unavailable` an toàn theo contract chat hiện có. Lỗi sau khi
bắt đầu stream giữ `provider_unavailable`/`generation_failed`; không phát citations
hoặc completed như thành công sau lỗi.

### 5. Chính sách model và luồng nhân viên

Hàm policy chung đề xuất trong `services/llm.py` nhận snapshot tổ chức, preference,
catalog mới và optional model ID của request. Trả model hiệu lực hoặc lỗi có kiểu.

1. Đọc singleton DB và preference của identity tin cậy.
2. Nếu chưa cấu hình: dừng; không gọi provider, embedding hoặc retrieval.
3. Tạo adapter từ snapshot URL/key với network settings server hiện có.
4. Lấy catalog mới; tập sử dụng được là `allowed IDs ∩ current catalog IDs`.
5. `GET /models` chỉ trả tập này. Không ghi preference hoặc catalog xuống DB.
6. Nếu request có model ID rõ ràng, kiểm tra ID trong tập; không tự lưu preference.
7. Nếu không có ID rõ ràng: dùng preference nếu hợp lệ. Preference không hợp lệ
   yêu cầu chọn lại; không tự đổi sang mặc định.
8. Chưa từng chọn hoặc preference NULL: dùng default nếu thuộc tập. Không chọn
   model đầu tiên nếu default mất. Không có model hiệu lực thì selection_required=true.
9. PATCH kiểm tra cùng tập và chỉ lưu preference của chính actor.
10. Chat dùng adapter copy đã resolve; chỉ sau đó mới embedding và authorized retrieval.

Catalog có thể trả mảng rỗng sau giao với allowlist, với selected=null và
selection_required=true. Provider trả catalog rỗng là lỗi probe theo adapter active.
GET metadata chỉ bỏ preference ngoài allowlist DB; khả dụng thực tế do GET models
và chat xác định. Frontend không dùng metadata riêng để bật nút gửi chat.

### 6. Luồng admin, transaction và concurrency

1. Kiểm tra session/admin trước mọi read/probe. Mutation còn kiểm tra Origin/CSRF.
2. Đọc snapshot/version; từ chối version sai trước khi gửi credential ra provider.
3. Resolve key action trên snapshot, normalize URL rồi probe bằng adapter active.
   Không giữ transaction ghi/row lock qua network call.
4. Kiểm tra allowlist/default bằng catalog probe khi apply.
5. Bắt đầu transaction ghi mới. Đọc lại và khóa actor bằng cơ chế admin hiện có;
   xác nhận active và role. Giữ thứ tự actor trước singleton khi cần khóa cả hai.
6. Cập nhật singleton có điều kiện `version=expected_version`; tăng version.
   Không có hàng khớp thì rollback và trả 409. Singleton version 0 đã có từ migration
   nên hai admin cấu hình lần đầu cũng dùng cùng cơ chế.
7. Ghi `llm.organization_settings.update` trong cùng transaction. Metadata chỉ có
   old/new version, số model được cấp và loại thao tác key, không có key/ciphertext.
8. Commit; trả metadata/version mới. Audit hoặc DB lỗi rollback toàn bộ.

Verify không ghi cấu hình. Nếu quyền/version thay đổi trong probe verify, kiểm tra
lại trước khi trả thành công; kết quả probe cũ không được dùng cho apply mới.
Không tự retry PUT/PATCH hoặc ghi lại bằng version mới sau conflict.

Policy cho một catalog/select/chat request có hiệu lực theo snapshot DB khi resolve.
Update commit sau thời điểm đó không hủy request đang xử lý. Chat đã resolve giữ
URL/key/model cũ kể cả chưa phát delta đầu tiên. Request resolve sau commit dùng
version mới. PATCH đang xử lý có thể lưu preference vừa bị thu hồi; request kế tiếp
vẫn phải kiểm tra policy mới, nên preference đó không cấp quyền.

### 7. UI states và vòng đời

Giữ System settings và shell hiện có. Owner admin đề xuất
`frontend/src/lib/features/llm/organization-llm-state.svelte.ts`; API client admin
đề xuất `organization-llm-api.ts`. Không đưa nghiệp vụ vào WorkspacePage.

| State | Hiển thị và hành vi |
| --- | --- |
| Loading metadata | Pending, khóa thao tác apply; không dùng draft phiên trước |
| Unconfigured | Admin thấy hướng dẫn kết nối; nhân viên thấy liên hệ admin |
| Editing/unverified | URL, key action, key mới; apply bị khóa cho đến khi verify |
| Verifying | Khóa mutation; hiển thị pending; không dùng response từ draft cũ |
| Verified | Catalog đầy đủ để chọn allowlist/default; nhãn rõ chưa áp dụng |
| Applying | Khóa thao tác lặp; không hiển thị thành công trước response |
| Applied | Metadata/version mới; xóa key draft; refresh catalog workspace |
| Validation/provider error | Giữ cấu hình đã lưu; hiển thị lỗi dịch an toàn, xóa key draft và bỏ trạng thái verified |
| Conflict | Bỏ verified, không tự ghi đè; reload thủ công, nhập lại key nếu cần |
| Unknown mutation result | Mất response sau khi gửi: không khẳng định lưu thất bại; xóa key draft, đọc lại metadata/version, không tự retry hoặc nhận công thay đổi của admin khác |
| Role/session loss | Xóa key/draft/request generation; xử lý admin_required khác Origin/CSRF 403 |

Sửa URL/key hoặc expected version làm mất verified catalog và khóa apply.
Chỉnh allowlist/default trên catalog đã verify không cần probe UI riêng; apply
vẫn probe lại phía server. Khi đổi URL, không giữ key cũ trong draft.
Rời System settings phải gọi lifecycle cleanup dù panel chỉ bị hidden; không chỉ
dựa vào unmount. Logout, user change, role loss và dispose vô hiệu hóa response cũ.
Abort browser không có nghĩa hủy transaction server.

Owner dùng request generation và configuration version. Response generation cũ
hoặc version thấp hơn trạng thái đã xác nhận không cập nhật UI. Khi apply thành công,
refresh catalog không ghi đè draft mới hoặc selection request mới.
Không thêm polling hoặc push. Tab khác nhận chính sách mới khi reload/select/chat.

Model selector nhân viên không có provider/key controls. Selection required hoặc
catalog lỗi khóa gửi chat mới. Người dùng có thể chọn model hợp lệ khác khi default
mất; explicit ID hợp lệ cho một chat không thay preference. Theme/locale không xóa
draft hợp lệ hoặc hủy stream đang chạy.

### 8. Contract component giao Claude

Component mới: `OrganizationModelPolicyEditor.svelte`. Component chỉ chỉnh draft,
không gọi API, không chứa URL/key, không verify/apply và không import owner/types API.
Contract do lead sở hữu; không tạo shared type module ở nhánh Claude.

```typescript
type Props = {
  id: string;
  models: readonly { id: string; name: string; available: boolean }[];
  allowedModelIds: readonly string[];
  defaultModelId: string | null;
  disabled: boolean;
  error: string | null;
  labels: {
    heading: string;
    search: string;
    allow: string;
    defaultModel: string;
    unavailable: string;
    empty: string;
    noMatches: string;
    help: string;
  };
  onchange: (next: {
    allowedModelIds: string[];
    defaultModelId: string | null;
  }) => void;
};
```

- Parent truyền hợp catalog và ID đã cấu hình; mỗi ID duy nhất. ID mất có row
  unavailable, tên có thể là ID. Labels/error đã dịch và chỉ render dạng text.
- Props là nguồn chính; chỉ search là state nội bộ. Không mutate arrays hoặc phát
  callback khi mount/props update. Callback trả draft mới, không ID trùng.
- Checkbox cấp model; radio mặc định chỉ bật khi model available và đã được cấp.
- Bỏ cấp default phát default=null; không tự chọn model đầu tiên.
- Unavailable đã cấp vẫn cho bỏ cấp; không cho cấp mới hoặc chọn default.
- Search theo ID/name không phân biệt hoa thường, giữ thứ tự đầu vào và lựa chọn ẩn.
- `disabled` khóa control và callback. Mảng models rỗng khác search không khớp.
- Native controls, label đúng, ID và radio group có prefix `id`; hai instance độc lập.
- Token CSS hiện có, scoped styles, focus-visible, không tràn ngang ở 360px;
  hiển thị long IDs và ba locale trong theme sáng/tối.

## Edge Cases

| Trường hợp | Kết quả bắt buộc |
| --- | --- |
| Chưa cấu hình tổ chức | Catalog/chat dừng an toàn; không dùng URL/key cũ hoặc env |
| Allowlist rỗng, trùng ID hoặc default ngoài allowlist | Reject apply; cấu hình/version không đổi |
| Model provider mới xuất hiện | Không tự cấp; admin phải thêm vào allowlist |
| Model bị gỡ/đổi ID | Loại khỏi tập khả dụng; preference mất hiệu lực yêu cầu chọn lại |
| Chỉ đổi name, giữ ID | Giữ lựa chọn; lấy name mới từ catalog |
| Default mất, preference khác còn hợp lệ | User có preference hợp lệ vẫn dùng được; user chưa chọn phải chọn model khác |
| Không còn model được cấp khả dụng | Catalog trả rỗng; chat không embedding/retrieval; không chọn model ngoài allowlist |
| Verify thành công nhưng model không chat được | Báo lỗi chat an toàn; không chuyển provider/model hoặc tự retry |
| Probe timeout, TLS/DNS/proxy lỗi, redirect hoặc catalog sai | Không ghi DB; không fallback direct hoặc env; không lộ upstream data |
| Clear key nhưng provider yêu cầu key | Probe thất bại; key/cấu hình đang active được giữ |
| URL thay đổi với keep | Reject trước provider call; key cũ không rời đến URL mới |
| Key mã hóa thiếu/sai/ciphertext hỏng | Lỗi an toàn; không coi là kết nối không key |
| DB/audit commit thất bại | Rollback cấu hình/version/audit; không hiện thành công |
| Hai admin hoặc initial apply đồng thời | Chỉ một request cùng expected version thành công; request kia 409 |
| Admin bị hạ role/khóa trong probe | Recheck trước apply; không ghi cấu hình |
| Response cũ, đổi tab, logout hoặc session thay đổi | Không cập nhật state mới hoặc khôi phục key draft |
| Mất response PUT | Kết quả chưa xác định; đọc lại metadata, không tự gửi lại |
| Stream đã resolve trước apply | Tiếp tục snapshot cũ; không đổi credential giữa stream |
| Admin đọc tài liệu không được cấp | Retrieval/citations vẫn default-deny; role admin không bypass |

## Acceptance Criteria

- [ ] AC01: Migration tạo đúng một singleton version 0, giữ preference và loại URL/key/catalog cá nhân; không sửa migration cũ hoặc seed từ admin/env.
- [ ] AC02: Mọi API read/probe/apply admin từ chối user thường; apply recheck actor trong transaction. Origin/CSRF thiếu/sai không gây mutation/probe trái phép.
- [ ] AC03: PUT/DELETE cá nhân cũ không ghi DB hoặc gọi provider; user nhận 403, admin nhận 410; PATCH lựa chọn vẫn chỉ tác động chính user.
- [ ] AC04: Verify không ghi DB; apply tự probe lại cùng payload; key actions và URL change tuân thủ contract.
- [ ] AC05: Allowlist không rỗng, ID duy nhất và thuộc catalog mới; default thuộc allowlist; sai input giữ cấu hình/version cũ.
- [ ] AC06: Catalog/select/chat dùng cùng policy; gửi model ID trực tiếp không vượt allowlist, kể cả admin.
- [ ] AC07: Preference hợp lệ giữ qua reload/login; preference mất yêu cầu chọn lại; chưa chọn dùng default; không chọn model đầu tiên tự động.
- [ ] AC08: Chưa cấu hình không fallback cá nhân/env; model/provider lỗi không fallback, embedding/retrieval không chạy khi model resolution thất bại.
- [ ] AC09: Key mới mã hóa tại rest; không key/ciphertext trong browser response, validation, error, log, audit hoặc storage; thiếu/sai key mã hóa không plaintext fallback.
- [ ] AC10: Provider/DB/audit lỗi không thay cấu hình active; response an toàn, no-store; mutation không tự retry.
- [ ] AC11: Hai apply cùng version chỉ một thành công; version/audit nguyên tử; response cũ không ghi đè UI.
- [ ] AC12: Request đã resolve giữ snapshot; request resolve sau commit dùng version mới; ACL tài liệu/citations không đổi.
- [ ] AC13: UI admin/nhân viên đúng quyền, pending/error/conflict/unknown-result; xóa key draft khi rời form/lỗi/logout/mất quyền.
- [ ] AC14: Component Claude giữ nguyên contract, có keyboard/disabled/unavailable/search đúng; ba locale, hai theme và 360px không tràn ngang.
- [ ] AC15: Required backend/frontend/browser checks được chạy và báo pass/fail/skip thực tế; skip không được tính là nghiệm thu pass.

### Ma trận test

| Nhóm | Ca kiểm tra chính | Mức kiểm tra / AC |
| --- | --- | --- |
| Migration | SQL upgrade/downgrade, seeded singleton, FK/constraints, dữ liệu cá nhân cũ, không phục hồi secret giả | PostgreSQL disposable + generated SQL; AC01 |
| Secret | Roundtrip, ciphertext khác plaintext, NULL key, thiếu/sai key, corrupt token, lỗi SQL/log/audit redaction | Unit + API/DB; AC09 |
| HTTP security | Anonymous, user/admin, role revoked, inactive, Origin/CSRF, extra fields, no-store | API integration; AC02–04 |
| Personal API cutover | PUT/DELETE 403/410, no provider/write, metadata thu hẹp, env/personal không fallback | API + service; AC03/08 |
| Admin apply | keep/replace/clear, URL change, empty/duplicate/default/model invalid, verify không ghi, apply re-probe | Unit + fake provider + DB; AC04/05 |
| Runtime policy | Catalog intersection, direct explicit ID, stale preference/default, no first-model fallback, no embedding khi reject | Service/chat integration; AC06–08 |
| Failure/transaction | Timeout/empty/malformed catalog, storage/audit rollback, uncertain response | Fake provider + DB + browser; AC10 |
| Concurrency | Two initial/existing applies, quyền thay đổi giữa probe/commit, version tăng một lần | PostgreSQL nhiều connection có barrier; AC02/11 |
| Transport regression | SSRF/local allowlist, redirect, mixed/rebound DNS, TLS pin, explicit proxy failure | Test adapter/proxy hiện có; AC08/09 |
| Stream/ACL | Snapshot URL/key/model, config đổi khi prepare/stream, user không đọc được tài liệu khác, admin không bypass | Chat/retrieval integration; AC12 |
| Component | SSR labels/state/IDs; browser callbacks, props update, keyboard, disabled/unavailable, long IDs | Node + harness Claude; AC14 |
| App lifecycle | Verify/edit/apply, conflict, late response, unknown result, 401/403 phân biệt, hidden/unmount cleanup | Frontend state + browser/E2E; AC11/13 |
| Locale/theme | vi-VN/en-US/ru-RU, light/dark, 360px, error/status labels | Browser; AC13/14 |

## Tasks

### Phân công và quy tắc tích hợp

Lead sở hữu kiến trúc, schema, shared types, API contracts, secret, business logic,
state owner, locale và tích hợp. Claude Opus 4.4 trong Antigravity làm một worktree
riêng từ `96d1bb0`, chỉ làm F016-007. Không cần interface code mới được commit trước;
component dùng contract props cố định ở Flow 8 và harness riêng.

Không có tệp đồng sở hữu trong thời gian chạy song song. Lead không sửa bốn tệp
Claude trước bàn giao. Claude không sửa app integration, shared types hoặc spec.
Nếu contract cần đổi, báo lead; hai bên dừng phần phụ thuộc đến khi thống nhất.
Claude bàn giao commit hash và test output; lead review, tích hợp rồi chạy regression.
Không merge/rebase nhánh của bên kia trong lúc đang làm.

Các đường dẫn tương đối sau tính từ repository root. Tệp mới được ghi rõ là mới.
Đây là kế hoạch triển khai; trước sửa code phải báo phạm vi theo AGENTS.md và giữ
công việc chưa commit. Không tự mở rộng whitelist worker.

- [ ] **F016-001 — Schema và migration** — Lead
  - **Where:** `backend/ruvie/models/llm.py`, `models/__init__.py`; migration mới `backend/migrations/versions/0012_organization_llm_settings.py` nếu head chưa đổi; test mới `tests/test_f016_001_llm_schema.py`.
  - **Work:** Viết test migration/schema trước. Tạo singleton version 0. Thu hẹp UserLlmSettings, giữ preference và timestamps. Xóa cột cá nhân và constraint cũ. Kiểm tra upgrade/downgrade SQL và DB thực. Không phục hồi secret từ tổ chức trong downgrade.
  - **Done:** AC01; singleton/constraints và chuyển dữ liệu được xác minh bằng disposable PostgreSQL. Head thay đổi thì chọn tên/revision mới, không sửa migration đã áp dụng.

- [ ] **F016-002 — Secret và cấu hình server** — Lead
  - **Where:** Mới `backend/ruvie/services/llm_secrets.py`, `tests/test_f016_002_llm_secrets.py`; `backend/ruvie/config.py`, `backend/requirements.txt`, `.env.example`.
  - **Work:** Test rồi thêm cryptography/Fernet, prefix v1, key server, lỗi an toàn và NULL key. Loại runtime env fallback; giữ local-origin/proxy settings. Không log secret hoặc plaintext fallback.
  - **Done:** AC08/09; thiếu/sai key và ciphertext hỏng được kiểm tra; config không đổi embedding/proxy contract.

- [ ] **F016-003 — Contracts và service quản trị** — Lead; sau 001–002
  - **Where:** `backend/ruvie/contracts/llm.py`, `services/llm.py`; dùng `services/admin.py`, `services/audit.py`; mới `tests/test_f016_003_admin_llm.py`.
  - **Work:** Strict draft/key-action contracts; metadata/verify/apply results. Probe ngoài transaction ghi. Recheck actor, CAS version, audit cùng commit. Rollback và typed safe errors. Test hai connection, initial apply, role change, provider/DB/audit failures.
  - **Done:** AC02/04/05/09–11; một apply thắng mỗi expected version và không giữ row lock qua network probe.

- [ ] **F016-004 — HTTP boundary và đóng API cũ** — Lead; sau 003
  - **Where:** `backend/ruvie/api/llm.py`, `backend/ruvie/main.py` nếu cần router registration; mới `tests/test_f016_004_llm_api.py`.
  - **Work:** API admin read/verify/apply, Origin/CSRF, redaction/no-store. Thu hẹp GET cá nhân và đóng PUT/DELETE 403/410. Giữ PATCH preference. Không port raw AdminRoute validation nếu có thể echo key.
  - **Done:** AC02–04/09/10; API trực tiếp của user không gọi provider hoặc sửa cấu hình; lỗi JSON không chứa submitted secret.

- [ ] **F016-005 — Policy catalog/select/chat** — Lead; sau 001–003
  - **Where:** `backend/ruvie/services/llm.py`, `services/chat.py`, `api/chat.py`, `adapters/llm.py` chỉ khi cần bỏ factory bypass; mới `tests/test_f016_005_chat_policy.py`.
  - **Work:** Một resolver/policy chung với fresh catalog, allowlist và preference/default rules. Giữ request adapter snapshot. Map safe failures sang HTTP/SSE. Kiểm tra mọi caller/factory để không còn personal/env bypass.
  - **Done:** AC06–08/12; invalid ID dừng trước embedding/retrieval; stream giữ snapshot; tài liệu/citations vẫn đúng quyền.

- [x] **F016-006 — Frontend API và state owner** — Lead; contracts 003 ổn định
  - **Where:** Mới `frontend/src/lib/features/llm/organization-llm-api.ts`, `organization-llm-state.svelte.ts`, `frontend/tests/f016-organization-llm-api.test.mjs`, `f016-organization-llm-state.test.mjs`; `llm-api.ts`, `llm-state.svelte.ts` hiện có.
  - **Work:** Tách admin draft/verify/apply khỏi workspace catalog/preference. Key action, generation/version, conflict, unknown result, role/session loss và active/hidden cleanup. Bỏ client API mutation cá nhân. Không retry mutation.
  - **Done:** AC10/11/13; test response cũ và lifecycle không phục hồi secret, version hoặc draft cũ. Có thể chạy song song backend sau khi contracts cố định.

- [x] **F016-007 — Component model policy độc lập** — Claude; chạy song song 001–006
  - **Where — whitelist duy nhất:** Mới `frontend/src/lib/features/llm/OrganizationModelPolicyEditor.svelte`, `frontend/tests/f016-model-policy-editor.test.mjs`, `frontend/tests/f016-model-policy-editor-browser.mjs`, `frontend/tests/fixtures/F016ModelPolicyEditorHarness.svelte`.
  - **Work:** Làm component theo Flow 8. Test render trước implementation; browser harness controlled props/callbacks, không mock API tương lai. Không sửa bất kỳ file khác, dependency, locale, app entry hoặc test cũ. Fixture/harness có thể dùng Vite configFile:false và plugin Svelte hiện có để serve bootstrap từ bộ nhớ. Loopback port ngẫu nhiên; đóng browser/server trong finally.
  - **Done:** AC14. Node test, full frontend test/build/lint/format check và browser script được chạy hoặc báo blocked chính xác. Kiểm tra callback allow/default/unavailable/search/disabled, props update không callback, hai instance, bàn phím, 360px, hai theme, ba locale labels, không page errors. Bàn giao commit chỉ có bốn tệp whitelist và test output.
  - **Avoid:** `backend/`, migrations, package/lock/config, API/state/shared types, `WorkspacePage`, `SettingsPanel`, `ModelSelector`, `LlmConnectionForm`, i18n, specs, README và test hiện có. Không sửa ngoài whitelist để làm suite xanh.

- [ ] **F016-008 — Tích hợp UI quản trị và nhân viên** — Lead; sau 006 và bàn giao 007
  - **Where:** `frontend/src/lib/features/llm/LlmConnectionForm.svelte`, `ModelSelector.svelte`, `features/settings/SettingsPanel.svelte`, `pages/WorkspacePage.svelte`, `i18n/messages.ts`, `i18n/locales/{vi-VN,en-US,ru-RU}/translation.json`; mới `frontend/tests/f016-organization-llm-browser.mjs`.
  - **Work:** Review commit Claude, mount component không sửa whitelist trong lúc worker làm. Tích hợp URL/key/verify/apply, trạng thái chưa cấu hình, allowlist/default draft và owner lifecycle. Cung cấp labels dịch và catalog có unavailable rows. Tách admin privilege errors khỏi CSRF. Không đưa API/business logic vào page.
  - **Done:** AC11/13/14; UI thực nối owner/API mới, không còn personal settings hoặc employee link gây gọi admin API ngoài quyền.

- [ ] **F016-009 — Regression, tài liệu và nghiệm thu** — Lead; sau 001–008
  - **Where:** Test F016 mới ở trên; `tests/test_f006_002_llm_settings.py`, `test_f006_003_004_llm.py`, `test_f006_005_chat_models.py`, `test_f006_008_browser_e2e.py`, `test_f005_007_e2e.py`, `test_f004_005_chat.py`, `test_f012_001_system_role.py`, `test_f015_007_activity_e2e.py`; frontend LLM API/form/browser/E2E tests và các fixture caller thực sự chịu ảnh hưởng. `README.md`, `specs/02-architecture.md`, `specs/to-be/admin-roadmap.md`, `docs/database-setup.md` nếu cần hướng dẫn cutover/secret cho người vận hành; spec này.
  - **Work:** Cập nhật assertions personal/env đã bị thay thế, giữ coverage transport/proxy/snapshot/ACL. Chạy required checks, ghi lỗi baseline riêng. Cập nhật kiến trúc và hướng dẫn thiết lập, backup/cutover/secret rotation; giữ developer notes trong specs. Báo đường dẫn bổ sung trước sửa nếu phát hiện caller khác.
  - **Done:** AC01–15 có bằng chứng; chỉ tick task đã hoàn tất và kiểm tra đạt. Không tick task đang blocked hoặc che fail/skip.

### Lệnh và điều kiện kiểm chứng

Theo README/AGENTS và `docs/database-setup.md`, không chạy hai backend suite cùng lúc.
Docker Desktop phải dùng Linux containers. Backend test dùng disposable PostgreSQL,
Alembic và fake provider; không cần provider key thật hoặc application DB reset.

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONPATH = 'tests;backend'
npm --prefix frontend run build
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py'
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run format:check
```

Claude chạy riêng, trong worktree của mình:

```powershell
node --experimental-strip-types --test frontend/tests/f016-model-policy-editor.test.mjs
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run lint
npm --prefix frontend run format:check
node frontend/tests/f016-model-policy-editor-browser.mjs
```

Lead chạy thêm `node frontend/tests/f016-organization-llm-browser.mjs` và các browser
regression liên quan theo README/AGENTS sau build. Browser cần Playwright/Chromium;
cấu hình `RUVIE_PLAYWRIGHT_PATH`, `RUVIE_BROWSER_PATH` theo máy hiện tại. Thiếu prerequisite
là blocked/skip, không phải pass. Không tự cài runtime/browser ngoài phạm vi đã duyệt.

Chỉ format tệp được giao; không chạy formatter ghi toàn repo. Build có thể sinh
`frontend/dist/`; browser artifact chỉ ở ignored `logs/`, Claude dùng
`logs/f016-model-policy/`. Không commit generated files, secrets, logs hoặc environments.
Mỗi bên ghi exact commands và số pass/fail/skip từ output. Lead đối chiếu ma trận
acceptance sau tích hợp; build của component chưa mount không thay thế browser test.

### Trạng thái kiểm chứng tài liệu

Spec được lập bằng đọc nguồn và đối chiếu thiết kế/split đã duyệt. Đã chạy SQL migration và migration PostgreSQL disposable, unit/backend focused và
frontend/browser checks như phần tiến độ. Backend focused F016 trước lần bổ sung
initial-concurrency/chat-error đạt 23/23; full backend sau cutover đạt 347 pass, 1 fail, 7 skip trên 355 test.
Chỉ F016-006/007 được đánh dấu theo bằng chứng frontend đã đạt. Những task khác và
acceptance criteria còn chờ full regression; không coi feature đã hoàn tất.

### Bằng chứng kiểm chứng sau cutover (2026-10-29)

- `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py'`:
  355 test; 347 pass, 1 fail, 7 skip. Output: `logs/f016-backend-tests.log`.
  Failure duy nhất: `test_f004_001_chat_contract.ChatConfigurationTests.test_loads_openai_compatible_provider_from_server_environment`.
  Test còn yêu cầu env fallback; user từ chối sửa tệp này. Không đổi implementation
  để khôi phục fallback trái thiết kế F016 và không che failure.
- Với browser variables được cấu hình, `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_f006_008_browser_e2e.py`:
  1 pass, 0 fail/skip; backend/PostgreSQL/provider fake thật, hai tài khoản và ACL.
  Output: `logs/f016-real-browser-e2e.log`.
- `npm --prefix frontend test`: 108 pass, 0 fail/skip với Playwright/Chromium đã cài.
  Output: `logs/f016-frontend-tests.log`.
- `npm --prefix frontend run build`, `run lint`, `run format:check`: đạt.
- `node frontend/tests/f016-model-policy-editor-browser.mjs`: 23 checks đạt;
  `node frontend/tests/f016-organization-llm-browser.mjs`: 7 checks đạt.
- Browser regression: auth 64 checks, theme 9 checks, admin 34 groups, frontend UX
  42 checks đạt. Workspace chưa đạt do helper accessibility còn metadata cũ;
  LLM/i18n migration test còn dang dở. Chi tiết ở `logs/f016-*-browser.log`.

Các backend task đã có code và test mới, nhưng chưa tick hoàn tất do required full
suite còn failure. F016-008/009 chưa tick vì regression còn lại chưa hoàn tất.
Chưa sửa `workspace-a11y-browser.mjs` ngoài phạm vi đã báo. Không sửa bốn tệp bị từ chối.

### Bổ sung UI key action và thông báo (2026-10-29)

Được user duyệt: dropdown theo theme thay menu native của hệ điều hành; icon dấu
chấm than cạnh nhãn mở tooltip bằng hover/focus, Escape đóng. Tooltip giải thích
khi nào giữ key, thay key hoặc không dùng key; việc thay/xóa chỉ được lưu sau apply.
Check connection và Reload chủ động hiện toast thành công/lỗi an toàn; mở form tự
động không hiện success toast. Reload thành công bỏ draft. Rời form vô hiệu hóa
thông báo từ request cũ. Không thay backend hoặc contract bảo mật.

Kiểm chứng bổ sung UI: frontend suite 109/109 pass, 0 fail/skip; build/lint/format check đạt. Browser tổ chức 10 checks đạt, bao gồm tooltip focus/Escape, dropdown bàn phím, toast verify/reload thành công và lỗi. `open()` trả kết quả chỉ cho request hiện hành; test state xác minh response muộn sau close bị bỏ qua.

### Áp dụng mockup light/dark (2026-10-29)

Đã được duyệt và áp dụng bố cục hai bước. Form có header/Tải lại, kết nối dịch vụ,
thao tác key gọn trên hàng nhãn, nút hiện/ẩn key draft, phản hồi kiểm tra và vùng cấp
model dạng bảng. Chưa verify thì chỉ hiện hướng dẫn; không mở search/table trống.
Footer giữ thống kê draft và nút Apply; toast/tooltip và contract policy giữ nguyên.

Kiểm chứng: frontend unit 109/109 pass (0 fail/skip), build/lint/format đạt;
browser component 23 checks và luồng tổ chức 11 checks đạt. Đã xem ảnh chụp thực
cả light/dark tại `logs/f016-mockup/`. Không dùng ảnh AI làm bằng chứng triển khai.
Các regression và failure backend đã ghi ở trên vẫn chưa được coi là hoàn tất.

### Tinh chỉnh bề mặt và dropdown (2026-10-29)

Theo yêu cầu user: bỏ border/background/shadow riêng của form để hòa nền Settings;
thay ký tự chevron bằng SVG có gap cố định, xoay theo trạng thái mở và tôn trọng
reduced motion. Bỏ dòng inline chung `llm_settings_unavailable` ở cuối form; lỗi
thao tác chủ động vẫn đi qua toast, conflict và unknown outcome vẫn được giữ.
Test SSR xác minh không còn câu lỗi chung; browser xác minh border=0, background
transparent, chevron SVG và luồng cũ vẫn đạt 12 checks. Đề xuất câu chữ tiếp theo
chưa được áp dụng khi chưa có duyệt của user.

### Chốt câu chữ giao diện (2026-10-29)

Đã được user duyệt: tiêu đề Cấu hình LLM; mục 2 giữ Model được cung cấp; URL là
Địa chỉ API (Base URL); key actions là Giữ key hiện tại / Nhập key mới / Không sử dụng key.
Tooltip dùng mô tả ngắn theo tình huống và một dòng chung về thời điểm áp dụng.
Lưu ý về khả năng chat chuyển sang title/accessible description của Check connection.
Footer hiển thị tên model mặc định khả dụng, hoặc Chưa chọn model mặc định; không
hiển thị cố định Mặc định: 1. Reload dùng màu phụ theo theme để phân biệt với Apply.
Ba locale vi-VN/en-US/ru-RU được cập nhật cùng key/placeholder.

Đã sửa markup để dòng nhắc áp dụng nằm trong tooltip, ẩn sau Escape. Browser
regression từng fail vì dòng đó lộ ra ngoài, sau sửa đạt. Kiểm chứng cuối: build,
lint, format check đạt; frontend 109 pass, 0 fail/skip; browser tổ chức 13 checks đạt.
Lệnh: npm --prefix frontend run build/test/lint/format:check (chạy từng script);
node frontend/tests/f016-organization-llm-browser.mjs với browser variables.
Không đổi backend hoặc trạng thái nghiệm thu toàn bộ F016 ở phần trên.
