# F019 - Lịch sử hội thoại

Ngày lập: 2026-10-31.
Trạng thái: Spec đã xác nhận phạm vi; chưa triển khai.
Liên quan: [F020 - Context hội thoại nhiều lượt](F020-multi-turn-chat-context.md).
Tên bảng, module, API và mã lỗi mới dưới đây là đề xuất triển khai.
Các task và tiêu chí nghiệm thu chưa được đánh dấu hoàn thành.

## Goal

Người dùng Ruvie Agent có thể quay lại cuộc trò chuyện của mình sau khi tải lại
trang, đăng nhập lại hoặc dùng trình duyệt khác. Hệ thống lưu câu hỏi, câu trả lời,
thứ tự trao đổi, model đã dùng và trích dẫn nguồn trong PostgreSQL.
Người dùng tạo chat mới, mở lại, tiếp tục gửi câu hỏi, đổi tên và xóa hội thoại.

Một hội thoại là chuỗi các lượt trao đổi của một chủ sở hữu. Một lượt trao đổi gồm
một câu hỏi và câu trả lời tương ứng. Một lần sinh là một lần gọi model để trả lời
lượt đó, kể cả khi người dùng chọn thử lại.
F019 lưu chuỗi trao đổi để hiển thị. F020 sẽ dùng chuỗi đó làm context cho model.

### Code currently does

| Nguồn active đã kiểm tra | Hành vi hiện tại | Khoảng cách |
| --- | --- | --- |
| `frontend/src/lib/features/chat/chat-state.svelte.ts::createChatState` | Giữ `turns` trong bộ nhớ; `reset` xóa nội dung; `stop` hủy request trình duyệt; `retry` thay câu trả lời của lượt cũ | Chưa có lưu server, ID bền vững hoặc khôi phục sau tải lại |
| `frontend/src/lib/features/chat/chat-turn.ts::ChatTurn` | Có câu hỏi, câu trả lời, model, trích dẫn và trạng thái | ID là số đếm tại trình duyệt; chưa có thời gian hay định danh lần sinh |
| `frontend/src/lib/features/chat/chat-api.ts::streamChat` | Gửi `{message, model_id?}` tới `POST /chat`; đọc SSE | Chưa truyền hội thoại hoặc mã chống gửi trùng |
| `backend/ruvie/api/chat.py::chat`, `contracts/chat.py::ChatRequest` | Xác thực session; nhận một câu hỏi; trả SSE | Chưa có API lịch sử hoặc lưu tin nhắn |
| `backend/ruvie/services/chat.py::ChatService.prepare`, `stream` | Resolve model phía server, lấy context qua `AuthorizedRetrievalService`, sinh các event `delta`, `citations`, `completed`, `error` | Mỗi câu hỏi độc lập; chưa lưu kết quả hoặc vòng đời lần sinh |
| `frontend/src/lib/layout/AppSidebar.svelte` | Có mục hội thoại nhưng chỉ hiện thông báo trống; menu dẫn đến view `history` | Chưa có danh sách hội thoại thật |
| `frontend/src/lib/pages/WorkspacePage.svelte` | Compose state chat và sidebar; tạo chat mới bằng reset | Cần điều phối lựa chọn hội thoại và URL |

### Spec requires

- PostgreSQL là nguồn dữ liệu lịch sử duy nhất. Không dùng browser storage làm bản lưu chính.
- Mọi thao tác hội thoại kiểm tra chủ sở hữu từ session ở backend.
- Admin hệ thống cũng không có quyền đọc hoặc sửa hội thoại của người khác.
- Mở lịch sử không gọi LLM hoặc embedding và không phụ thuộc provider đang hoạt động.
- Kiểm tra quyền đọc tài liệu trước khi trả nội dung lịch sử có nguồn tài liệu.
- Cấu hình provider, API key và endpoint tiếp tục chỉ do server quản lý.

### Proposed implementation và nguồn tái sử dụng

- Giữ `ChatService` phụ trách model, retrieval và prompt. Bổ sung service lịch sử
  để quản lý lưu trữ và vòng đời; API chỉ kiểm tra HTTP và encode kết quả.
