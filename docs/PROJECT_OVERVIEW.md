# Tổng quan dự án

## Project này giải quyết vấn đề gì?

Project này là một self-hosted AI workspace dựa trên Open WebUI. Code hiện tại cung cấp một giao diện web để người dùng nói chuyện với các model AI, kết nối Ollama/OpenAI-compatible APIs, quản lý model tuỳ biến, upload file, tạo knowledge base cho RAG, dùng tool/function/skill, làm việc với notes, channels, calendar và automations.

Bằng chứng chính:

* `README.md` mô tả Open WebUI là "self-hosted AI platform" hỗ trợ Ollama, OpenAI-compatible APIs, RAG, plugins, models/agents, notes, channels, calendar, automations.
* `backend/ruvie/main.py` tạo FastAPI app và đăng ký các router cho `auths`, `users`, `chats`, `models`, `knowledge`, `files`, `tools`, `skills`, `functions`, `channels`, `calendar`, `automations`.
* `src/routes/(app)/+page.svelte` render `src/lib/components/chat/Chat.svelte` làm màn hình app chính.

## Người dùng chính

* End user: đăng nhập, chat với AI, upload/gắn file, dùng knowledge, notes, channels, calendar, automations.
* Admin: quản lý users/groups/roles, cấu hình auth, model connections, web search, documents, code execution, tools/functions và analytics. UI nằm trong `src/routes/(app)/admin/*` và backend dùng `get_admin_user` trong nhiều router.
* Builder/power user: tạo model wrapper, prompt, tool, skill, function, knowledge base trong workspace routes `src/routes/(app)/workspace/*`.
* Operator/self-host maintainer: cài đặt env, database, storage, vector DB, Redis/WebSocket, Docker/dev server qua `pyproject.toml`, `package.json`, `backend/start.sh`, `backend/start_windows.bat`, `docker-compose*.yaml`.

## Chức năng chính

* Auth và user access: signup/signin/signout, LDAP/OAuth/trusted headers, API key, admin config trong `backend/ruvie/routers/auths.py`, user/group management trong `backend/ruvie/routers/users.py` và `backend/ruvie/routers/groups.py`.
* Chat AI: UI tại `src/lib/components/chat/Chat.svelte`, message input tại `src/lib/components/chat/MessageInput.svelte`, chat CRUD tại `backend/ruvie/routers/chats.py`, completion endpoint tại `backend/ruvie/main.py`.
* Model registry và connections: frontend API `src/lib/apis/models/index.ts`, backend `backend/ruvie/routers/models.py`, provider proxy `backend/ruvie/routers/openai.py`, `backend/ruvie/routers/ollama.py`.
* Files và knowledge/RAG: upload/process files trong `backend/ruvie/routers/files.py`, knowledge CRUD/reindex/sync trong `backend/ruvie/routers/knowledge.py`, retrieval/vector logic trong `backend/ruvie/retrieval/*`.
* Tools, functions, skills: UI trong `src/lib/components/workspace/*` và `src/lib/components/admin/Functions*`, API trong `backend/ruvie/routers/tools.py`, `functions.py`, `skills.py`, execution helpers trong `backend/ruvie/utils/tools.py`, `backend/ruvie/functions.py`.
* Collaboration: channels và realtime messages trong `backend/ruvie/routers/channels.py`, socket app trong `backend/ruvie/socket/main.py`.
* Notes, calendar, automations: routers `notes.py`, `calendar.py`, `automations.py`; UI nằm dưới `src/routes/(app)/notes`, `src/routes/(app)/calendar`, `src/routes/(app)/automations`.
* Admin analytics/evaluations: routes `src/routes/(app)/admin/analytics`, `src/routes/(app)/admin/evaluations`; backend `analytics.py`, `evaluations.py`.

## Luồng hoạt động tổng quan

1. User mở web app. SvelteKit root `src/routes/+layout.svelte` khởi tạo i18n, socket.io, config, theme, pyodide worker và app state.
2. Nếu chưa có token/user, app điều hướng đến `src/routes/auth/+page.svelte`; frontend gọi `src/lib/apis/auths/index.ts` tới `backend/ruvie/routers/auths.py`.
3. Sau khi có session user, `src/routes/(app)/+layout.svelte` tải user settings, models, banners, tools, terminal/tool servers. Nếu role không phải `user`/`admin`, component `AccountPending.svelte` hiện overlay pending.
4. Main app render `src/lib/components/chat/Chat.svelte`. User chọn model, nhập prompt trong `MessageInput.svelte`, optionally attach files/knowledge/notes/chats/web pages.
5. Frontend tạo/cập nhật chat qua `src/lib/apis/chats/index.ts` và gửi completion đến backend endpoint `/api/chat/completions` trong `backend/ruvie/main.py`.
6. Backend `chat_completion` gọi `process_chat_payload` trong `backend/ruvie/utils/middleware.py` để nạp model, files, knowledge, tools, filters, permissions, metadata; sau đó forward request sang Ollama/OpenAI-compatible/provider pipeline.
7. Streaming/non-streaming response đi qua `process_chat_response`, tool calls, file outputs, citations, task/status events; frontend cập nhật message tree trong `Chat.svelte`.
8. Khi task chính hoàn tất, chat/messages/files được lưu vào database qua models như `backend/ruvie/models/chats.py`, `chat_messages.py`, `files.py`; UI cho phép share/archive/tag/pin/export/tiếp tục chat.

## Assumptions / Unknowns

* Sản phẩm hiển thị thương hiệu `Ruvie`; các tên package, URL upstream và định danh tương thích
  `open-webui` vẫn được giữ để tránh làm hỏng tích hợp. README tiếp tục ghi nhận nguồn gốc dự án
  dựa trên Open WebUI.
* Tài liệu này dựa trên source code hiện tại, không xác minh tất cả tính năng bằng end-to-end UI.
* Một số chức năng enterprise/production như SCIM, Redis multi-node, cloud storage, vector DB ngoài Chroma có code/config, nhưng chưa được chạy kiểm thử trong môi trường hiện tại.
