# F006 - Kết nối LLM bằng URL và chọn model trong chat

**Trạng thái:** F006-001–006 đã hoàn thành. F006-007–008 chưa triển khai.

**Plan:** F006-003–004 và F006-005–006 đã được xác nhận làm chung
ngày 2026-10-07. F006-005–006 đã triển khai và kiểm tra đạt.

## Goal

Cho người dùng nhập URL LLM và chọn model trên giao diện, thay vì sửa
`LLM_MODEL` trong `.env` mỗi lần đổi model.

Base URL là địa chỉ gốc của dịch vụ, ví dụ `http://localhost:11434/v1`.
Dịch vụ cần hỗ trợ `/models` để lấy danh sách và `/chat/completions` để chat
(theo chuẩn OpenAI-compatible).

## User Story

Là người dùng đã đăng nhập, tôi muốn nhập URL LLM và chọn một model có sẵn,
để chat với model phù hợp mà không cần sửa cấu hình backend.

## Scope

### In

- Mỗi tài khoản có một kết nối riêng và chọn một model cho mỗi câu hỏi.
- Form kết nối có Base URL và API key tùy chọn. Dịch vụ cần key thì phải
  nhập key hợp lệ; dịch vụ không cần key thì chỉ nhập URL.
- Backend gọi `/models`, trả danh sách gồm `id` và `name` cho giao diện.
- Bộ chọn model có tìm kiếm, danh sách cuộn, dấu tick và nút tải lại.
- Lưu kết nối và model đã chọn trong PostgreSQL theo tài khoản.
- Dùng cấu hình `.env` khi chưa có kết nối riêng. Model/key LLM có thể
  trống; nếu chưa chọn model, dùng mặc định hợp lệ hoặc mục đầu danh sách.
- Chỉ lưu kết nối mới sau khi kiểm tra thành công. Gỡ kết nối riêng thì
  dùng cấu hình dự phòng; kết nối riêng bị lỗi thì báo lỗi, không tự đổi.
- Chat gửi `message` và `model_id`. Backend lấy URL/key từ cấu hình đã lưu
  và kiểm tra model trước khi tìm tài liệu hoặc gọi LLM.
- Giữ quyền đọc tài liệu, nguồn trích dẫn và embedding `1024` chiều/cosine.

**Code mẫu cần tham khảo:**

| Phần | File/hàm trong `references/` | Cách tận dụng |
|---|---|---|
| Form kết nối | `src/lib/components/chat/Settings/Connections.svelte`: `updateHandler`; `src/lib/components/AddConnectionModal.svelte`: `verifyOpenAIHandler`, `submitHandler` | Lấy cách nhập URL/key và hiển thị trạng thái kiểm tra. |
| Lấy model | `src/lib/apis/openai/index.ts`: `getOpenAIModelsDirect`, `verifyOpenAIConnection`; `backend/ruvie/routers/openai.py`: `get_models_request`, `get_models` | Lấy mẫu gọi `/models`; chuyển phần gọi dịch vụ sang backend active. |
| Dropdown | `src/lib/components/chat/ModelSelector/Selector.svelte`: `toggleOpen`, `handlePointerDown`, `handleKeydown`, `filteredItems` | Lấy bố cục, tìm kiếm, dấu tick và cách đóng; chỉnh cho Svelte 5. |
| Nối model vào chat | `backend/ruvie/routers/openai.py`: `generate_chat_completion` | Lấy cách kiểm tra model và chọn kết nối trước khi gọi LLM; chỉnh sang cấu hình theo tài khoản và quyền tài liệu active. |
| Nhớ lựa chọn | `src/lib/components/chat/ModelSelector.svelte`: `saveDefaultModel`, kiểm tra `selectedModels` | Kiểm tra model còn tồn tại và lưu một lựa chọn duy nhất. |

Các đường dẫn trong bảng nằm dưới `references/`. Dùng lại code active trước,
chỉ port phần legacy phù hợp và ghi file nguồn cùng phần đã chỉnh.
Theo xác nhận của chủ dự án, không cần kiểm tra license riêng cho code trong
`references/`. Không import hoặc chạy legacy trong ứng dụng active.

### Out