- Giữ `ChatConversation.svelte`, `AnswerContent.svelte`, `CitationSources.svelte`,
  `ChatComposer.svelte` và cách chọn model hiện tại. Mở rộng state chat hiện có.
- Thêm component danh sách trong feature chat; `AppSidebar` nhận nội dung và callback
  từ page. Layout không gọi API và không sở hữu state lịch sử.
- Legacy đã đối chiếu: `references/backend/ruvie/models/chats.py::Chat`,
  `ChatTable.get_chat_title_id_list_by_user_id`, `get_chat_by_id_and_user_id`,
  `delete_chat_by_id_and_user_id`; `references/backend/ruvie/routers/chats.py::get_chat_by_id`,
  `delete_chat_by_id`; `references/src/lib/components/layout/Sidebar/ChatItem.svelte`.
- Kế thừa hành vi danh sách theo người dùng, chọn dòng hiện tại, đổi tên và xác nhận
  xóa. Thích nghi với Svelte 5/Vite, service active và session/CSRF hiện tại.
- Không port JSON hội thoại tùy ý do client ghi đè, admin đọc chat người khác,
  chia sẻ, Redis, SvelteKit stores hoặc giả định SQLite. Không import hay chạy legacy.
- Dùng bảng quan hệ và migration Alembic mới sau head hiện hành; không sửa migration đã áp dụng.

## User Story

- Là người dùng, tôi muốn xem các hội thoại của mình để tìm lại cuộc trao đổi trước.
- Là người dùng, tôi muốn tải lại trang hoặc đăng nhập lại mà vẫn đọc được chat đã lưu.
- Là người dùng, tôi muốn tiếp tục gửi câu hỏi trong chat cũ để giữ các trao đổi cùng chỗ.
- Là người dùng, tôi muốn đổi tên chat để nhận biết nội dung và xóa chat khi không cần giữ.
- Là người dùng, tôi muốn biết câu trả lời đã hoàn thành, bị dừng hay gặp lỗi trước khi thử lại.

## Scope

### In

- Lưu hội thoại riêng theo tài khoản; tạo ở lần gửi câu hỏi đầu tiên.
- Danh sách theo hoạt động gần nhất, phân trang, trạng thái tải/trống/lỗi và tải lại.
- Mở hội thoại theo URL; hỗ trợ tải lại trang và Back/Forward của trình duyệt.
- Lưu thứ tự lượt, câu hỏi, nội dung trả lời, model thực tế, thời gian, trạng thái và nguồn.
- Tiếp tục gửi câu hỏi, dừng và thử lại trong hội thoại đã lưu.
- Đổi tên; xóa toàn bộ hội thoại sau xác nhận. Không xóa từng tin nhắn trong đợt này.
- Tên tự động lấy từ câu hỏi đầu tiên. Không gọi model để đặt tên.
- Quyền sở hữu, kiểm tra lại quyền nguồn, chống gửi trùng và xung đột nhiều tab.
- UI desktop theo thiết kế hiện tại; đầy đủ vi-VN, en-US và ru-RU.

### Out

- Dùng lịch sử làm prompt, diễn giải câu hỏi nối tiếp, tóm tắt hoặc giới hạn context: F020.
- Tìm kiếm lịch sử, ghim, thư mục, tag, lưu trữ, xuất/nhập hoặc chia sẻ hội thoại.
- Phân nhánh, chỉnh sửa câu hỏi cũ hoặc so sánh nhiều câu trả lời.
- Chạy sinh nền để tiếp tục sau khi mất kết nối; nối lại SSE từ vị trí cũ.
- Đồng bộ trực tiếp giữa các tab bằng WebSocket hoặc dịch vụ hàng đợi mới.
- Đọc hội thoại người khác qua trang admin; chuyển dữ liệu từ legacy hoặc browser cũ.
- Thay cấu hình AI, chính sách model, pipeline ingestion hoặc quyền tài liệu hiện hành.

### Dữ liệu và quy tắc lưu

