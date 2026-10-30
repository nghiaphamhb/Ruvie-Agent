# F017 - Tách kết nối AI và quản lý kết nối embedding

Ngày lập: 2026-10-30.
Trạng thái: Đã triển khai và nghiệm thu F017-001–008.
Baseline: `d0530fe` (`feat: admin sets up shared chat model`), kế thừa F016.
Tên file/class/API mới trong tài liệu là đề xuất triển khai.

## Goal

Ruvie Agent cung cấp hai kết nối độc lập cho model trả lời và model embedding.
Admin quản lý cả hai trong System settings, không phải sửa `.env` để đổi key embedding.
Backend và worker sử dụng cùng cấu hình embedding trong PostgreSQL.
Thay kết nối đã lưu có hiệu lực với request/job mới mà không cần khởi động lại.

### Thuật ngữ đã chốt

| Thuật ngữ UI | Ý nghĩa | Tên kỹ thuật |
| --- | --- | --- |
| Kết nối AI | Nhóm cấu hình hai dịch vụ | AI connections |
| Model trả lời | Model sinh câu trả lời | Chat model |
| Model embedding | Model chuyển văn bản thành vector | Embedding model |
| Kết nối dịch vụ | Base URL và thông tin xác thực | Provider connection |
| Hồ sơ embedding | ID model, số chiều và distance metric | Embedding profile |
| Tạo lại chỉ mục | Tạo lại vector bằng hồ sơ khác | Reindex; ngoài F017 |

Không gọi embedding là model trả lời. Một nhà cung cấp có thể phục vụ cả hai
kết nối, nhưng URL/key/version và trạng thái lưu của chúng độc lập.

### Code currently does

| Nguồn active đã kiểm tra | Hành vi hiện tại | Khoảng cách |
| --- | --- | --- |
| `frontend/src/lib/features/settings/SettingsPanel.svelte` | Một mục kết nối LLM trong settings hệ thống | Chưa có nhóm mở/thu với hai mục con |
| `features/llm/LlmConnectionForm.svelte` | Form URL/key, tooltip, verify, policy và apply | Cần tái sử dụng bố cục cho hai mục |
| `organization-llm-api.ts`, `organization-llm-state.svelte.ts` | Admin quản lý kết nối trả lời, version/generation và secret draft | Chưa có owner embedding độc lập |
| `backend/ruvie/models/llm.py`, `services/llm.py` | Kết nối trả lời mã hóa trong DB; allowlist/default | Giữ dữ liệu và contract F016 |
| `config.py::load_settings`, `adapters/embedding.py::create_query_embedder` | Kết nối embedding lấy từ môi trường | Chưa có persistence/admin API |
| `main.py::lifespan`, `worker_cli.py::main` | Tạo client/embedder từ lúc khởi động | Key mới chưa tự có hiệu lực ở cả hai process |
| `services/chat.py::ChatService.prepare` | Resolve model trả lời, embedding, authorized retrieval, sau đó stream | Lỗi embedding bị gộp thành provider unavailable |
| `api/documents.py::retrieve_chunks` | Gọi embedder trực tiếp trong route | Khi đổi luồng này phải chuyển use case sang service |
| `services/documents/ingestion.py::DocumentIngestionWorker` | Nhận embedder/profile từ caller | Phải snapshot cấu hình theo job |
| `models/documents.py::DocumentRevision` | Lưu profile theo revision; chunk vector 1024 chiều | Không được sửa profile/vector cũ tại chỗ |

Chẩn đoán vận hành trước F017 đã gặp key embedding hết hạn dù catalog LLM tải được.
Đây là lý do tách trạng thái kiểm tra hai kết nối; không phải bằng chứng tính năng
F017 đã được triển khai. Không đưa key thật hoặc nội dung hội thoại vào spec/test.

### Nguồn tái sử dụng

- Active: `LlmConnectionForm`, owner/API tổ chức, `OrganizationModelPolicyEditor`,
  i18n/toast và settings layout. Tách phần form dùng chung; giữ policy trả lời riêng.
- Active: `LlmSecretStore`, `LlmRoute`, identity admin, `AuditEventWriter`, version
  conflict và key actions của F016. Không trả secret/ciphertext về browser.
- Active: `normalize_llm_url`, `PinnedLlmTransport`, embedding adapter và profile
  validation. Dùng transport được bảo vệ cho catalog/probe/runtime embedding.
- Legacy: `references/backend/ruvie/routers/retrieval.py::get_embedding_config`,
  `update_embedding_config`; `references/src/lib/components/admin/Settings/Documents.svelte::embeddingModelUpdateHandler`.
  Tái sử dụng ý tưởng cấu hình embedding riêng, pending và kiểm tra trước lưu.
  Không port response chứa key, logging cấu hình, localStorage token, runtime cache
  toàn cục hoặc engine Ollama/Azure/internal-model không thuộc phạm vi.