- Dấu `+`, chat nhiều model cùng lúc và nhiều kết nối riêng cho một tài khoản.
- Tabs phân loại, pin, tags, cài/xóa model hoặc nhập tên model bằng tay.
- API riêng của Azure, Anthropic hoặc Ollama không theo chuẩn trên.
- Đổi embedding, xử lý lại tài liệu, lưu lịch sử chat hoặc thêm tools.

## Flow

1. Đăng nhập và tải kết nối/model đã lưu; chưa có kết nối riêng thì dùng `.env`.
2. Nhập Base URL, key nếu cần và bấm **Kết nối**.
3. Backend kiểm tra URL và gọi `/models`. Thành công mới lưu cấu hình.
4. UI hiển thị model đã lưu hoặc mặc định hợp lệ trước khi gửi câu hỏi.
5. Người dùng chọn model; backend kiểm tra và lưu lựa chọn.
6. Gửi câu hỏi cùng `model_id`. Backend dùng đúng model đó và tài liệu đã
   được phép đọc, rồi trả từng phần câu trả lời cùng nguồn trích dẫn.
7. Reload vẫn giữ lựa chọn. Tải lại danh sách mà model đã mất thì yêu cầu
   chọn lại; gỡ kết nối riêng thì tải cấu hình dự phòng.

### Contract đã chốt — F006-001

Năm API kết nối/model đã triển khai; chat có `model_id` thuộc F006-005.
Tất cả API dùng tài khoản từ session; API ghi kiểm tra Origin và `X-CSRF-Token`.

| API | Input | Kết quả |
|---|---|---|
| `GET /llm/connection` | Session | URL, nguồn cấu hình, trạng thái key và model đã chọn. |
| `PUT /llm/connection` | `base_url`, `api_key` tùy chọn | Kiểm tra `/models`, rồi lưu kết nối và trả danh sách/model đã chọn. |
| `DELETE /llm/connection` | Session + CSRF | Trả `204`; UI tải lại cấu hình dự phòng và danh sách model. |
| `GET /models` | Session | Lấy danh sách mới từ kết nối hiện tại và trạng thái lựa chọn. |
| `PATCH /llm/connection/model` | `model_id` | Kiểm tra ID thuộc danh sách, lưu và trả `selected_model_id`. |
| `POST /chat` | `message`, `model_id` tùy chọn | Kiểm tra model trước retrieval; trả SSE theo contract hiện tại. |

Ví dụ đọc kết nối:

```json
{"source":"personal","base_url":"http://localhost:11434/v1","has_api_key":false,"selected_model_id":"model-a"}
```

`source` là `personal`, `server` hoặc `none`. Khi chưa có cấu hình, URL/model
là `null` và `has_api_key` là `false`. API không trả key.

Ví dụ lưu kết nối chỉ cần URL và kết quả danh sách:

```json
{"base_url":"http://localhost:11434/v1"}
```

```json
{"models":[{"id":"model-a","name":"Model A"}],"selected_model_id":"model-a","selection_required":false}
```

- **Chọn model:** khi kết nối mới, chọn mặc định hợp lệ hoặc model đầu tiên.
  Với cùng kết nối, giữ model đã lưu nếu còn tồn tại. Model đã mất thì trả
  `selected_model_id: null`, `selection_required: true` và yêu cầu chọn lại.
- **Key:** bỏ field thì giữ key cũ khi URL không đổi; chuỗi rỗng thì xóa key.
  Đổi URL không mang key cũ sang. Chỉ gửi Bearer header khi có key.
- **URL:** bỏ dấu `/` cuối. HTTPS public được phép; HTTP và địa chỉ local/LAN
  chỉ được phép qua `LLM_ALLOWED_LOCAL_ORIGINS` phía server, mặc định rỗng.
  Ví dụ origin được phép: `http://localhost:11434` (không gồm path `/v1`).
  `localhost` là máy chạy backend. Chặn URL có thông tin đăng nhập,
  metadata/link-local và đích bị cấm cả khi DNS thay đổi lúc kết nối.
  Không tự theo redirect; client không tự bật quyền.
- **Lỗi:** `401` cho hết phiên, `403` cho Origin/CSRF sai, `422` cho input/model
  không hợp lệ. Provider lỗi key, timeout, 429/5xx hoặc danh sách sai/rỗng trả
  `502` với thông báo an toàn. Không ghi đè kết nối/lựa chọn cũ khi xử lý lỗi.