Các tên sau là đề xuất, cần chốt trong task dữ liệu:

| Bảng | Trường và ràng buộc chính |
| --- | --- |
| `chat_conversations` | UUID, `owner_user_id`, `title`, `created_at`, `updated_at`, `version`; index theo owner, updated time và ID |
| `chat_turns` | UUID, conversation ID, số thứ tự duy nhất trong hội thoại, câu hỏi, thời điểm tạo; câu hỏi không thay khi thử lại |
| `chat_generation_attempts` | UUID, turn ID, owner-scoped `request_id`, model ID, nội dung trả lời, trạng thái, mã lỗi an toàn, thời điểm bắt đầu/kết thúc, lease; unique request ID theo owner |
| `chat_attempt_sources` | Attempt ID, định danh document/revision/chunk và thứ tự nguồn; đủ provenance để kiểm tra quyền trước khi trả lời dở hoặc đầy đủ |

- Mỗi lượt chỉ có một lần sinh hiện hành để hiển thị; retry tạo attempt mới và thay
  lần sinh hiện hành, không thêm câu hỏi trùng. Các attempt cũ không có UI xem lại ở F019.
- Trạng thái lần sinh: `generating`, `completed`, `stopped`, `error`, `interrupted`.
  `loading` và `streaming` hiện tại là trạng thái trình bày của frontend.
- Một hội thoại có tối đa một lần sinh đang hoạt động. Khóa/constraint và transaction
  bảo vệ điều này giữa nhiều process/tab; không chỉ dựa vào biến `busy` ở browser.
- Lưu câu hỏi và attempt trước khi gọi provider. Gắn provenance sau retrieval và
  trước khi lưu hoặc gửi nội dung trả lời đầu tiên, kể cả khi chưa phát event citations.
- Server lưu các đoạn trả lời theo nhóm bằng transaction ngắn trước khi phát delta
  tương ứng. Không giữ transaction mở trong lúc chờ provider; không ghi mỗi token.
- Commit kết quả cuối và nguồn trước khi phát `completed`. Lỗi ghi DB không được
  báo hoàn thành. Sau lỗi, UI đọc lại server thay vì coi dữ liệu cục bộ là đã lưu.
- Attempt có lease hữu hạn và định danh để chặn cập nhật muộn. Thời hạn lease,
  cách gia hạn và timeout đọc provider phải được xác định trong task streaming.
  Provider timeout phải cho phép phát hiện mất tiến triển trước khi lease hết hạn.
- Khi đóng/mất kết nối, backend kết thúc stream khi phát hiện và cố lưu `interrupted`.
  Nếu process chết, lần đọc/gửi tiếp theo thu hồi lease hết hạn và chốt `interrupted`.
  Không ghi đè attempt mới hoặc đổi một attempt đã hoàn thành thành lỗi.
- Retry không tự chạy khi mở lại chat. Người dùng chủ động thử lại bằng model còn
  được phép; khi model cũ bị gỡ, cung cấp lựa chọn model hiện tại như UI đang có.
- `updated_at` đổi khi nhận câu hỏi, retry hoặc đổi tên; không đổi khi chỉ đọc, dừng,
  tải danh sách hoặc nhận từng delta. Thứ tự danh sách: `updated_at DESC, id DESC`.
- Tên ban đầu: trim câu hỏi, gộp khoảng trắng và lấy tối đa 80 ký tự Unicode.
  Đổi tên nhận 1–120 ký tự sau trim; hiển thị dưới dạng text, không render HTML.
- Xóa vật lý hội thoại cùng lượt, attempt và liên kết nguồn trong một transaction.
  Không xóa tài liệu, revision hay audit. Thời hạn giữ trong backup theo vận hành DB.

### Contract API đề xuất

Tất cả endpoint dùng session hiện hành; không nhận `owner_user_id` từ client.
Các response lịch sử dùng `Cache-Control: no-store`. Thao tác ghi dùng Origin/CSRF
theo cơ chế active; cập nhật cả client `/chat` nếu chưa gửi CSRF.