- Không import/chạy legacy runtime. Ưu tiên code active; nếu port source khi triển
  khai phải ghi rõ phần thích nghi. Không đọc thư mục tên `archive` ở bất kỳ cấp nào.

## User Story

- Là admin, tôi muốn mở Model trả lời hoặc Model embedding dưới Kết nối AI.
- Là admin, tôi muốn hai form giống nhau về bố cục nhưng có nội dung đúng chức năng.
- Là admin, tôi muốn dùng hai nhà cung cấp hoặc hai API key độc lập.
- Là admin, tôi muốn xem/chọn model embedding và được giải thích nếu chưa hỗ trợ.
- Là admin, tôi muốn biết lỗi thuộc catalog, model trả lời hay embedding.
- Là nhân viên, tôi muốn chat/tìm kiếm dùng kết nối hợp lệ và vẫn giữ quyền tài liệu.

## Scope

### In

- Nhóm Kết nối AI mở/thu; hai mục con thụt lề 16–20px trong sidebar settings hiện có.
- Một bộ component trình bày chung; hai owner/API và bản nháp tách biệt.
- Kết nối embedding singleton trong DB, key mã hóa và admin read/catalog/verify/apply.
- Catalog embedding qua endpoint OpenRouter `/embeddings/models`, không trộn với
  `/models` trả lời. Runtime embedding vẫn OpenAI-compatible `/embeddings`.
- Cho chọn model embedding kể cả model chưa hỗ trợ để xem thông tin/cảnh báo.
  Không cho lưu model hoặc số chiều không được hỗ trợ.
- Profile được áp dụng trong F017 chỉ là `baai/bge-m3`, 1024 chiều, cosine.
- Hot update URL/key embedding cho backend/worker; không thay profile tài liệu.
- Cập nhật lỗi an toàn, kiểm thử, kiến trúc và hướng dẫn vận hành khi triển khai.

### Out

- Đổi profile sang model khác, reindex, sửa vector/revision cũ, nhiều vector spaces.
- Nhiều kết nối cho một loại, load balancing, failover tự động hoặc chọn embedding theo user.
- UI quản lý proxy. Giữ `LLM_PROXY_URL`, `EMBEDDING_PROXY_URL` và local-origin allowlist
  phía server; lỗi proxy không tự chuyển direct.
- Tự sao chép key trả lời sang embedding; tự nhập key từ `.env` vào DB; worker fallback env.
- Di chuyển/đổi tên bảng trả lời F016 chỉ để đồng bộ thuật ngữ; sửa auth/ACL ngoài phạm vi.
- Thiết kế mobile mới. Giữ giao diện desktop và không làm hỏng hành vi hiện có.

## Flow

### 1. Điều hướng và form dùng chung

```text
Kết nối AI ▾
    Model trả lời
    Model embedding
```

Mục cha là nút mở/thu với `aria-expanded`, không phải một tab nội dung thứ ba.
Mỗi mục con mở một panel; có active state, keyboard focus và nhãn dịch tương ứng.
Đi vào một mục con làm nhóm cha mở. Thu nhóm không xóa draft/panel đang chọn.
Chỉ mục con đang chọn có nền nổi bật. Giữ shortcut cấu hình LLM hiện tại mở Model
trả lời; người thường không được thấy hoặc gọi API quản trị embedding.

Form chung có header/Tải lại, bước 1 Kết nối dịch vụ, bước 2 cấu hình model,
footer trạng thái và Áp dụng cấu hình. Giữ dropdown/hint dưới nhãn API key,
nút Kiểm tra kết nối bên phải, tick trắng nền xanh tròn, bảng cuộn tối đa 360px
và tiêu đề sticky. Không sao chép toàn bộ form thành hai component gần giống nhau.

Component chung nhận labels, trạng thái và callback; không chứa nghiệp vụ DB/API.
Slot/snippet cho bước 2: trả lời giữ allowlist/default; embedding dùng một lựa chọn
radio và thông tin số chiều/profile. Embedding không có “Cho phép tất cả”.

Mỗi panel có toast/loading/error riêng; dùng ID riêng cho input/radio/tooltip/toast.
Tải lại chỉ tải cấu hình của panel đó và bỏ draft sau khi tải thành công.
Chuyển giữa hai mục giữ draft trong bộ nhớ, gồm key mới chưa lưu. Dừng request/toast
cũ không cho cập nhật panel mới; đánh dấu kết quả cần kiểm tra lại nếu đã hủy probe.
Rời System settings, logout, thay user hoặc mất role phải xóa cả hai key draft và
vô hiệu hóa response muộn. Không ghi key vào URL hoặc browser storage.

### 2. Catalog và chọn model embedding

1. Admin nhập URL/key action rồi bấm Kiểm tra kết nối. Server kiểm tra quyền,
   chuẩn hóa URL và tải catalog. Kết quả này chỉ có nghĩa tải catalog thành công.