- **Chat:** thiếu `model_id` thì dùng lựa chọn đã lưu hoặc mặc định hợp lệ;
  model đã mất phải chọn lại. Chốt URL/key/model riêng cho mỗi request, không
  sửa adapter dùng chung. Giữ `AuthorizedRetrievalService` và quyền tài liệu.

Phần triển khai tiếp theo dùng lại HTTP client/session/CSRF của active trước.
Adapter đảm nhiệm gọi provider; service kiểm tra và lưu cấu hình; route xử lý
HTTP/SSE. Frontend chỉ gửi URL/key ở API kết nối, gửi model ID ở API chat.
Code mẫu trong bảng được chỉnh theo contract này; không thêm dấu `+`.

### Plan chung F006-003–004

Làm adapter và service/API trong cùng đợt, giữ hai task để kiểm tra riêng.
Không thêm migration, lớp repository hoặc nối lựa chọn vào `/chat` ở đợt này.

- `GET /llm/connection` chỉ đọc cấu hình; `GET /models` lấy danh sách mới và
  trả trạng thái lựa chọn, không ghi database. Model đã mất thì trả ID `null`
  và `selection_required: true`; không tự chọn model khác thay cho lựa chọn cũ.
- `PUT` kiểm tra URL, key và `/models` thành công trước khi lưu. `PATCH` lấy
  danh sách mới, kiểm tra ID rồi lưu danh sách/lựa chọn trong một transaction.
  `DELETE` xóa bản ghi riêng/lựa chọn; UI tải lại cấu hình server.
- Dùng `UserLlmSettings` của F006-002, user ID từ session và Origin/CSRF active.
  Không nhận user ID, quyền hoặc cấu hình mạng từ body. Key bỏ field, rỗng hoặc
  đổi URL được xử lý theo contract đã chốt; response chỉ có `has_api_key`.
- Chuẩn hóa và kiểm tra URL ở service; adapter kiểm tra đích kết nối thực tế.
  Không dùng chung cookie provider giữa các user hoặc gửi cookie Ruvie đi.
  Không dùng proxy môi trường để bỏ qua quy tắc đích kết nối.
- Test HTTP giả cho adapter; test API/quyền, rollback và hai user trên
  PostgreSQL dùng một lần. Chạy toàn bộ backend suite trước khi tick task.

### Plan chung F006-005–006

Trước đợt này, chat dùng adapter chung. API kết nối/model đã có; frontend chưa có form.
Đợt này nối cấu hình riêng vào chat và thêm form. Không thêm migration.

- Chat lấy URL/key theo tài khoản, kiểm tra model rồi mới lấy tài liệu.
  Mỗi request giữ cấu hình đã lấy, kể cả khi tab khác sửa kết nối.
- Có `model_id` thì ưu tiên ID đó nếu hợp lệ. Thiếu ID thì dùng lựa chọn đã
  lưu hoặc mặc định hợp lệ. Lựa chọn đã mất thì yêu cầu chọn lại.
- Service trả `ChatStreamEvent`; API mã hóa SSE. Giữ tên/thứ tự event,
  quyền tài liệu và nguồn trích dẫn. Đóng session DB trước khi stream.
- Form nằm trên vùng hội thoại. Form gửi URL/key qua backend và hiển thị
  trạng thái kết nối/model hiện tại. Bộ chọn model thuộc F006-007.
- Tận dụng service/adapter, session và CSRF active. Form tham khảo
  `AddConnectionModal.svelte:verifyOpenAIHandler, submitHandler` và
  `Connections.svelte:updateHandler` trong bảng. Chỉ lấy xử lý URL, form
  và trạng thái; dùng cookie/CSRF active, không lấy token từ localStorage.
- Tham khảo `generate_chat_completion` để kiểm tra model/chọn kết nối.
  Dùng `AuthorizedRetrievalService` active cho quyền tài liệu.

## Edge Cases

- URL trống/sai: báo lỗi trước khi gọi dịch vụ. Bỏ dấu `/` cuối URL.
- Thiếu/sai key, timeout hoặc HTTP 429/5xx: dừng loading và cho thử lại;
  không hiển thị key hay lỗi gốc chứa thông tin nhạy cảm.