| Endpoint | Input chính | Kết quả |
| --- | --- | --- |
| `GET /conversations?limit=30&cursor=...` | Limit 1–100; cursor mờ | Metadata của chính người dùng, `next_cursor`; không trả nội dung tin nhắn |
| `GET /conversations/{id}?limit=50&before=...` | Limit 1–100; cursor lượt | Metadata, trang lượt mới nhất theo thứ tự tăng dần, cursor tải lượt cũ |
| `PATCH /conversations/{id}` | `{title, expected_version}` | Metadata đã cập nhật; 409 nếu version cũ |
| `DELETE /conversations/{id}` | Không nhận nội dung chat | 204 sau commit; 409 nếu đang có attempt hoạt động |
| `POST /chat` | `{message, model_id?, conversation_id?, request_id}` | Lưu lượt mới, rồi trả SSE; thiếu conversation ID thì tạo chat trong cùng transaction |
| `POST /conversations/{id}/turns/{turn_id}/retry` | `{request_id, model_id?}` | Tạo attempt cho câu hỏi đã lưu; không nhận nội dung câu hỏi thay thế; trả SSE |
| `POST /conversations/{id}/turns/{turn_id}/stop` | `{attempt_id}` | Kết quả trạng thái bền vững; chỉ dừng attempt tương ứng |

- `request_id` là UUID do client tạo cho một thao tác gửi/retry. Trùng ID và cùng
  payload trả 409 `request_already_recorded` kèm ID tài nguyên thuộc chính người dùng
  để client đọc lại; không gọi provider lần nữa. Trùng ID khác payload trả 409
  `request_conflict`. Kiểm tra quyền trước khi trả metadata lỗi.
- Lỗi xác thực/validation/ownership/DB lúc nhận request trả HTTP trước khi mở SSE.
  Lỗi model trước khi nhận lượt không tạo chat trống. Lỗi embedding/provider sau khi
  đã nhận lượt được lưu vào attempt rồi phát SSE `error` an toàn.
- Bổ sung event `accepted` đầu stream với `conversation_id`, `turn_id`, `attempt_id`
  sau commit. Giữ ý nghĩa `delta`, `citations`, `completed`, `error`; cập nhật parser
  và regression tương ứng. Hoàn tất SSE chỉ có ý nghĩa thành công sau durable commit.
- 401 khi session không hợp lệ. 404 giống nhau khi không tồn tại hoặc không thuộc
  người dùng. 422 cho input không hợp lệ/model không còn được phép. 409 cho version,
  request hoặc generation conflict. 503 `history_unavailable` khi DB không khả dụng.
- Cursor phải được kiểm tra định dạng; không dùng cursor làm quyền truy cập. Query
  luôn lọc owner. Chỉ trả trường công khai, không kèm khóa, endpoint, prompt nội bộ,
  nội dung exception, URI blob hoặc nội dung nguồn chưa được phép đọc.
- Stop là thao tác server có kiểm tra attempt ID. Hủy fetch chỉ đóng browser stream,
  không chứng minh server đã lưu trạng thái dừng. Stop lặp không thay terminal state;
  nếu completed đã commit trước thì giữ completed. Generator kiểm tra trạng thái
  khi ghi để loại bỏ delta muộn. Đóng provider stream khi có thể; không hứa hủy phí
  provider đã phát sinh.

### Quyền tài liệu khi đọc lịch sử

- Owner check không thay thế quyền nguồn. Service dùng readable-document predicate
  từ DB trước khi serialize câu trả lời hoặc metadata citation.
- Với attempt đã dùng nguồn tài liệu: nếu bất kỳ document nào không còn đọc được
  hoặc nguồn không thể xác minh, trả nội dung assistant rỗng, citations rỗng và
  `content_unavailable: true`. UI hiện thông báo nguồn không còn khả dụng; không
  render, copy hoặc đưa câu trả lời cũ vào context. Áp dụng cả câu trả lời dở.
- Giữ câu hỏi do người dùng viết, thứ tự và trạng thái. Không trả tên, ID hoặc lý do
  chi tiết của tài liệu bị chặn. Không sửa/xóa nội dung gốc trong DB chỉ vì quyền đổi.
