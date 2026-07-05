# Change Guide

## Them tinh nang moi nen sua o dau?

| Loai thay doi | Khu vuc thuong can sua |
|---|---|
| Them API/domain moi | `backend/ruvie/routers/<domain>.py`, `backend/ruvie/models/<domain>.py`, mount router trong `backend/ruvie/main.py`, frontend wrapper trong `src/lib/apis/<domain>/index.ts`. |
| Them man hinh frontend | `src/routes/(app)/...`, component trong `src/lib/components/...`, store neu la state cross-page trong `src/lib/stores/index.ts`. |
| Them chat behavior | `src/lib/components/chat/Chat.svelte`, `MessageInput.svelte`, backend `/api/chat/completions` trong `main.py`, `backend/ruvie/utils/middleware.py`. |
| Them model/provider setting | `backend/ruvie/config.py`, `routers/models.py` hoac provider router, admin settings UI under `src/lib/components/admin/Settings/*`. |
| Them RAG/file capability | `backend/ruvie/routers/files.py`, `knowledge.py`, `retrieval/*`, `utils/middleware.py`, frontend `apis/files`, `apis/knowledge`, workspace knowledge UI. |
| Them tool/function/skill | `routers/tools.py`/`functions.py`/`skills.py`, corresponding `models`, `utils/tools.py`/`functions.py`, UI in `src/lib/components/workspace` or `admin/Functions`. |
| Them admin setting | `backend/ruvie/config.py`, `routers/auths.py` or `configs.py`, admin settings component in `src/lib/components/admin/Settings/*`. |
| Them DB field/table | SQLAlchemy model in `backend/ruvie/models/*`, Alembic migration under `backend/ruvie/migrations/versions`, repository methods, API schema/models. |

## Patterns hien tai

- Frontend API wrappers: moi resource co file `src/lib/apis/<resource>/index.ts`, dung `fetch`, `WEBUI_API_BASE_URL`, `Authorization: Bearer`.
- Backend router pattern: `APIRouter`, Pydantic form/response models, FastAPI dependencies `get_current_user`, `get_verified_user`, `get_admin_user`, async DB session injection.
- Persistence pattern: SQLAlchemy table class + Pydantic model + singleton repository, vi du `Users = UsersTable()`, `Chats = ChatTable()`, `Models = ModelsTable()`.
- Config pattern: env defaults trong `env.py`/`config.py`, persisted runtime config qua `backend/ruvie/models/config.py`, admin update endpoints.
- Access-control pattern: role-based dependencies, group/user access grants via `models/access_grants.py` va `utils/access_control/*`.
- Chat pipeline pattern: frontend giu message tree/history, backend middleware enrich payload before provider call, response middleware streams results/events/files.
- Extensibility pattern: tools/functions/skills co valves/user valves, import/export, access grants, active/global toggles.

## Can can trong khi sua

- `backend/ruvie/utils/middleware.py`: rat trung tam va dai; thay doi o day co the anh huong chat, RAG, tools, files, streaming, citations.
- Auth/user bootstrap: `DEFAULT_USER_ROLE` default la `pending`; first-user admin logic trong `auths.py`; DB local tung co duplicate email va zero admin. Sua signup nen kem DB constraint/migration va test race/duplicate.
- `WEBUI_SECRET_KEY`: backend se fail khi `WEBUI_AUTH=True` ma secret rong neu start truc tiep uvicorn.
- Frontend dev `npm run dev`: co buoc `pyodide:fetch`, can network; trong moi truong offline nen dung direct Vite neu phu hop.
- Branding/logo: nen doi dong bo `static/static/*`, splash, favicon, login logo, sidebar logo va PWA manifest icons trong cung mot dot thay doi.
- Database migrations: model co the khai bao unique/columns nhung DB cu chua co constraint neu migration thieu. Kiem tra Alembic history truoc khi dua ra gia dinh.
- Storage deletion: `storage/provider.py` local/cloud delete co the xoa file thuc; can can than voi scripts/admin operations.
- Access grants: models/knowledge/chats/tools co sharing/access logic. Khi them resource shareable, nen dung pattern co san thay vi tu tao permission rieng.
- Socket/realtime: chat/channel/user activity co socket state; khi doi role/access, mot so code disconnect session de stale privileges khong con hieu luc.

## Technical debt / diem chua ro

- Chat middleware gom qua nhieu workflow trong mot file lon, kho test don vi va kho reasoning khi sua nho.
- Signup duplicate email/zero-admin da xay ra o local DB; can migration unique email va xu ly `IntegrityError` neu muon fix goc.
- README van la upstream Open WebUI va co encoding hien thi loi trong terminal Windows; chua co branding/tai lieu Ruvie rieng.
- `package.json` scripts dung `;` trong `npm run lint`, co the mang tinh shell-specific tren Windows.
- Pyodide preparation phu thuoc network va static cache; setup offline can tai lieu/asset strategy ro hon.
- Nhieu optional providers/vector DB/cloud storage co code support nhung kho biet cai nao duoc team dung that neu khong co env/deploy docs.

## Quy trinh de them feature an toan

1. Xac dinh domain da co router/model/UI nao gan nhat.
2. Them backend schema + repository method truoc, kem permission dependency phu hop.
3. Them API wrapper trong `src/lib/apis`.
4. Them UI theo component pattern hien co, tranh dua state global vao store neu chi dung cuc bo.
5. Neu cham DB schema, them Alembic migration va test tren DB co du lieu cu.
6. Neu cham chat pipeline, test it nhat: text chat, chat co file, streaming, tool/RAG neu lien quan.
7. Cap nhat docs trong `docs/` neu feature doi architecture/setup/use case.

## Assumptions / Unknowns

- Chua co test suite backend ro rang trong scripts doc duoc ngoai lint/format/deps; can xem them CI neu muon chuan hoa quality gate.
- Chua phan tich het Docker compose variants, nen production change guide chi noi muc source code.
- Cac enterprise flags/license behavior co the phu thuoc runtime license/config khong co trong local repo.