- Không có `/models`, JSON sai hoặc danh sách rỗng: giữ cấu hình cũ, báo lỗi.
- Model thiếu tên: dùng ID làm tên. Bỏ mục thiếu ID và gộp ID trùng.
- Model đã mất hoặc ID tự chế: từ chối trước khi tìm tài liệu/gọi LLM.
  Lưu lựa chọn thất bại thì giữ lựa chọn cũ.
- Đang chat: khóa sửa kết nối/chọn model ở UI; mỗi request giữ cấu hình lúc
  bắt đầu. Hai tài khoản hoặc nhiều tab không được lẫn URL/key/model.
- Đăng xuất/hết phiên: xóa state frontend và bỏ qua response từ phiên cũ.
- URL local: `localhost` là máy chạy backend. Backend phải kiểm tra đích
  kết nối, gồm DNS/redirect, và chặn địa chỉ metadata/link-local bị cấm.

## Acceptance Criteria

- [x] Plan đã được chủ dự án xác nhận trước khi sửa code ứng dụng.
- [ ] Nhập URL lấy được danh sách model; key chỉ bắt buộc khi dịch vụ yêu cầu.
- [ ] Backend hỗ trợ cấu hình LLM chỉ có URL, không bắt buộc model/key.
- [ ] Bộ chọn có tìm kiếm, dấu tick, loading/lỗi và thao tác bàn phím;
      không có dấu `+` hoặc gửi nhiều model cho một câu hỏi.
- [ ] Chọn model B thì request tới LLM gửi đúng B, không dùng model A cũ.
- [ ] Reload/đăng nhập lại giữ lựa chọn hợp lệ; hai tài khoản có cấu hình riêng.
- [ ] Kết nối mới lỗi không ghi đè cấu hình cũ; model mất phải chọn lại.
- [ ] API cấu hình kiểm tra phiên đăng nhập, Origin và CSRF; không trả key
      hoặc lưu key trong localStorage/log. Chat từ chối URL/key và scope tự khai.
- [ ] Đổi model vẫn giữ quyền tài liệu, nguồn trích dẫn và SSE contract hiện tại.
- [x] F006-005: model sai/mất bị từ chối trước embedding, retrieval và sinh
      câu trả lời. Đổi cấu hình ở tab khác không đổi request đang chạy.
- [x] F006-005: session DB đóng trước khi stream; service trả event có cấu trúc,
      API mã hóa SSE. Các test quyền tài liệu và thứ tự event vẫn đạt.
- [x] F006-006: key bỏ field giữ key riêng khi cùng URL; key rỗng xóa key.
      Đổi URL xóa key đang nhập và không mang key cũ sang.
- [x] F006-006: form chặn submit lặp và sửa kết nối khi đang chat.
      Đăng xuất/hết phiên xóa state và bỏ qua response của phiên cũ.
- [ ] Migration SQL, backend/frontend tests và frontend build đạt;
      có hướng dẫn README và ghi nhận phần code đã tận dụng.

## Tasks

Làm theo thứ tự F006-001 → F006-008 sau khi plan được xác nhận. Với chức năng
mới, viết test trước rồi thêm code. Chỉ tick task khi đã kiểm tra kết quả.
F006-003 và F006-004 được làm chung theo plan trên.

- [x] F006-001 Chốt cách làm và API.
  - Đọc code mẫu trong bảng; so với `App.svelte`, `chat-api.ts` và luồng
    chat backend. Ghi phần dùng lại, phần cần chỉnh và file nguồn.
  - Chốt ví dụ request/response cho `GET/PUT/DELETE /llm/connection`,
    `GET /models`, `PATCH /llm/connection/model` và chat có `model_id`.
  - Chốt URL local được phép và quy tắc key: bỏ field key thì giữ key cũ
    nếu URL không đổi; key rỗng thì xóa. URL mới dùng key mới nếu cần.
    Lỗi trả thông báo an toàn.
  - **Hoàn thành khi:** có contract rõ và chủ dự án xác nhận cách làm.