- Câu trả lời không dùng tài liệu vẫn đọc được theo quyền sở hữu hội thoại.
- Không lấy snapshot citations làm bằng chứng quyền. Re-upload không thay citation
  sang revision mới; khi vẫn đủ quyền, hiển thị đúng revision/chunk đã dùng.
- Việc thu hồi quyền có hiệu lực ở lần đọc server tiếp theo; không hứa thu hồi
  nội dung người dùng đã nhận hoặc sao chép. Không thêm cơ chế push thu hồi ở F019.

## Flow

1. Sau đăng nhập, page tải danh sách hội thoại của người dùng. Khi chưa có hội thoại,
   sidebar hiện trạng thái trống. Lỗi tải hiện thông báo và nút thử lại.
2. Người dùng chọn “Chat mới”. Frontend tạo màn hình trống, chưa tạo bản ghi DB.
   Draft chưa gửi không được lưu lâu dài; không tạo chat trống khi tải lại trang.
3. Khi gửi câu hỏi đầu tiên, client tạo request ID. Server kiểm tra session, CSRF,
   input và model; tạo hội thoại, lượt và attempt trong transaction.
4. Client nhận `accepted`, cập nhật URL bằng ID server và thêm chat vào sidebar.
   URL đề xuất: `?conversation=<uuid>` trong view chat; giữ các query khác cần thiết.
5. Service retrieval kiểm tra quyền, lưu provenance rồi stream và lưu trả lời.
   UI chỉ coi câu trả lời hoàn thành khi nhận `completed` sau commit.
6. Khi chọn hội thoại cũ hoặc tải lại URL, frontend đọc từ DB. UI tải lượt gần nhất,
   cho tải thêm lượt cũ và giữ vị trí đọc. Không sinh lại câu trả lời khi mở lịch sử.
7. Nếu attempt vẫn hoạt động ở kết nối khác, UI hiện trạng thái đang xử lý, khóa gửi
   và cho làm mới/dừng. Không gắn lại SSE hoặc tự tạo một attempt thay thế.
8. Người dùng gửi câu hỏi mới trong chat cũ. Backend thêm lượt theo thứ tự. Trong
   F019, retrieval/prompt chỉ dùng câu hỏi mới và tài liệu được phép như hiện tại.
   Lịch sử hiển thị không được hiểu là model đã nhận context nhiều lượt.
9. Người dùng đổi tên từ menu chat. Client gửi version; thành công cập nhật sidebar.
   Xung đột yêu cầu tải lại tên hiện hành trước khi thử lại, không âm thầm ghi đè.
10. Người dùng xóa chat từ menu và xác nhận bằng dialog có tên hội thoại. Sau 204,
    sidebar bỏ dòng đó; nếu đang mở chat bị xóa thì chuyển sang chat mới trống.
    Nếu thao tác thất bại, giữ chat và báo lỗi; không báo xóa thành công sớm.

### Tương tác desktop

- Dòng sidebar hiển thị tên, trạng thái được chọn và menu đổi tên/xóa. Tên dài
  được rút gọn bằng CSS; tên đầy đủ vẫn có trong accessible name/tooltip.
- Sidebar và view `history` dùng chung owner/API danh sách; view `history` cung cấp
  danh sách và tải thêm, không trở thành một bản state riêng.
- Khi đang stream, chọn chat khác hoặc “Chat mới” yêu cầu xác nhận dừng trước khi
  chuyển; hủy dialog giữ nguyên chat. Logout vẫn thực hiện được và hủy request cục bộ.
- Khi nhiều request đọc chồng nhau, chỉ kết quả thuộc lựa chọn/account hiện tại
  được cập nhật UI. Dọn state và abort khi logout/unmount; không rò chat sang account mới.
- Menu và dialog dùng component active, hỗ trợ bàn phím, label và focus trả về
  control phù hợp. Không thay design system hoặc tạo layout dành riêng mobile.
