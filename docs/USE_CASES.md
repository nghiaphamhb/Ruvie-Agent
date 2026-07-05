# Use Cases

## 1. Đăng ký / đăng nhập / chờ admin duyệt

* Actor: end user, admin.
* Precondition: backend đang chạy, `WEBUI_AUTH=True`, signup/login form được bật trong config.
* Main flow: user vào `src/routes/auth/+page.svelte`; frontend gọi `src/lib/apis/auths/index.ts`; backend xử lý trong `backend/ruvie/routers/auths.py`; session user được tải trong layout; nếu role là `pending`, `src/lib/components/layout/Overlay/AccountPending.svelte` hiện overlay; admin vào `src/routes/(app)/admin/users/[tab]/+page.svelte` và đổi role qua `EditUserModal.svelte`.
* Edge cases: first user được nâng lên `admin` trong `signup_handler`; user pending bị chặn ở authenticated layout; LDAP/OAuth/trusted-header có các đường auth riêng trong `auths.py` và `utils/oauth.py`; duplicate email/zero-admin là rủi ro đã thấy trong local DB hiện tại.
* Files liên quan: `src/lib/apis/auths/index.ts`, `src/routes/auth/+page.svelte`, `src/routes/(app)/+layout.svelte`, `src/lib/components/layout/Overlay/AccountPending.svelte`, `backend/ruvie/routers/auths.py`, `backend/ruvie/routers/users.py`, `backend/ruvie/models/users.py`, `backend/ruvie/models/auths.py`.
* Trạng thái: có code hỗ trợ.

## 2. Chat với một hoặc nhiều model

* Actor: verified user.
* Precondition: user role là `user` hoặc `admin`; ít nhất một model/base model khả dụng qua Ollama/OpenAI-compatible/provider config.
* Main flow: app render `Chat.svelte`; user chọn model trong model selector; nhập prompt trong `MessageInput.svelte`; frontend tạo/cập nhật chat qua `src/lib/apis/chats/index.ts`; request completion đến `backend/ruvie/main.py` endpoint `/api/chat/completions`; middleware xử lý payload và provider response; UI stream kết quả vào message tree.
* Edge cases: selected model rỗng; nhiều model tạo multi-response; queue message khi response đang active; model bị mất/toggle/offline; streaming bị lỗi; user pending không vào được layout chat.
* Files liên quan: `src/lib/components/chat/Chat.svelte`, `src/lib/components/chat/MessageInput.svelte`, `src/lib/apis/chats/index.ts`, `backend/ruvie/main.py`, `backend/ruvie/utils/middleware.py`, `backend/ruvie/routers/openai.py`, `backend/ruvie/routers/ollama.py`, `backend/ruvie/models/chats.py`, `backend/ruvie/models/chat_messages.py`.
* Trạng thái: có code hỗ trợ.

## 3. Upload file và dùng file trong chat

* Actor: verified user.
* Precondition: user có permission upload file; storage provider được cấu hình; file type/size nằm trong policy.
* Main flow: `MessageInput.svelte` upload file qua `src/lib/apis/files/index.ts`; backend `backend/ruvie/routers/files.py` lưu file qua `storage/provider.py`, tạo record `models/files.py`, optionally process content; chat payload gắn file metadata; `utils/middleware.py` đưa file/attached context vào request model.
* Edge cases: file rỗng, file đang upload, vượt max count, file không đọc được, storage cloud lỗi, process status pending/failed, image file cần convert thành image_url parts.
* Files liên quan: `src/lib/components/chat/MessageInput.svelte`, `src/lib/apis/files/index.ts`, `backend/ruvie/routers/files.py`, `backend/ruvie/models/files.py`, `backend/ruvie/storage/provider.py`, `backend/ruvie/utils/files.py`, `backend/ruvie/utils/middleware.py`.
* Trạng thái: có code hỗ trợ.

## 4. Tạo và dùng Knowledge Base / RAG

* Actor: verified user/admin tuỳ access grant.
* Precondition: embedding/retrieval config hợp lệ; vector DB có sẵn; file đã upload hoặc external knowledge source được cấu hình.
* Main flow: user vào workspace knowledge routes; frontend gọi `src/lib/apis/knowledge/index.ts`; backend `routers/knowledge.py` tạo knowledge, thêm file, reindex/sync, quản lý directory/access; retrieval/vector modules embed và truy vấn; khi chat gắn knowledge/files, `utils/middleware.py` đưa sources/citations vào prompt/response.
* Edge cases: external source config sai; file pending/processing; reindex thất bại; user không có access; vector DB ngoài Chroma cần env riêng; full-context mode khác search mode.
* Files liên quan: `src/routes/(app)/workspace/knowledge/*`, `src/lib/components/workspace/Knowledge*.svelte`, `src/lib/apis/knowledge/index.ts`, `backend/ruvie/routers/knowledge.py`, `backend/ruvie/models/knowledge.py`, `backend/ruvie/retrieval/*`, `backend/ruvie/retrieval/vector/*`, `backend/ruvie/utils/middleware.py`.
* Trạng thái: có code hỗ trợ.

## 5. Quản lý model wrapper / agent-like model