- [x] F006-002 Lưu cấu hình theo tài khoản.
  - Thêm model SQLAlchemy và migration mới cho URL/key riêng, danh sách
    model và lựa chọn. Mỗi `User.id` có tối đa một bản ghi.
  - Cho phép lưu lựa chọn khi dùng `.env`, không sao chép key server.
    Sửa `config.py` để model/key LLM tùy chọn; có model/key mà thiếu URL
    thì báo lỗi.
  - Test lưu/đọc hai tài khoản và cấu hình chỉ có URL. Kiểm tra SQL;
    chủ dự án tự áp dụng migration trên DB dev theo README.
  - **Hoàn thành khi:** cấu hình lưu riêng và tests/SQL đạt.

  - **Kết quả ngày 2026-10-07:** thêm `models/llm.py`, đăng ký model và migration
    `0008_user_llm_settings`; cho phép cấu hình LLM chỉ có URL. Dùng lại `Base`,
    session và cách viết migration active; tham khảo cách lưu theo user trong
    `references/backend/ruvie/models/users.py:update_user_settings_by_id`.
  - Unit test F006-002: 13 pass, gồm SQL upgrade/downgrade. Kiểm chứng
    PostgreSQL ngày 2026-10-07: 1 test pass, gồm lưu riêng A/B, constraint,
    rollback và migration round-trip trên database dùng một lần.
    Toàn bộ backend suite: 107 pass, 0 fail, 0 skip. Chưa áp dụng DB dev.

- [x] F006-003 Thêm chức năng lấy model trong adapter.
  - **Làm gì/ở đâu:** thêm `list_models()` trong `backend/ruvie/adapters/llm.py`.
    Gọi `{base_url}/models` bằng `httpx`, trả danh sách `{id, name}` cho service.
    Tận dụng `getOpenAIModelsDirect` và `get_models_request` trong bảng references.
  - Chỉ gửi Bearer header khi có key; đặt timeout, không theo redirect và kiểm
    tra đích thực tế. Không gửi cookie Ruvie hoặc lẫn cookie/key giữa các user.
  - Bỏ mục thiếu ID, gộp ID trùng; thiếu tên thì dùng ID. HTTP lỗi, JSON sai
    hoặc danh sách rỗng trả lỗi an toàn. Không đưa lỗi/key gốc ra frontend.
  - Giữ cấu hình riêng cho mỗi adapter/request, không sửa adapter chung.
    Test HTTP giả cho URL/header, timeout, response sai và stream model A/B.
  - **Hoàn thành khi:** lấy được danh sách chuẩn hóa; model/key không bị lẫn;
    tests adapter và backend suite đạt. Nối model vào chat ở F006-005.

  - **Kết quả ngày 2026-10-07:** `list_models()` chuẩn hóa ID/tên và trả lỗi
    an toàn. Adapter chỉ gửi Bearer khi có key, bỏ cookie, không theo redirect
    hoặc proxy môi trường. Transport kiểm tra IP rồi kết nối đúng IP đó, giữ
    Host/TLS SNI để chặn DNS đổi đích. Stream giữ model/key riêng và đóng response.
  - Tham khảo `references/src/lib/apis/openai/index.ts:getOpenAIModelsDirect`
    và `references/backend/ruvie/routers/openai.py:get_models_request`,
    `verify_connection`: dùng lại cách gọi `/models` và Bearer tùy chọn;
    chỉnh sang `httpx`, chuẩn hóa response và kiểm tra đích ở backend active.
    Không import runtime legacy. Test chung F006-003/004: 20 pass.

