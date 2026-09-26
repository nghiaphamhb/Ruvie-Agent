# F004 - Basic Chat MVP

## Goal
Cho phép người dùng gửi câu hỏi trong chat UI tối giản và nhận câu trả lời
được tạo từ authorized document context, stream trực tiếp từ backend kèm
citations ổn định.

## User Story
As an authenticated project user, I want to ask a technical question and see
a streamed answer with its sources, so that I can get help grounded in
documents I am allowed to read.

## Scope
### In
- Thay frontend placeholder bằng chat UI tối giản: nhập câu hỏi, hiển thị
  trạng thái đang trả lời, token stream, lỗi và citations.
- Tạo chat endpoint nhận câu hỏi; identity chỉ lấy từ trusted backend
  authentication seam (`request.state.domain_user_id`), không nhận user ID,
  project ID, document IDs hoặc ACL scope từ client.
- Tạo query embedding bằng adapter server-side tương thích với embedding
  profile đã pin ở F003; không cho client chọn model/profile.
- Dùng F003 retrieval để lấy chunks từ ready revisions trong authorized scope;
  dựng prompt/context chỉ từ kết quả đã được F002/F003 cho phép.
- Gọi LLM qua OpenAI-compatible endpoint với base URL, model và API key cấu
  hình server-side. Không forward secrets hoặc dữ liệu unauthorized.
- Stream answer qua Server-Sent Events; gửi citations có provenance F003 cùng
  trong stream response và kết thúc bằng event hoàn tất. Lỗi upstream trả
  contract an toàn, không trả credentials hay nội dung ngoài scope.
- Dùng hội thoại tạm ở frontend; không lưu chats/messages vào database trong
  F004. Mỗi request backend nhận một câu hỏi độc lập.
- Ghi nhận trong tasks việc rà soát và khép các acceptance criteria còn bỏ
  ngỏ của F001–F003.

### Out
- Đăng nhập, đăng ký, cấp phát identity hoặc UI/session management. F004 dùng
  trusted identity do integration phía backend cung cấp và fail-closed nếu
  thiếu identity.
- Lưu, liệt kê, đồng bộ hoặc chia sẻ lịch sử chat.
- Skills, tools, compatibility lookup, ticket workflow, web search,
  personalization nâng cao, reranking và hybrid search.
- Upload UI hoặc thay đổi ingestion pipeline.
- Cho LLM tự quyết định authorization, cấp quyền, hoặc truy cập trực tiếp
  database/vector store.

## Architecture Decisions
- Active backend là authority cho identity, authorization, retrieval, prompt
  context và LLM provider. Frontend không gửi trusted context hoặc citations
  để backend tin cậy.
- Tham khảo flow và SSE forwarding ở
  `references/backend/ruvie/routers/openai.py`, chat client ở
  `references/src/lib/apis/chats/`, chat page/components trong
  `references/src/routes/(app)/` và retrieval/citation flow ở
  `references/backend/ruvie/routers/retrieval.py`. Chỉ kế thừa các mẫu
  request/stream/UI phù hợp; không import hoặc chạy legacy source.
- Authorized retrieval phải hoàn tất trước khi tạo prompt. Chỉ chunk text và
  citation từ `PgvectorChunkRepository` với `AuthorizedScope.for_user()` được
  đưa vào LLM context. Nếu retrieval rỗng, LLM nhận câu hỏi mà không có tài
  liệu nguồn; UI không hiển thị citation giả.
- Provider/model/key/base URL là cấu hình server-side. Client không thể gửi
  model override, provider credentials, context, ACL filter hoặc authorized
  scope.
- Stream giữ một response envelope duy nhất: answer deltas, danh sách
  citations, trạng thái completed; lỗi dùng event/contract an toàn. Citation
  giữ nguyên ID và provenance do F003 tạo, không phụ thuộc thứ tự stream.
- Mỗi request là một lượt độc lập, không có chat persistence hoặc replay; UI
  có thể giữ nội dung trong memory đến khi reload.

## Flow
1. Người dùng nhập câu hỏi ở chat UI; frontend gửi câu hỏi tới backend.
2. Backend resolve domain user từ trusted identity seam; request thiếu identity
   bị từ chối.
3. Backend embed câu hỏi qua adapter tương thích embedding profile đã cấu hình,
   dựng authorized scope từ user và retrieve các chunks sẵn sàng bằng F003.
4. Backend dựng prompt chỉ từ câu hỏi và authorized chunks; citations lấy từ
   cùng retrieval hits.
5. Backend gọi OpenAI-compatible LLM bằng cấu hình server-side và stream answer
   deltas cùng citations tới frontend.