2. Với OpenRouter, gọi `GET {base_url}/embeddings/models` bằng key của draft.
   Danh sách được chuẩn hóa thành ID/name và metadata an toàn. Không suy đoán model
   embedding từ tên hoặc lấy catalog trả lời làm fallback.
3. Admin tìm theo ID/name và chọn một model. Không tự chọn dòng đầu tiên.
   Khi tải cấu hình đã lưu, giữ model đã lưu; model mất catalog có trạng thái unavailable.
4. Mọi model trong catalog được phép chọn làm draft, trừ lúc form busy/disabled.
   Nếu model ID khác `baai/bge-m3`, hiển thị inline warning kèm tooltip có thể focus:
   “Ứng dụng chưa hỗ trợ model này. Hiện hỗ trợ baai/bge-m3, 1024 chiều.”
   Toast cảnh báo một lần cho thao tác chọn chủ động; không toast lặp khi render/reload.
   Radio vẫn giữ model user vừa chọn. Apply bị khóa; cấu hình active không đổi.
5. Số chiều catalog thiếu là “Chưa xác định”, không phải tương thích hay lỗi model.
   Không suy số chiều từ tên. Với model được hỗ trợ, admin bấm Kiểm tra model để
   tạo vector thật qua `POST /embeddings` với câu cố định không chứa dữ liệu người dùng.
6. Server xác minh vector hữu hạn, số chiều 1024 và đúng model đã chọn. Vector sai
   số chiều trả mã lỗi riêng; UI giải thích số chiều nhận được nếu an toàn, giữ draft,
   bỏ verified và khóa apply. Không lấy 1024 phần tử đầu hoặc padding vector.
7. Với model/metadata biết chắc không hỗ trợ, server từ chối trước probe embedding.
   Không cho frontend vượt kiểm tra bằng cách tự gửi dimensions=1024 cho model khác.
8. Danh sách không hỗ trợ endpoint catalog vẫn cho biết lỗi catalog riêng; không
   invent model list hoặc dùng dữ liệu chat. Nhập tay model ID ngoài catalog chưa thuộc F017.

UI không cung cấp ô sửa số chiều trong F017; hiển thị số chiều từ metadata/probe.
Cùng số chiều không đủ để coi hai model tương thích. Trường hợp chưa hỗ trợ phải
giải thích, không chỉ disable radio hoặc đưa thông báo “không kết nối được”.