- [x] F006-004 Thêm service/API kết nối và lựa chọn.
  - **Làm gì/ở đâu:** tạo `backend/ruvie/contracts/llm.py` cho request/response,
    `backend/ruvie/services/llm.py` cho đọc/kiểm tra/lưu cấu hình và
    `backend/ruvie/api/llm.py` cho HTTP. Đăng ký router trong `main.py`.
  - Dùng session lấy user; đọc `UserLlmSettings` hoặc `.env`. Thêm danh sách
    `LLM_ALLOWED_LOCAL_ORIGINS` trong `config.py`; client không sửa danh sách này.
  - Thêm đủ năm API theo contract. GET chỉ đọc; PUT/PATCH kiểm tra provider
    trước khi ghi; DELETE trở về cấu hình server. Dùng transaction để giữ dữ
    liệu cũ khi ghi lỗi. Model đã mất yêu cầu chọn lại, không tự đổi dịch vụ.
  - Dùng `api/security.py` cho Origin/CSRF. Request từ chối field ngoài contract;
    response chỉ có `has_api_key`, không có key. Test quy tắc key và lỗi an toàn.
  - **Hoàn thành khi:** năm API đúng contract; hai tài khoản không đọc/sửa lẫn
    cấu hình; tests quyền/URL/rollback, PostgreSQL và backend suite đạt.

  - **Kết quả ngày 2026-10-07:** thêm contracts, `LlmConnectionService` và
    năm API; đăng ký router, đọc `LLM_ALLOWED_LOCAL_ORIGINS` từ server.
    Dùng lại session, `UserLlmSettings` và Origin/CSRF active, không thêm repository.
    PUT/PATCH kiểm tra provider trước khi lưu; GET không ghi DB; DELETE xóa
    cấu hình riêng. Response không trả key; lỗi validation không lặp lại body.
  - Test PostgreSQL dùng một lần: 1 pass, kiểm tra hai tài khoản, header riêng,
    model mất, lỗi provider và rollback khi commit lỗi. Toàn bộ backend suite:
    128 pass, 0 fail, 0 skip. Không đổi schema hoặc áp dụng migration DB dev.
    Chưa nối lựa chọn vào `/chat` và chưa sửa frontend; thuộc F006-005–007.

- [x] F006-005 Nối model đã chọn vào chat.
  - **Ở đâu:** sửa `backend/ruvie/contracts/chat.py`, `services/llm.py`,
    `services/chat.py`, `api/chat.py` và wiring trong `main.py`.
    Các đường dẫn rút gọn ở đây đều nằm dưới `backend/ruvie/`.
  - **Làm gì:** thêm `model_id` tùy chọn vào `ChatRequest`. Thêm hàm service
    lấy cấu hình theo user và kiểm tra ID với danh sách model mới từ provider.
    Request chỉ có `message` dùng lựa chọn đã lưu hoặc mặc định hợp lệ.
    Lựa chọn đã mất phải chọn lại; chat không tự lưu lựa chọn mới.
  - Tạo adapter từ URL/key/model đã chốt cho request. Kiểm tra model trước
    embedding và retrieval. Đóng session DB trước khi stream.
  - Dùng lại `AuthorizedRetrievalService`. Service trả `ChatStreamEvent`;
    API mã hóa SSE, giữ tên/thứ tự event và thông báo lỗi an toàn hiện tại.
  - **Kiểm tra:** model A/B, hai user, cấu hình đổi giữa chừng, model sai/mất,
    provider lỗi trước/trong stream và session DB. Giữ test quyền/nguồn/SSE
    và từ chối URL/key/user ID/scope trong body chat.
  - **Hoàn thành khi:** LLM nhận đúng model; cấu hình không lẫn giữa user;
    các test trên và toàn bộ backend suite đạt.

  - **Kết quả ngày 2026-10-07:** `resolve_chat_adapter()` kiểm tra danh sách mới
    và tạo adapter riêng. `PreparedChat` giữ URL/key/model và tài liệu được phép
    đọc; session DB đóng trước stream. API mã hóa `ChatStreamEvent` thành SSE.
    Bỏ adapter chat dùng chung và dependency cũ; không đổi schema.
  - Dùng lại service/adapter active và `AuthorizedRetrievalService`. Tham khảo
    `references/backend/ruvie/routers/openai.py:generate_chat_completion` cho
    thứ tự kiểm tra model/chọn kết nối và session ngắn; chỉnh theo user active.
  - Tests model/snapshot: 8 pass. Tests quyền/SSE: 15 pass. Toàn bộ backend:
    137 pass, 0 fail, 0 skip. PostgreSQL/provider giả xác nhận hai user gửi đúng
    model/key riêng; model mất không gọi embedding hoặc sinh câu trả lời.