- Dùng thông báo bản địa hóa cho nguồn không còn khả dụng, lỗi tải, lỗi ghi, conflict
  và attempt gián đoạn; không hiển thị raw error từ backend/provider.

## Edge Cases

- Gửi hai lần hoặc mất response `accepted`: retry cùng request ID để đọc lại tài
  nguyên đã nhận; không tạo chat/câu hỏi thứ hai và không gọi model hai lần.
- Hai tab gửi vào cùng chat: chỉ một attempt được nhận; tab còn lại nhận 409 và tải
  lại dữ liệu. Hai chat khác nhau không bị khóa chung ở backend.
- Provider hoặc embedding lỗi: giữ câu hỏi, attempt lỗi và phần trả lời đã lưu nếu
  có; nguồn vẫn chịu kiểm tra quyền. Mở lịch sử được dù provider tiếp tục lỗi.
- Mất kết nối giữa chừng: giữ nội dung đã commit; lượt hiển thị gián đoạn sau khi
  server chốt hoặc thu hồi lease. Phần buffer chưa commit không được hứa khôi phục.
- Process chết sau commit trước event: đọc lại DB khôi phục terminal state đúng,
  không tự retry. Process chết giữa chừng không để hội thoại bị khóa vô thời hạn.
- Stop đua với completed/retry: so attempt ID và terminal state; kết quả đã chốt
  không bị sự kiện muộn ghi đè. Retry tạo attempt mới sau khi attempt cũ terminal.
- DB lỗi trước khi nhận lượt: không gọi provider. DB lỗi giữa stream: không phát
  completed; frontend báo chưa xác nhận lưu và cho đọc lại, không tự gửi lại câu hỏi.
- Chat bị xóa ở tab khác: lần đọc/gửi sau trả 404; UI báo không còn khả dụng và
  chuyển sang chat mới. Không tạo lại chat cùng ID hoặc ghi lại sau khi đã xóa.
- Đổi model/chính sách tổ chức: lịch sử vẫn hiển thị model cũ như metadata; gửi/retry
  kiểm tra chính sách hiện hành. Không tự đổi model trong một attempt đang chạy.
- Thu hồi quyền nguồn hoặc xóa nguồn: chặn nội dung assistant như quy tắc trên.
  Không làm mất các câu hỏi và lượt khác còn được phép đọc.
- Danh sách đổi khi đang phân trang: merge theo ID để tránh dòng trùng; refresh lấy
  thứ tự hiện hành. Cursor không cam kết snapshot trong suốt phiên duyệt.
- Hội thoại dài: API phân trang theo lượt; không tải toàn bộ lịch sử khi chỉ mở
  sidebar. F019 không gửi toàn bộ lịch sử sang LLM.
- Session hết hạn: xóa dữ liệu chat khỏi UI và chuyển theo luồng auth hiện hành.
  Draft chưa gửi không tự phục hồi sang một account khác.

## Acceptance Criteria

