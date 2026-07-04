# Use Cases

## 1. Dang ky / dang nhap / cho admin duyet

- Actor: end user, admin.
- Precondition: backend dang chay, `WEBUI_AUTH=True`, signup/login form duoc bat trong config.
- Main flow: user vao `src/routes/auth/+page.svelte`; frontend goi `src/lib/apis/auths/index.ts`; backend xu ly trong `backend/open_webui/routers/auths.py`; session user duoc tai trong layout; neu role la `pending`, `src/lib/components/layout/Overlay/AccountPending.svelte` hien overlay; admin vao `src/routes/(app)/admin/users/[tab]/+page.svelte` va doi role qua `EditUserModal.svelte`.
- Edge cases: first user duoc nang len `admin` trong `signup_handler`; user pending bi chan o authenticated layout; LDAP/OAuth/trusted-header co cac duong auth rieng trong `auths.py` va `utils/oauth.py`; duplicate email/zero-admin la rui ro da thay trong local DB hien tai.
- Files lien quan: `src/lib/apis/auths/index.ts`, `src/routes/auth/+page.svelte`, `src/routes/(app)/+layout.svelte`, `src/lib/components/layout/Overlay/AccountPending.svelte`, `backend/open_webui/routers/auths.py`, `backend/open_webui/routers/users.py`, `backend/open_webui/models/users.py`, `backend/open_webui/models/auths.py`.
- Trang thai: co code ho tro.

## 2. Chat voi mot hoac nhieu model

- Actor: verified user.
- Precondition: user role la `user` hoac `admin`; it nhat mot model/base model kha dung qua Ollama/OpenAI-compatible/provider config.
- Main flow: app render `Chat.svelte`; user chon model trong model selector; nhap prompt trong `MessageInput.svelte`; frontend tao/cap nhat chat qua `src/lib/apis/chats/index.ts`; request completion den `backend/open_webui/main.py` endpoint `/api/chat/completions`; middleware xu ly payload va provider response; UI stream ket qua vao message tree.
- Edge cases: selected model rong; nhieu model tao multi-response; queue message khi response dang active; model bi mat/toggle/offline; streaming bi loi; user pending khong vao duoc layout chat.
- Files lien quan: `src/lib/components/chat/Chat.svelte`, `src/lib/components/chat/MessageInput.svelte`, `src/lib/apis/chats/index.ts`, `backend/open_webui/main.py`, `backend/open_webui/utils/middleware.py`, `backend/open_webui/routers/openai.py`, `backend/open_webui/routers/ollama.py`, `backend/open_webui/models/chats.py`, `backend/open_webui/models/chat_messages.py`.
- Trang thai: co code ho tro.

## 3. Upload file va dung file trong chat

- Actor: verified user.
- Precondition: user co permission upload file; storage provider duoc cau hinh; file type/size nam trong policy.
- Main flow: `MessageInput.svelte` upload file qua `src/lib/apis/files/index.ts`; backend `backend/open_webui/routers/files.py` luu file qua `storage/provider.py`, tao record `models/files.py`, optionally process content; chat payload gan file metadata; `utils/middleware.py` dua file/attached context vao request model.
- Edge cases: file rong, file dang upload, vuot max count, file khong doc duoc, storage cloud loi, process status pending/failed, image file can convert thanh image_url parts.
- Files lien quan: `src/lib/components/chat/MessageInput.svelte`, `src/lib/apis/files/index.ts`, `backend/open_webui/routers/files.py`, `backend/open_webui/models/files.py`, `backend/open_webui/storage/provider.py`, `backend/open_webui/utils/files.py`, `backend/open_webui/utils/middleware.py`.
- Trang thai: co code ho tro.

## 4. Tao va dung Knowledge Base / RAG

- Actor: verified user/admin tuy access grant.
- Precondition: embedding/retrieval config hop le; vector DB co san; file da upload hoac external knowledge source duoc cau hinh.
- Main flow: user vao workspace knowledge routes; frontend goi `src/lib/apis/knowledge/index.ts`; backend `routers/knowledge.py` tao knowledge, them file, reindex/sync, quan ly directory/access; retrieval/vector modules embed va truy van; khi chat gan knowledge/files, `utils/middleware.py` dua sources/citations vao prompt/response.
- Edge cases: external source config sai; file pending/processing; reindex that bai; user khong co access; vector DB ngoai Chroma can env rieng; full-context mode khac search mode.
- Files lien quan: `src/routes/(app)/workspace/knowledge/*`, `src/lib/components/workspace/Knowledge*.svelte`, `src/lib/apis/knowledge/index.ts`, `backend/open_webui/routers/knowledge.py`, `backend/open_webui/models/knowledge.py`, `backend/open_webui/retrieval/*`, `backend/open_webui/retrieval/vector/*`, `backend/open_webui/utils/middleware.py`.
- Trang thai: co code ho tro.

## 5. Quan ly model wrapper / agent-like model