- [x] F006-006 Tạo form kết nối LLM.
  - **Ở đâu:** tạo `frontend/src/lib/components/LlmConnectionForm.svelte`
    và `frontend/src/lib/llm-api.ts`. Sửa `frontend/src/App.svelte`
    và cấu hình Vite để proxy `/llm`, `/models`.
  - **Làm gì:** đặt form trên vùng hội thoại. Thêm Base URL, key tùy chọn
    dạng password, Kết nối/Gỡ kết nối và thao tác **Xóa key đã lưu**.
    Hiển thị loading, thành công/lỗi và model hiện tại; chưa thêm dropdown.
  - Không điền lại key đã lưu. Key trống thông thường thì bỏ field để giữ
    key riêng khi cùng URL. **Xóa key đã lưu** gửi `api_key: ""`.
    Đổi URL thì xóa key đang nhập; không sao chép key server.
  - API client dùng cookie cùng origin và CSRF active. Sau đăng nhập/reload,
    tải kết nối và model. Sau gỡ kết nối, tải lại cấu hình dự phòng.
  - Chặn submit lặp và sửa kết nối khi chat. Đăng xuất/hết phiên xóa state;
    bỏ qua response thuộc phiên cũ. Lỗi kết nối giữ dữ liệu đã lưu trước đó.
  - **Kiểm tra:** test payload key bỏ field/rỗng, URL đổi, cookie/CSRF,
    response `204` và lỗi API. Kiểm tra form, loading, khóa khi chat,
    logout/hết phiên, response cũ, bàn phím và màn hình nhỏ.
  - **Hoàn thành khi:** nhập URL lấy được model qua backend; reload giữ
    cấu hình hợp lệ; frontend tests/build và kiểm tra form đạt.

  - **Kết quả ngày 2026-10-07:** thêm form, API client và Vite proxy. Form nằm
    trên hội thoại, không điền lại key; có thao tác giữ/xóa key và gỡ kết nối.
    Khóa khi chat; xóa state và bỏ qua response phiên cũ, gồm tải lại project.
    Chỉnh CSS mobile để không tràn ngang và giữ vùng hội thoại đọc được.
  - Tận dụng cookie/CSRF active. Tham khảo `AddConnectionModal.svelte` và
    `Connections.svelte` trong bảng cho form URL/key, loading và phản hồi;
    chỉnh sang Svelte 5/backend active, không dùng token legacy/localStorage.
  - Frontend: 15 tests pass, 0 fail, 0 skip; build đạt. `tests/llm-browser.mjs`
    kiểm tra 10 nhóm hành vi trên Edge ẩn với API giả: tải ban đầu, URL/key,
    reload, lỗi, khóa thao tác, mobile/bàn phím, gỡ kết nối và logout/hết phiên.
    Cách chạy được ghi trong README. Bộ chọn model vẫn thuộc F006-007.

- [ ] F006-007 Tạo bộ chọn model.
  - Tham khảo legacy `ModelSelector/Selector.svelte`; tạo bộ chọn một model
    có tìm theo tên/ID, danh sách cuộn, dấu tick và nút tải lại, không có `+`.
  - Hỗ trợ lên/xuống, Enter chọn, Escape/click ngoài đóng và trả focus.
    Hiển thị rõ trạng thái loading, lỗi, không có kết quả; dùng được trên mobile.
  - Tải/lưu lựa chọn qua API và gửi `model_id` cùng câu hỏi. Khóa chọn khi
    chat; test đổi model, reload, lỗi lưu và model đã mất.
  - **Hoàn thành khi:** đổi model trên UI và câu hỏi sau dùng đúng model đó.

- [ ] F006-008 Kiểm tra toàn luồng và viết hướng dẫn.
  - Test đăng nhập → kết nối → chọn B → chat có nguồn → reload vẫn chọn B.
    Dùng DB test/dịch vụ giả; thêm lỗi key, timeout, model mất và hai user.
  - Chạy backend/frontend tests theo README, frontend build và kiểm tra
    SQL migration. Ghi kết quả và kiểm tra nào chưa chạy được.
  - Cập nhật README tiếng Anh, `.env.example` và ghi phần code đã tận dụng.
    Hướng dẫn URL/key, `localhost`, cấu hình dự phòng và kiểm tra thủ công.
  - **Hoàn thành khi:** toàn luồng được kiểm chứng và hướng dẫn đủ để chạy.