* Actor: admin hoặc user có quyền workspace.
* Precondition: base models/providers đã cấu hình; user có permission tạo/sửa model.
* Main flow: user vào `workspace/models`; frontend gọi `src/lib/apis/models/index.ts`; backend `routers/models.py` tạo model record, tags, access grants, knowledge/tools/skills defaults; chat selector dùng danh sách models từ store.
* Edge cases: model id không hợp lệ; base model không còn tồn tại; access grant sai; model có knowledge/file user không được đọc.
* Files liên quan: `src/routes/(app)/workspace/models/*`, `src/lib/components/workspace/Models*.svelte`, `src/lib/apis/models/index.ts`, `backend/ruvie/routers/models.py`, `backend/ruvie/models/models.py`, `backend/ruvie/utils/access_control/*`.
* Trạng thái: có code hỗ trợ.

## 6. Tools / Functions / Skills

* Actor: admin, builder/power user, verified user khi dùng trong chat.
* Precondition: tool/function/skill được tạo/import và user có access.
* Main flow: workspace/admin UI tạo tool/function/skill; frontend APIs gọi `tools`, `functions`, `skills`; backend lưu definition; chat middleware nạp danh sách tool/function, apply valves/user valves, thực thi tool calls và trả kết quả vào stream.
* Edge cases: code/function không hợp lệ; valves schema sai; tool server OpenAPI/MCP không kết nối; permission/access grants chặn user; tool result có file/image phải convert thành display files.
* Files liên quan: `src/lib/components/workspace/Tools*`, `Skills*`, `src/lib/components/admin/Functions*`, `src/lib/apis/tools/index.ts`, `src/lib/apis/functions/index.ts`, `src/lib/apis/skills/index.ts`, `backend/ruvie/routers/tools.py`, `functions.py`, `skills.py`, `backend/ruvie/utils/tools.py`, `backend/ruvie/functions.py`, `backend/ruvie/models/tools.py`, `functions.py`, `skills.py`.
* Trạng thái: có code hỗ trợ.

## 7. Channels / team messages

* Actor: verified user, channel members, model mentions.
* Precondition: user có access channel/group/member; socket app đang chạy.
* Main flow: user tạo/vào channel; frontend `src/lib/apis/channels/index.ts` gọi `backend/ruvie/routers/channels.py`; messages, threads, reactions, pins, webhooks được lưu qua `models/channels.py` và `models/messages.py`; socket events cập nhật realtime.
* Edge cases: private channel access denied; inactive member; webhook token sai; model response handler trong channel lỗi; thread/reaction target không tồn tại.
* Files liên quan: `src/routes/(app)/channels/[id]/+page.svelte`, `src/lib/components/channel/*`, `src/lib/apis/channels/index.ts`, `backend/ruvie/routers/channels.py`, `backend/ruvie/models/channels.py`, `backend/ruvie/models/messages.py`, `backend/ruvie/socket/main.py`.
* Trạng thái: có code hỗ trợ.

## 8. Calendar và automations

* Actor: verified user.
* Precondition: user có permission calendar/automation; model để automation run được chọn; schedule hợp lệ.
* Main flow: calendar UI gọi `src/lib/apis/calendar/index.ts`; backend `routers/calendar.py` CRUD calendars/events/attendees/RSVP/search; automation UI gọi `src/lib/apis/automations/index.ts`; backend `routers/automations.py` tạo schedule, toggle, run, xem runs; models `calendar.py`, `automations.py` lưu state.
* Edge cases: RRULE/schedule sai; automation limit; timezone; event attendee status; model không available khi automation run.
* Files liên quan: `src/routes/(app)/calendar/+page.svelte`, `src/lib/components/calendar/*`, `src/routes/(app)/automations/*`, `src/lib/components/automations/*`, `backend/ruvie/routers/calendar.py`, `backend/ruvie/routers/automations.py`, `backend/ruvie/models/calendar.py`, `backend/ruvie/models/automations.py`.
* Trạng thái: có code hỗ trợ.

## 9. Admin configuration, analytics, evaluations

* Actor: admin.
* Precondition: user role `admin`.
* Main flow: admin vào `src/routes/(app)/admin/*`; cấu hình auth, models, connections, web search, audio, documents, code execution; APIs đi qua `src/lib/apis/auths`, `configs`, `analytics`, `evaluations`; backend routers cập nhật persisted config và trả analytics/evaluation data.
* Edge cases: invalid env/config, API key bị thiếu, LDAP/OAuth config sai, analytics router có điều kiện license/flag trong `main.py`.
* Files liên quan: `src/lib/components/admin/*`, `src/routes/(app)/admin/*`, `backend/ruvie/routers/auths.py`, `configs.py`, `analytics.py`, `evaluations.py`, `backend/ruvie/models/config.py`.
* Trạng thái: có code hỗ trợ; một số analytics/license behavior chưa được xác minh end-to-end.

## Assumptions / Unknowns

* "Use case chính" được chọn theo route/API/module hiện có và README, không phải theo product roadmap riêng của Ruvie.
* Không tất cả edge cases được test thực tế; chúng được suy ra từ code paths, guards, và config.
* Use case terminal/code execution có nhiều UI/API (`terminals.py`, `XTerminal.svelte`, `FileNav`) nhưng chưa được mô tả thành use case riêng vì cần thêm thông tin về deployment terminal server.