- [ ] AC-01: “Chat mới” chưa gửi không tạo bản ghi; lần gửi hợp lệ đầu tiên tạo đúng một hội thoại, lượt và attempt thuộc session user.
- [ ] AC-02: Tải lại, đăng nhập lại và trình duyệt khác hiển thị cùng lịch sử đã commit theo đúng thứ tự, model, trạng thái và citations khi còn quyền.
- [ ] AC-03: Sidebar và view history chỉ liệt kê chat của chủ sở hữu, sắp xếp ổn định và tải thêm không tạo dòng trùng.
- [ ] AC-04: URL trực tiếp và Back/Forward mở đúng chat; response chậm của chat/account cũ không ghi đè lựa chọn mới.
- [ ] AC-05: Tên đầu tiên được tạo từ câu hỏi mà không gọi LLM; đổi tên hợp lệ được lưu; tên rỗng/quá dài và version cũ bị từ chối theo contract.
- [ ] AC-06: Xóa phải xác nhận; commit xóa toàn bộ dữ liệu chat liên quan, giữ tài liệu; lỗi xóa giữ chat trên UI; chat đang sinh bị từ chối xóa.
- [ ] AC-07: User khác và admin khác đều nhận 404 khi đọc, sửa, xóa, gửi, retry hoặc stop bằng ID không thuộc mình; giả owner/cursor không vượt quyền.
- [ ] AC-08: Request ghi thiếu/sai CSRF hoặc Origin bị từ chối; session không hợp lệ nhận 401; lịch sử không có provider secret, URI blob hoặc raw exception.
- [ ] AC-09: Completed chỉ phát sau commit; câu trả lời dở được lưu theo nhóm; lỗi DB không bị hiển thị như đã lưu thành công.
- [ ] AC-10: Gửi/retry cùng request ID không tạo trùng hoặc gọi provider lần nữa; cùng ID khác payload trả conflict.
- [ ] AC-11: Hai tab không tạo hai attempt hoạt động trong cùng chat; stop/retry/delta muộn không ghi đè attempt hoặc terminal state khác.
- [ ] AC-12: Dừng, mất SSE và process chết dẫn tới trạng thái terminal hoặc được thu hồi sau lease; không treo generating vô thời hạn; retry không nhân đôi câu hỏi.
- [ ] AC-13: Thu hồi quyền một nguồn chặn toàn bộ nội dung assistant và citation metadata của attempt liên quan trước serialization, kể cả câu trả lời dở; lượt độc lập còn quyền vẫn đọc được.
- [ ] AC-14: Provider/model cũ không hoạt động vẫn mở lịch sử được; gửi/retry kiểm tra model và quyền tài liệu hiện hành.
- [ ] AC-15: Câu hỏi mới trong chat cũ được lưu cùng hội thoại nhưng prompt F019 không nhận các lượt trước; kiểm thử adapter xác nhận ranh giới với F020.
- [ ] AC-16: Vi-VN/en-US/ru-RU và theme hiện có hiển thị đủ trạng thái; đổi tên/xóa/tải thêm dùng được bằng bàn phím và dialog phục hồi focus.
- [ ] AC-17: Migration mới áp dụng trên PostgreSQL/pgvector disposable, có FK/index/unique và rollback hợp lệ; migration cũ và DB ứng dụng không bị sửa để chạy test.

## Tasks

- [ ] **F019-001 — Dữ liệu hội thoại và migration**
  - **Work:** Chốt schema/ID, thứ tự lượt, attempt hiện hành, owner-scoped request ID,
    version, lease và cascade; thêm model và migration sau head hiện hành.
  - **Where:** Đề xuất `backend/ruvie/models/chat.py`, migration mới trong
    `backend/migrations/versions/`; cập nhật `backend/ruvie/models/__init__.py`.
  - **Done:** AC-17; test constraint/order/cascade trên DB disposable, kiểm tra SQL
    upgrade/downgrade và dữ liệu account/tài liệu không bị thay đổi.

- [ ] **F019-002 — Service lịch sử, quyền sở hữu và quyền nguồn**
  - **Work:** Implement list/detail phân trang, rename/version và delete; kiểm tra
    ownership trước mọi truy cập; dùng readable-document predicate để che assistant
    và citations không còn quyền trước serialization; batch kiểm tra nguồn mỗi trang.
  - **Where:** Đề xuất `backend/ruvie/services/conversations.py`,
    `backend/ruvie/contracts/conversations.py`; tái sử dụng
    `backend/ruvie/services/access.py` và model/citation active.
  - **Done:** AC-03, 05–07, 13; integration test chéo owner/admin, thu hồi grant,
    membership, nguồn mất, nhiều nguồn trong một attempt, revision và pagination.

- [ ] **F019-003 — Lưu vòng đời sinh và chống gửi trùng**
  - **Work:** Nhận câu hỏi/attempt nguyên tử, giữ một generation hoạt động; bổ sung
    provenance trước output; lưu delta theo nhóm và terminal state; retry/stop;
    lease expiry và attempt fencing. Chốt kích thước/thời gian buffer, lease và
    provider timeout bằng test với fake provider có điều khiển thời gian.
  - **Where:** `backend/ruvie/services/chat.py`, service conversations đề xuất,
    `backend/ruvie/contracts/chat.py`; chỉ điều chỉnh adapter nếu cần timeout/close.
  - **Done:** AC-01, 09–12, 14–15; test duplicate request, DB fault, disconnect,
    process abandonment, stop-vs-completed và hai transaction gửi đồng thời.
    Không giữ DB transaction trong lúc đợi provider.