Tài liệu tham khảo endpoint:
[OpenRouter embeddings catalog](https://openrouter.ai/docs/api/api-reference/embeddings/list-embeddings-models).
Đây là khả năng provider, không phải tuyên bố backend Ruvie đã có catalog embedding.

### 3. Contract API đề xuất

Giữ `/admin/llm/connection` của F016 cho model trả lời. Không nhận `kind` tùy ý để
trộn cấu hình hai loại vào một row. Thêm router/service/contracts embedding riêng:

| Method/path đề xuất | Input | Output/hành vi |
| --- | --- | --- |
| GET `/admin/embedding/connection` | Session admin | Metadata cấu hình đã lưu, không probe provider |
| POST `/admin/embedding/connection/catalog` | Draft URL, key action, expected_version | Catalog an toàn và version; không ghi DB |
| POST `/admin/embedding/connection/verify` | Draft + model_id | model_id, dimension, distance_metric, compatible, version khi probe thành công |
| PUT `/admin/embedding/connection` | Draft + model_id | Tự probe lại, kiểm tra profile, commit và trả metadata mới |

Draft gồm `base_url`, `key_action: keep|replace|clear`, `expected_version`,
`api_key` write-only chỉ khi replace. Không tin `verified`, `compatible`, dimension
hoặc catalog do browser gửi. Không tạo saved state từ verify/catalog.

Metadata gồm `configured`, `base_url`, `has_api_key`, `model_id`, `dimension`,
`distance_metric`, `version`, `updated_at`. Unconfigured trả null cho profile/URL.
Catalog trả `models: [{id,name,dimension:number|null,supported:boolean,reason_code:string|null}]`
và `version`. Server tính supported theo profile cho phép, metadata chiều nếu có;
supported không thay thế việc probe thật. Không trả vector mẫu hoặc response provider thô.

Key actions theo F016: keep chỉ khi đã configured và URL chuẩn hóa không đổi;
replace cần key mới; clear chỉ xóa key khi apply thành công. Không tự lấy key trả lời.
Đổi URL không gửi key cũ tới host mới. Provider không cần key được dùng clear.

Mọi endpoint yêu cầu admin active trong DB. POST/PUT yêu cầu Origin/CSRF hợp lệ.
PUT kiểm tra lại quyền sau probe và trong transaction; compare-and-swap version,
audit/cấu hình commit nguyên tử. Hai apply cùng expected_version chỉ một thành công.
Probe không giữ transaction/row lock qua mạng; giữ version/snapshot rồi recheck.

Lỗi dự kiến: 409 `configuration_conflict`; 422 `embedding_model_unsupported`,
`embedding_dimension_unsupported`, `invalid_embedding_request`; 503
`embedding_provider_unavailable`, `embedding_settings_unavailable`,
`embedding_not_configured`. 401/403 giữ phân biệt hết phiên, mất role và CSRF.
Lỗi validation không echo key. Response có no-store; audit chỉ actor/version/profile
và loại thao tác, không raw URL chứa secret, API key, ciphertext hay vector.

### 4. Persistence và cutover

Đề xuất model `OrganizationEmbeddingSettings`, bảng `organization_embedding_settings`.
Thêm migration Alembic kế tiếp (dự kiến 0013; kiểm tra head lúc triển khai).
Không sửa migration 0012 hoặc bảng trả lời đã lưu.

| Cột đề xuất | Ràng buộc |
| --- | --- |
| id | PK integer, duy nhất id=1 |
| version | Integer >=0, tăng khi apply thành công |
| base_url, api_key_ciphertext | URL chuẩn hóa, key mã hóa hoặc NULL |
| model_id, dimension, distance_metric | Khi configured: baai/bge-m3, 1024, cosine |
| updated_by | FK user, có thể SET NULL |
| created_at, updated_at | Timestamp timezone phía DB |

Seed một row version=0 chưa cấu hình, không key; không seed env hoặc key trả lời.
Version 0 có URL/profile/key NULL. Configured phải có profile hợp lệ; key được NULL
cho provider không yêu cầu auth. Dùng lại cơ chế Fernet/versioned ciphertext F016;
thiếu key mã hóa hoặc ciphertext hỏng là lỗi, không coi là clear key.

Cutover có khoảng bảo trì: backup theo hướng dẫn vận hành, upgrade schema rồi admin
cấu hình/verify/apply embedding trên UI trước khi mở lại chat/ingestion. Không tự
copy `.env` vào DB. Giữ nguyên tài liệu/chunk/preference trả lời. `.env` chỉ còn giữ
khóa mã hóa, proxy và các thiết lập hạ tầng/profile cố định cần thiết.
Các biến URL/key embedding cũ không còn là fallback runtime sau cutover.
Ứng dụng phải khởi động được khi row chưa cấu hình để admin hoàn tất thiết lập.
Downgrade phải có hướng dẫn riêng: không chuyển key mã hóa sang plaintext hoặc
khẳng định tự khôi phục kết nối env. Không chạy migration application DB trong test.

### 5. Runtime backend và worker

Đề xuất `EmbeddingConnectionService` resolve snapshot URL/key/profile/version từ DB.
Client/adapter cho một operation giữ snapshot; không mutate shared client khi admin
apply. Không cache cấu hình đến hết lifetime process, không polling cấu hình.

- Chat/retrieval: resolve trước lần embedding của request. Request sau commit đọc
  version mới; request đã resolve tiếp tục snapshot cũ. Không đổi key giữa request.
- Worker: resolve theo job đã claim; dùng cùng snapshot cho mọi batch của job.
  Job tiếp theo đọc version mới. Không resolve lại mỗi chunk. Thiếu cấu hình phải
  theo luồng job failure hữu hạn hiện có, không crash loop hoặc tạo READY thiếu vector.
- Upload: profile ghi vào revision lấy từ server và phải đúng profile được hỗ trợ.
  Không nhận URL/key/profile từ client. Job đối chiếu profile revision trước embedding;
  sai profile phải fail an toàn, không sửa metadata revision để “khớp”.
- `api/documents.py::retrieve_chunks`: chuyển embed + retrieval vào service use case;
  route chỉ validate input, lấy identity và serialize kết quả. Không nhân rộng exception
  gọi embedder trực tiếp trong API.
- AuthorizedRetrievalService vẫn áp dụng predicate readable-document trước context
  và serialization; không bypass ACL vì actor là admin.
- LLM trả lời và embedding resolve độc lập. Lỗi một kết nối không fallback sang key,
  URL hoặc model của kết nối kia. Không đổi thứ tự kiểm tra policy trả lời trước embedding.

Catalog/probe/runtime embedding đều dùng transport kiểm tra URL/IP/DNS pinning,
TLS và reject redirect. Giữ proxy embedding phía server; không tin proxy từ browser
hoặc ambient HTTP_PROXY. Local service phải thuộc allowlist server hiện có.

Chat giữ lỗi trả lời hiện có và phân biệt lỗi embedding trước stream bằng mã an toàn
`embedding_unavailable`. Người dùng thấy “Kết nối tìm kiếm tài liệu đang gặp sự cố.
Vui lòng liên hệ quản trị viên.” Không gửi raw upstream error/key cho nhân viên.
Admin thấy lỗi xác thực/timeout/model/chiều bằng safe code được dịch, không raw body.

### 6. Kiểm tra model trả lời và vòng đời

Giữ verify catalog F016 nhưng ghi rõ catalog thành công không chứng minh sinh câu
trả lời được. Thêm thao tác Kiểm tra model cho model mặc định đã chọn: dùng câu thử
cố định, không tài liệu/hội thoại; xác nhận có nội dung trả về. Không probe mọi model
đã cấp hoặc hứa tất cả model hoạt động. Không làm đổi allowlist/default đang lưu.
Apply trả lời giữ contract F016; lỗi smoke test có trạng thái riêng với catalog.
Apply embedding luôn probe vector thật phía server dù UI đã verify.

Sửa URL/key/model embedding làm mất verified. Đổi search, theme/locale không làm
mất lựa chọn. Mất response PUT: báo chưa xác định, xóa key draft, đọc lại metadata;
không retry mutation hoặc coi version thay đổi là bằng chứng thao tác mình thành công.

## Edge Cases

| Điều kiện | Hành vi bắt buộc |
| --- | --- |
| Catalog có model khác nhưng cùng 1024 chiều | Cho chọn xem, cảnh báo unsupported, không apply |
| Model hỗ trợ nhưng vector 768/1536 chiều, NaN hoặc Infinity | Probe/apply thất bại, cấu hình cũ giữ nguyên |
| Thiếu metadata số chiều | Hiện chưa xác định; probe thật trước apply |
| Không có kết quả search/catalog rỗng | Empty state riêng; không chọn model giả hoặc dòng đầu |
| Model đang lưu mất catalog | Hiện unavailable, không tự thay model; runtime lỗi an toàn |
| Provider không có endpoint catalog embedding | Báo catalog unsupported/unavailable, không dùng catalog chat |
| Key hết hạn, rate limit, timeout | Giữ cấu hình active, lỗi đúng bước, không fallback/retry mutation |
| Thiếu khóa mã hóa/ciphertext hỏng | Báo settings unavailable; không gọi provider như không key |
| Thay kết nối lúc job/request đang chạy | Operation cũ giữ snapshot; operation mới đọc version mới |
| Đổi URL và keep | Từ chối trước khi gửi key cũ tới URL mới |
| Admin bị khóa/hạ role trong probe | Không commit; xóa secret draft và rời quyền quản trị |
| Chuyển mục con khi request đang chạy | Không cho response cũ cập nhật mục mới; giữ draft hợp lệ |
| Đổi embedding khi đã có tài liệu | Chỉ đổi kết nối cùng profile; không sửa chunk/revision cũ |
| Hai admin cùng lưu | Một thành công, một 409; audit chỉ có thay đổi đã commit |
| Embedding chưa cấu hình sau cutover | Admin vẫn mở settings; chat/retrieval/job lỗi có kiểm soát |

## Acceptance Criteria

- [x] AC01: Menu cha Kết nối AI mở/thu, hai mục con đúng nhãn/active/keyboard; shortcut cũ mở Model trả lời.
- [x] AC02: Hai form dùng component bố cục chung, text đúng chức năng, ID độc lập, theme sáng/tối và vi/en/ru; giữ bố cục desktop đã chốt.
- [x] AC03: Draft, URL/key, version, loading/toast và lưu độc lập; chuyển con giữ draft, rời settings/logout/mất role xóa secret và bỏ response muộn.
- [x] AC04: Catalog embedding gọi đúng endpoint, search ID/name, không dùng catalog trả lời hoặc model giả.
- [x] AC05: Chọn được model chưa hỗ trợ; giữ radio draft, có inline/tooltip và toast chủ động, khóa apply; API trực tiếp cũng không lưu được.
- [x] AC06: Chỉ baai/bge-m3/1024/cosine được áp dụng; probe thật kiểm tra vector hữu hạn và chiều; metadata thiếu không bị đoán là 1024.
- [x] AC07: Migration tạo singleton chưa cấu hình, không seed secret/env, không đổi dữ liệu trả lời/revision/chunk; SQL và upgrade/downgrade được kiểm chứng trên DB disposable.
- [x] AC08: GET/catalog/verify/apply admin kiểm tra quyền; mutation/probe có CSRF/Origin; recheck role và version tại commit; rollback audit/config cùng nhau.
- [x] AC09: Key mã hóa at rest, write-only; không lộ trong response/errors/logs/audit/storage; key actions và URL change tuân thủ F016.
- [x] AC10: Proxy/SSRF/DNS/TLS/redirect bảo vệ cả catalog, verify và runtime embedding; không direct/env fallback.
- [x] AC11: Backend/worker đang chạy dùng version mới cho request/job mới không restart; operation đang chạy giữ snapshot cũ cho mọi batch.
- [x] AC12: Upload/job/query dùng cùng profile; ACL retrieval/citations default-deny giữ nguyên; route retrieval không còn orchestration embedder trực tiếp.
- [x] AC13: Chưa cấu hình hoặc provider lỗi không ngăn admin mở settings; nhân viên nhận lỗi embedding riêng, không raw error hay secret.
- [x] AC14: LLM trả lời F016 giữ allowlist/default/preference; kiểm tra model trả lời có request sinh thử riêng, không coi catalog là smoke test.
- [x] AC15: Có kiểm thử concurrency, late response, failed/unknown apply, quyền bị thu hồi và hai process; báo chính xác pass/fail/skip, không tính skip là pass.
- [x] AC16: Hướng dẫn backup/cutover/admin setup không cần sửa key embedding trong .env; tồn đọng F016 được báo riêng, không che bằng sửa fallback trái spec.

## Tasks

Các task dưới đây đã được triển khai và kiểm chứng theo kết quả nghiệm thu. Trước mỗi đợt code phải báo và duyệt chính
xác các tệp sửa theo AGENTS.md; danh sách Where là kế hoạch, không cấp quyền sửa.
Lead sở hữu schema, API, shared contract và business logic. Chưa giao task cho agent
song song trong F017; nếu cần giao UI độc lập phải chốt contract và whitelist trước.

- [x] **F017-001 — Schema và cutover embedding**
  - **Work:** Chốt schema; migration kế tiếp, singleton/check constraints/FK/version; không seed env hoặc sửa 0012. Ghi chiến lược cutover và downgrade.
  - **Where:** Đề xuất `backend/migrations/versions/0013_organization_embedding_settings.py`, `models/embedding.py`, `models/__init__.py`, `tests/test_f017_001_embedding_schema.py`.
  - **Done:** AC07; upgrade từ 0012 có dữ liệu vẫn giữ reply policy, revision/profile và chunk; migration SQL/downgrade disposable đạt.

- [x] **F017-002 — Adapter catalog/probe embedding có bảo vệ mạng**
  - **Work:** Dùng active transport, catalog `/embeddings/models`, normalize metadata; vector probe finite/1024; safe typed result/errors và profile compatibility. Không làm lỏng proxy/SSRF LLM.
  - **Where:** `adapters/embedding.py`, `adapters/llm.py` chỉ khi cần tái sử dụng transport; đề xuất `contracts/embedding.py`, `tests/test_f017_002_embedding_adapter.py`.
  - **Done:** AC04–06/10; fake providers phủ endpoint, missing dimensions, unsupported ID, NaN/Infinity, proxy, DNS/TLS và redirect.

- [x] **F017-003 — Service quản trị và API embedding** (sau 001–002)
  - **Work:** Chốt contracts; implement metadata/catalog/verify/apply, secret reuse, CAS version, recheck actor, audit nguyên tử và unknown outcomes.
  - **Where:** Đề xuất `services/embedding.py`, `api/embedding.py`, `contracts/embedding.py`, `tests/test_f017_003_embedding_service.py`, `tests/test_f017_004_embedding_api.py`; `main.py` đăng ký router; reuse `services/llm_secrets.py`, auth/audit hiện có.
  - **Done:** AC08–09/15; user trực tiếp không probe/read/mutate, invalid payload không echo key, unsupported model không commit, concurrent PUT chỉ một thắng.

- [x] **F017-004 — Runtime snapshot cho API và worker** (sau 003)
  - **Work:** Thay embedder startup bằng resolver theo operation; job giữ một snapshot; chuyển use case retrieve sang service; profile revision/ACL giữ nguyên. Bỏ runtime env URL/key fallback, giữ cấu hình proxy/khóa mã hóa.
  - **Where:** `main.py`, `dependencies.py`, `config.py`, `worker_cli.py`, `services/chat.py`, `api/documents.py`, `services/documents/ingestion.py`; đề xuất `services/documents/retrieval.py`, `tests/test_f017_005_embedding_runtime.py` và test worker tích hợp.
  - **Done:** AC11–13; hai process đọc version mới sau commit, old operation giữ snapshot; DB/provider failure không READY sai hoặc bypass ACL.

- [x] **F017-005 — Frontend API/state embedding độc lập** (sau contract 003)
  - **Work:** Xây owner/client theo F016; selection/support/verified, version/generation, lifecycle giữ draft khi đổi mục con và xóa secret khi rời settings. Không encode API trong page.
  - **Where:** Đề xuất `frontend/src/lib/features/embedding/embedding-api.ts`, `embedding-state.svelte.ts`, `frontend/tests/f017-embedding-api.test.mjs`, `f017-embedding-state.test.mjs`; điều chỉnh lifecycle owner trả lời khi cần.
  - **Done:** AC03/05/15; stale response/conflict/unknown-result không phục hồi draft cũ hoặc gây toast cho panel khác.

- [x] **F017-006 — Form chung và menu hai mục con** (sau 005)
  - **Work:** Tách presentation từ form hiện có; compose reply policy và single embedding selector; warning/tooltip/toast unsupported, model probe và dimension. Menu mở/thu, focus, i18n và IDs riêng; giữ kiểm thử UI F016.
  - **Where:** `features/settings/SettingsPanel.svelte`, `features/llm/LlmConnectionForm.svelte`, `pages/WorkspacePage.svelte`; đề xuất `features/ai-connections/AiConnectionForm.svelte`, `features/embedding/EmbeddingConnectionForm.svelte`, `EmbeddingModelSelector.svelte`; locales vi/en/ru; test form/selector/navigation mới F017.
  - **Done:** AC01–06; browser chọn model unsupported vẫn giữ lựa chọn/cảnh báo, không gửi apply; đủ keyboard, search, scroll, hai theme và ba locale.

- [x] **F017-007 — Smoke test model trả lời và lỗi theo bước**
  - **Work:** Thêm admin probe sinh câu trả lời cho default đã chọn; không gửi tài liệu/user message. Tách catalog success khỏi smoke success; giữ F016 apply contract. Map embedding error an toàn trong chat/retrieval/frontend.
  - **Where:** `api/llm.py`, `services/llm.py`, `contracts/llm.py`, `services/chat.py`, `api/chat.py`, frontend owners/error mapping/locales; tests reply probe và embedding error integration.
  - **Done:** AC13–14; catalog có thể thành công trong khi smoke fail và UI báo đúng; key provider không lộ cho nhân viên; không gọi mọi model trong allowlist.

- [x] **F017-008 — Regression, vận hành và nghiệm thu** (sau 001–007)
  - **Work:** Unit/service/API + real browser với fake providers và DB disposable; backend/worker không restart; ACL, schema, proxy, secret, F016 regression. Cập nhật README/.env.example, docs/database-setup và kiến trúc khi code thật đã có.
  - **Where:** Tests F017 mới; các test backend/frontend hiện có thực sự chịu ảnh hưởng; `README.md`, `.env.example`, `docs/database-setup.md`, `specs/02-architecture.md`, roadmap và spec này khi được duyệt phạm vi triển khai.
  - **Done:** AC01–16 được đối chiếu bằng output; full backend không chạy song song; báo baseline fail/skip và giới hạn riêng; không thay app DB hoặc key thật trong automated tests.

### Validation và tồn đọng kế thừa

Chạy lệnh chuẩn trong README/AGENTS, database-setup; không sao chép thành bộ lệnh
khác trong spec. Bắt đầu Docker Desktop Linux containers cho DB tests. Build trước
browser; cấu hình Playwright/Chromium, thiếu prerequisite là skip/blocked.
Test bằng fake providers, DB disposable; không gọi tài khoản trả phí hoặc reset DB
ứng dụng. Chỉ format tệp đã được duyệt. Không commit logs/dist/secrets.

F016 đã bàn giao nhưng full backend gần nhất ghi nhận 347 pass, 1 fail, 7 skip/355.
Failure cũ yêu cầu env fallback trái F016; workspace/LLM/i18n browser còn điểm chưa
nghiệm thu trong lịch sử. Không khẳng định tất cả regression đã pass.
Bốn tệp từng bị từ chối sửa (`tests/test_f004_001_chat_contract.py`,
`tests/test_f004_002_model_adapters.py`, `tests/test_llm_proxy.py`,
`backend/ruvie/database.py`) không được tự mở rộng quyền sửa qua spec F017.
Nếu cần sửa test cũ để hỗ trợ cutover embedding, báo rõ phạm vi và xin duyệt riêng.

Baseline phía trên mô tả trạng thái trước triển khai. Kết quả mới ở phần nghiệm thu bên dưới.


## Nghiệm thu triển khai 2026-10-30

Đã triển khai schema/API, snapshot backend/worker, hai owner và form chung,
smoke probe trả lời, lỗi embedding riêng trong chat/tìm kiếm và hướng dẫn vận hành.
Migration chỉ chạy trên PostgreSQL disposable; DB ứng dụng chưa được nâng cấp.
Tái sử dụng secret store, pinned transport, identity/admin lock, audit, CAS,
policy editor và i18n active. Legacy chỉ dùng ý tưởng cấu hình riêng/pending/probe
ở các đường dẫn đã ghi; không import runtime legacy.

- F017 backend: 22 pass, 0 fail, 0 skip. Có concurrency/CAS, rollback audit,
  ciphertext hỏng, no-key, SQL migration, upgrade/downgrade giữ revision/chunk có
  dữ liệu, process giữ snapshot cũ và đọc kết nối mới, worker nhiều batch/hai job.
- Full backend có Playwright/Edge: 371 test, 368 pass, 3 fail, 0 skip.
  Hai failure F015 do locator sai nhãn nút; đã sửa test và chạy lại riêng: 2 pass.
  Failure còn lại là `test_f004_001_chat_contract.py` đòi env fallback trái F016.
  Người dùng đã duyệt riêng sửa test này: test mới xác nhận LLM và embedding
  không fallback env; 2/2 test trong file pass, SSE giữ nguyên. Đang chạy lại
  full backend acceptance trên mã hiện tại.
- Frontend cuối có browser prerequisites: 118 test, 118 pass, 0 fail, 0 skip.
  Build/lint/format đã pass. Không coi skip là pass.
- Browser F017: 13 checks pass; F016: 13 checks pass; admin: 34 nhóm pass;
  auth: 64 checks pass; theme: 9 checks pass; frontend UX: 42 checks pass.
  F017 có keyboard, tooltip/Escape, ID riêng, collapse, draft độc lập,
  unsupported selection, probe/apply và sáu tổ hợp theme/locale.
- Workspace browser sau khi sửa mock contract và hết phiên: 29 checks pass.
  LLM toolbar/Enter sau cập nhật mock metadata và ID tab: 16 checks pass.
  Phần personal-provider trong script LLM cũ thuộc contract trước F016; không
  coi toàn bộ script đó là pass. Form tổ chức được kiểm chứng bằng browser F016
  và F017 riêng.
- Log và screenshot ở `logs/f017-*` bị ignore, không commit.

### Phạm vi production/configuration

- Migration 0013 và `models/embedding.py`, `models/__init__.py`: singleton rỗng,
  profile constraints, version và FK; không seed env/key hay đổi vector cũ.
- `contracts/embedding.py`, `services/embedding.py`, `api/embedding.py`: draft
  write-only → catalog/probe → CAS và audit nguyên tử; metadata không lộ secret.
- `adapters/embedding.py`: catalog riêng, vector hữu hạn, transport pinning,
  explicit proxy, TLS và reject redirect. `config.py`: bỏ env URL/key fallback.
- `main.py`, `dependencies.py`, `worker_cli.py`: lifecycle DB và resolver theo
  operation. `services/documents/ingestion.py`: resolve sau claim, snapshot mỗi job.
- `services/chat.py`, `api/chat.py`: policy trả lời trước embedding và lỗi riêng.
  `services/documents/retrieval.py`, `api/documents.py`: use case embed/retrieve
  trong service, giữ authorized retrieval và serialization HTTP trong route.
- `contracts/llm.py`, `services/llm.py`, `api/llm.py`: smoke probe câu cố định,
  không tài liệu/hội thoại, không đổi contract apply F016.
- `AiConnectionForm.svelte`: presentation chung, ID/toast/lifecycle riêng;
  `LlmConnectionForm.svelte`, `EmbeddingConnectionForm.svelte`: wrapper hai loại.
- `embedding-api.ts`, `embedding-state.svelte.ts`: client và draft owner độc lập,
  version/generation, unknown apply đọc metadata và không retry mutation.
  `EmbeddingModelSelector.svelte`: search/radio/dimension/warning/tooltip.
- `organization-llm-api.ts`, `organization-llm-state.svelte.ts`: smoke probe,
  suspend và unknown result. `SettingsPanel.svelte`: menu mở/thu, bàn phím.
  `WorkspacePage.svelte`: compose và dispose hai owner.
- `chat-api.ts`, `documents-api.ts`, `i18n/messages.ts` và ba locale vi/en/ru:
  lỗi an toàn theo bước, thông báo embedding riêng cho nhân viên.
- `.env.example`, `README.md`, `docs/database-setup.md`: cấu hình UI,
  encryption/proxy, backup/cutover/downgrade. `specs/02-architecture.md`: boundaries.

F017-008 đã hoàn tất sau lượt full backend acceptance cuối: 378 pass,
0 fail, 0 skip trong 854.376 giây. Test env cũ đã được người dùng duyệt riêng
và đổi theo contract F016/F017; SSE giữ nguyên. Các kết quả 371 test/3 failure
phía trên là lịch sử trước khi sửa test và được giữ để đối chiếu.

Lệnh full acceptance: `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py'`
với `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=tests;backend` và Playwright/Edge
đã cấu hình như README. Frontend: `npm --prefix frontend test` có 118 pass,
0 fail, 0 skip; build, lint, format:check và git diff --check đều pass.

Tổng kết browser hiện hành: F017 13 checks; F016 13 checks; workspace 29 checks;
LLM toolbar/Enter 16 checks; admin 34 nhóm; auth 64 checks; theme 9 checks;
frontend UX 42 checks. Phần personal-provider trong script LLM lịch sử chưa port,
được ghi là giới hạn kế thừa; không coi toàn bộ script lịch sử đó là pass.
Bộ F016/F017 độc lập kiểm chứng quản trị kết nối hiện hành.

DB ứng dụng chưa chạy migration và chưa commit thay đổi. Khi triển khai thực tế,
áp dụng quy trình backup/cutover trong docs/database-setup.md; cấu hình embedding
trên UI trước khi mở lại chat/ingestion. Không tự lấy key từ env.


### Cutover DB local theo yêu cầu người dùng

Đã backup DB ứng dụng và thử restore thành công vào DB tạm trước khi upgrade.
DB hiện ở `0013_org_embedding_settings`; singleton embedding version 0, chưa
cấu hình. Backup local bị ignore: `logs/f017-before-migration-985943a6.dump`.
Người dùng tự restart backend; cần cấu hình/verify/apply Model embedding trên UI.
Không nhập key từ env vào DB. Ghi nhận này thay thế trạng thái chưa migrate ở trên.