6. Frontend cập nhật câu trả lời theo stream, hiển thị citations và trạng thái
   hoàn tất; lỗi được hiển thị mà không lộ thông tin nhạy cảm.

## Chat HTTP/SSE Contract
- `POST /chat` nhận JSON `{ "message": string }`. `message` được trim và phải
  không rỗng; request có trường ngoài `message` bị từ chối. Identity không
  nằm trong request body.
- Response thành công có `Content-Type: text/event-stream`. Mỗi SSE frame có
  `event` và JSON trong `data` theo một trong bốn dạng:
  `delta` với `{ "text": string }`; `citations` với
  `{ "citations": Citation[] }`; `completed` với `{}`; hoặc `error` với
  `{ "code": "provider_unavailable" | "generation_failed", "message": string }`.
- Các event `delta` có thể lặp lại. Backend gửi tối đa một `citations` event,
  sau đó một `completed` event khi thành công; khi lỗi trong quá trình stream,
  gửi một `error` event rồi kết thúc response. `Citation` giữ contract F003.
- Request không hợp lệ trả HTTP `422`; thiếu trusted identity trả HTTP `401`.
  Cấu hình provider thiếu hoặc upstream không sẵn sàng dùng SSE `error` với
  thông điệp an toàn, không trả API key, base URL hoặc raw upstream body.

## Acceptance Criteria
- [ ] Chat UI cho phép nhập câu hỏi, gửi request, hiển thị streaming answer,
      citations và trạng thái lỗi/hoàn tất.
- [ ] Backend chat endpoint chỉ nhận prompt từ client và lấy actor từ trusted
      identity; thiếu identity trả unauthorized, không có fallback identity
      dựa trên client input.
- [ ] Query embedding và LLM provider được cấu hình phía server; client không
      thể override model, API key, embedding profile, ACL scope, project hoặc
      document IDs.
- [ ] Chat orchestration dùng F002/F003 authorization trước retrieval/context;
      chunks không được phép không xuất hiện trong prompt, answer context,
      citations hoặc response.
- [ ] LLM nhận câu hỏi cùng authorized chunks; không có chunks phù hợp thì
      request vẫn xử lý mà không tạo citations không có nguồn.
- [ ] Answer được stream qua SSE tới UI; completion/error kết thúc stream theo
      contract ổn định và lỗi upstream không tiết lộ secrets hoặc raw private
      resource details.
- [ ] Citations trong response/UI giữ `document_id`, `revision_id`, `chunk_id`,
      offsets, title và source hash từ F003; chỉ render citations của chunks đã
      authorize.
- [ ] Không có chat/message persistence, Skills, tool execution hoặc ticket
      side effect trong request path F004.
- [ ] Tests bao gồm provider/embedding adapters giả, stream success/error,
      identity fail-closed, authorized context/citation và Project Alpha/Beta
      isolation; không gọi dịch vụ LLM/embedding bên ngoài.
- [ ] Các acceptance criteria F001–F003 đang bỏ ngỏ được đối chiếu với code,
      migration SQL, tests và (khi cần) PostgreSQL integration; spec cũ chỉ được
      cập nhật trạng thái sau khi có bằng chứng tương ứng.

## Tasks
- [x] F004-001 Chốt request/event/error contract cho chat SSE và cấu hình
      OpenAI-compatible provider phía server.
- [ ] F004-002 Implement query embedding adapter server-side theo pinned F003
      embedding profile và cấu hình/factory LLM adapter; cung cấp fake adapters
      cho tests.
- [ ] F004-003 Implement chat orchestration: trusted identity, authorized
      retrieval, context/prompt assembly, citation preservation và streaming
      answer; không thêm tool/skill/persistence path.
- [ ] F004-004 Thêm minimal chat UI/API client cho submit, SSE parsing,
      incremental rendering, citations, loading và error state.
- [ ] F004-005 Viết tests cho stream protocol, provider failures, authorization
      isolation, client-scope injection và citation provenance.
- [ ] F004-006 Rà soát bảy AC chưa đánh dấu hoàn tất ở F001–F003: F001 migration
      trên PostgreSQL trống; F002 migration và audit allow/deny; F003 migration,
      upload authorization/private blob/revision/job, worker ingestion/retry,
      upload/retrieval audit an toàn. Với từng AC, ghi rõ đã đáp ứng/chưa đáp
      ứng, evidence/test còn thiếu, và task/follow-up cụ thể; kiểm tra lại các
      AC đã có tests nhưng spec chưa được đánh dấu.
- [ ] F004-007 Chạy backend suite documented trong README và xác minh PostgreSQL
      migration SQL và coverage liên quan authorization/isolation; cập nhật
      README cho cấu hình LLM/chat và các integration seams.