- [ ] **F019-004 — API lịch sử và SSE có định danh**
  - **Work:** Expose contract đề xuất; thêm accepted event, endpoint retry/stop,
    error mapping, no-store và CSRF/Origin. Đăng ký router, giữ route mỏng;
    không nhận nội dung assistant/citations do client cung cấp.
  - **Where:** Đề xuất `backend/ruvie/api/conversations.py`; cập nhật
    `backend/ruvie/api/chat.py`, `backend/ruvie/main.py` và contracts liên quan.
  - **Done:** HTTP/SSE contract test cho tất cả endpoint, AC-07–10; lỗi trước SSE
    và lỗi sau accepted được phân biệt; response lỗi không lộ tài nguyên người khác.

- [ ] **F019-005 — Owner frontend và khôi phục hội thoại**
  - **Work:** Thêm API lịch sử, ID bền vững và trạng thái hydration; mở/tải lượt cũ;
    quản lý request ID, accepted, stop server, retry và reconciliation sau lỗi;
    bảo vệ response muộn và dọn state khi account đổi.
  - **Where:** Đề xuất `frontend/src/lib/features/chat/conversation-api.ts`,
    `conversation-state.svelte.ts`; cập nhật `chat-api.ts`, `chat-state.svelte.ts`,
    `chat-turn.ts` trong cùng feature. Page chỉ compose các owner.
  - **Done:** AC-02, 04, 09–12, 14; state test tải chồng nhau, duplicate/lost accepted,
    session hết hạn, model bị gỡ và nội dung nguồn bị che không tồn tại trong UI state.

- [ ] **F019-006 — Sidebar, URL và thao tác lịch sử**
  - **Work:** Render danh sách chung cho sidebar/history; selected row, tải thêm,
    rename/delete dialog và trạng thái rỗng/lỗi; tích hợp URL/Back/Forward, chat mới
    và xác nhận dừng trước khi chuyển. Hiển thị interrupted/content unavailable;
    giữ renderer, composer và thiết kế desktop hiện có.
  - **Where:** Đề xuất `frontend/src/lib/features/chat/ConversationList.svelte`,
    `ConversationHistory.svelte`; cập nhật `ChatConversation.svelte`,
    `frontend/src/lib/layout/AppSidebar.svelte`,
    `frontend/src/lib/pages/WorkspacePage.svelte` và ba catalog trong
    `frontend/src/lib/i18n/locales/`. Tái sử dụng dialog/menu active.
  - **Done:** AC-03–06, 13, 16; browser test chat mới → gửi → reload → mở lại →
    gửi tiếp → đổi tên → xóa, gồm bàn phím, theme và ba ngôn ngữ.

- [ ] **F019-007 — Nghiệm thu và regression**
  - **Work:** Thêm kiểm thử tích hợp và browser còn thiếu; cập nhật test `/chat`
    hiện tại theo contract mới; kiểm tra account isolation, citations, model/proxy
    và stop/retry. Chạy bộ kiểm tra theo README/AGENTS trên DB disposable, ghi số
    pass/fail/skip thực tế. Cập nhật spec sau khi có bằng chứng nghiệm thu.
  - **Where:** Đề xuất `tests/test_f019_chat_history.py`,
    `frontend/tests/f019-history-browser.mjs`, frontend state tests trong
    `frontend/tests/` và các chat regression hiện hành; file spec này.
  - **Done:** Đối chiếu toàn bộ AC-01–17; full backend suite, frontend tests,
    build/lint/format và browser prerequisites theo tài liệu. Skip không tính pass;
    không dùng provider thật hoặc reset DB ứng dụng. Chỉ tick task đã được kiểm chứng.