- Actor: admin hoac user co quyen workspace.
- Precondition: base models/providers da cau hinh; user co permission tao/sua model.
- Main flow: user vao `workspace/models`; frontend goi `src/lib/apis/models/index.ts`; backend `routers/models.py` tao model record, tags, access grants, knowledge/tools/skills defaults; chat selector dung danh sach models tu store.
- Edge cases: model id khong hop le; base model khong con ton tai; access grant sai; model co knowledge/file user khong duoc doc.
- Files lien quan: `src/routes/(app)/workspace/models/*`, `src/lib/components/workspace/Models*.svelte`, `src/lib/apis/models/index.ts`, `backend/open_webui/routers/models.py`, `backend/open_webui/models/models.py`, `backend/open_webui/utils/access_control/*`.
- Trang thai: co code ho tro.

## 6. Tools / Functions / Skills

- Actor: admin, builder/power user, verified user khi dung trong chat.
- Precondition: tool/function/skill duoc tao/import va user co access.
- Main flow: workspace/admin UI tao tool/function/skill; frontend APIs goi `tools`, `functions`, `skills`; backend luu definition; chat middleware nap danh sach tool/function, apply valves/user valves, thuc thi tool calls va tra ket qua vao stream.
- Edge cases: code/function khong hop le; valves schema sai; tool server OpenAPI/MCP khong ket noi; permission/access grants chan user; tool result co file/image phai convert thanh display files.
- Files lien quan: `src/lib/components/workspace/Tools*`, `Skills*`, `src/lib/components/admin/Functions*`, `src/lib/apis/tools/index.ts`, `src/lib/apis/functions/index.ts`, `src/lib/apis/skills/index.ts`, `backend/open_webui/routers/tools.py`, `functions.py`, `skills.py`, `backend/open_webui/utils/tools.py`, `backend/open_webui/functions.py`, `backend/open_webui/models/tools.py`, `functions.py`, `skills.py`.
- Trang thai: co code ho tro.

## 7. Channels / team messages

- Actor: verified user, channel members, model mentions.
- Precondition: user co access channel/group/member; socket app dang chay.
- Main flow: user tao/vao channel; frontend `src/lib/apis/channels/index.ts` goi `backend/open_webui/routers/channels.py`; messages, threads, reactions, pins, webhooks duoc luu qua `models/channels.py` va `models/messages.py`; socket events cap nhat realtime.
- Edge cases: private channel access denied; inactive member; webhook token sai; model response handler trong channel loi; thread/reaction target khong ton tai.
- Files lien quan: `src/routes/(app)/channels/[id]/+page.svelte`, `src/lib/components/channel/*`, `src/lib/apis/channels/index.ts`, `backend/open_webui/routers/channels.py`, `backend/open_webui/models/channels.py`, `backend/open_webui/models/messages.py`, `backend/open_webui/socket/main.py`.
- Trang thai: co code ho tro.

## 8. Calendar va automations

- Actor: verified user.
- Precondition: user co permission calendar/automation; model de automation run duoc chon; schedule hop le.
- Main flow: calendar UI goi `src/lib/apis/calendar/index.ts`; backend `routers/calendar.py` CRUD calendars/events/attendees/RSVP/search; automation UI goi `src/lib/apis/automations/index.ts`; backend `routers/automations.py` tao schedule, toggle, run, xem runs; models `calendar.py`, `automations.py` luu state.
- Edge cases: RRULE/schedule sai; automation limit; timezone; event attendee status; model khong available khi automation run.
- Files lien quan: `src/routes/(app)/calendar/+page.svelte`, `src/lib/components/calendar/*`, `src/routes/(app)/automations/*`, `src/lib/components/automations/*`, `backend/open_webui/routers/calendar.py`, `backend/open_webui/routers/automations.py`, `backend/open_webui/models/calendar.py`, `backend/open_webui/models/automations.py`.
- Trang thai: co code ho tro.

## 9. Admin configuration, analytics, evaluations

- Actor: admin.
- Precondition: user role `admin`.
- Main flow: admin vao `src/routes/(app)/admin/*`; cau hinh auth, models, connections, web search, audio, documents, code execution; APIs di qua `src/lib/apis/auths`, `configs`, `analytics`, `evaluations`; backend routers cap nhat persisted config va tra analytics/evaluation data.
- Edge cases: invalid env/config, API key bi thieu, LDAP/OAuth config sai, analytics router co dieu kien license/flag trong `main.py`.
- Files lien quan: `src/lib/components/admin/*`, `src/routes/(app)/admin/*`, `backend/open_webui/routers/auths.py`, `configs.py`, `analytics.py`, `evaluations.py`, `backend/open_webui/models/config.py`.
- Trang thai: co code ho tro; mot so analytics/license behavior chua duoc xac minh end-to-end.

## Assumptions / Unknowns

- "Use case chinh" duoc chon theo route/API/module hien co va README, khong phai theo product roadmap rieng cua Ruvie.
- Khong tat ca edge cases duoc test thuc te; chung duoc suy ra tu code paths, guards, va config.
- Use case terminal/code execution co nhieu UI/API (`terminals.py`, `XTerminal.svelte`, `FileNav`) nhung chua duoc mo ta thanh use case rieng vi can them thong tin ve deployment terminal server.
