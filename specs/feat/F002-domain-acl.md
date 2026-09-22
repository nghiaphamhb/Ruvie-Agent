# F002 - Domain + ACL

## Goal
Xây dựng schema domain tối thiểu và lớp authorization cho active application,
để document luôn được giới hạn theo project trước khi retrieval trả dữ liệu cho
caller hoặc LLM context.

## User Story
As a project member, I want to retrieve only documents I am authorized to
read, so that documents from other projects do not leak into my results or
LLM context.

## Scope
### In
- Tạo schema PostgreSQL qua SQLAlchemy/Alembic cho `User`, `Role`, `Project`,
  `Membership`, `Document`, `AccessGrant` và `AuditEvent`.
- `Role` là vai trò domain toàn cục, với vocabulary ban đầu:
  `BIM_CAD_SPECIALIST`, `DEVELOPER`, `IT_SUPPORT`.
- `Membership` biểu diễn quan hệ user--project; user có thể là member của
  nhiều project.
- Mỗi `Document` thuộc chính xác một `Project`; document không có project là
  dữ liệu không hợp lệ.
- Định nghĩa policy `document:read`: default deny; cho phép khi user là member
  project và role được document cho phép, hoặc khi có `AccessGrant` đọc trực
  tiếp còn hiệu lực cho user.
- `AccessGrant` chỉ là ngoại lệ cụ thể cho principal `user`, permission
  `read`, và có thể cấp quyền cho user không phải member project. Nó không hỗ
  trợ wildcard/public grant, group grant, hay implicit admin bypass trong F002.
- Thêm service/repository authorization dùng chung để resolve tập document có
  thể đọc và để retrieve theo tập đó, thay vì retrieve trước rồi lọc kết quả.
- Ghi `AuditEvent` cho mọi quyết định allow hoặc deny của document retrieval,
  gồm actor, action, document/project mục tiêu, outcome và thời điểm.
- Viết test quan trọng nhất: user chỉ là member của Project Alpha không thể
  retrieve document thuộc Project Beta và document Beta không xuất hiện trong
  kết quả/context trả về.

### Out
- Đăng ký/đăng nhập, JWT, UI quản trị user/role/project, và API CRUD đầy đủ.
- Upload file, parsing/chunking, embeddings, vector store, RAG/chat UI, hoặc
  tool authorization.
- Groups, public sharing, role hierarchy, deny grants, permission write/delete,
  và admin bypass.
- Sao chép, import runtime, chạy hoặc deploy code từ `references/`.

## Architecture Decisions
- Active application là nguồn thực thi duy nhất; legacy `references/` chỉ là
  tài liệu tham khảo. Legacy `AccessGrant` có wildcard và group principals,
  nhưng các semantics đó không được mang sang F002.
- Authorization theo thứ tự: authenticated domain user -> direct grant hoặc
  membership + role -> query filter -> retrieval -> context. Không được để LLM
  hoặc post-filter quyết định document nào được giữ lại.
- `AccessGrant` là cơ chế exception explicit, không thay thế membership. Một
  grant đọc còn hiệu lực cho phép user ngoài project đọc duy nhất resource được
  cấp; nó không mở quyền tới các document khác của project.
- Database là authority cho quyết định access. Các foreign key, unique
  constraints và indexes cần bảo vệ integrity và đường truy vấn ACL.

## Domain Model

| Entity | Trách nhiệm tối thiểu | Constraints chính |
|---|---|---|
| `User` | Domain identity của actor | ID ổn định; email unique; active state; timestamps |
| `Role` | Vocabulary quyền cơ bản | role code unique |
| `Project` | Biên tenant/resource scope | ID, name/code unique, timestamps |
| `Membership` | User tham gia project và role áp dụng | unique (`user_id`, `project_id`, `role_id`) |
| `Document` | Metadata resource có thể retrieve | `project_id` non-null FK; title/type/status; allowed role codes; timestamps |
| `AccessGrant` | Exception đọc document trực tiếp | `resource_type=document`; `resource_id`; `principal_type=user`; `principal_id`; `permission=read`; optional expiry; unique theo grant identity |
| `AuditEvent` | Dấu vết quyết định authorization | actor, action, resource/project, outcome, reason, timestamp; append-only |

`Document.allowed_role_codes` phải được kiểm tra với role của membership. Một
user có nhiều memberships ở cùng project được allow nếu ít nhất một membership
có role được document cho phép. Dữ liệu seed/test phải tạo role và membership
tường minh, không dựa vào giá trị mặc định ẩn.

## Flow
1. Hệ thống nhận domain user đã được xác thực và yêu cầu retrieve document.
2. Authorization service resolve document candidates trong database bằng một
   predicate allow: direct `AccessGrant` còn hiệu lực **hoặc** membership của
   project với role nằm trong `Document.allowed_role_codes`.
3. Candidate không thỏa predicate bị loại ngay tại truy vấn; chúng không được
   gửi tới retriever, response hay LLM context.
4. Retrieval chỉ chạy trên candidates đã được phép và trả document/context
   hợp lệ.
5. Hệ thống append một `AuditEvent` với outcome `allow` hoặc `deny`; denial
   không tiết lộ metadata/nội dung của document không được phép.

## Acceptance Criteria
- [ ] Một migration mới tạo đầy đủ bảy schema entity cùng foreign key, unique
      constraint và ACL query indexes cần thiết trên PostgreSQL database trống.
- [x] Không thể tạo `Document` thiếu `project_id`; document tham chiếu project
      không tồn tại bị database từ chối.
- [x] Không thể tạo duplicate membership cùng user/project/role hoặc duplicate
      direct read grant cùng resource/principal/permission.
- [x] Authorization mặc định deny nếu user không có direct grant và không có
      membership với role phù hợp.
- [x] User có membership Project Alpha và role được phép chỉ retrieve được
      documents Project Alpha mà role đó được phép đọc.
- [x] User có direct, non-expired `AccessGrant` đọc document có thể retrieve
      document đó dù không là member project; grant không mở rộng sang
      document khác.
- [x] User Project Alpha không thể retrieve document Project Beta; Beta không
      có trong retrieval result hoặc LLM context.
- [ ] Mỗi quyết định document retrieval allow/deny tạo `AuditEvent` append-only
      với actor, target, outcome, reason và timestamp.
- [x] Không có endpoint/retrieval path nào retrieve toàn bộ documents rồi mới
      lọc authorization trong memory hoặc ở LLM layer.
- [x] Test suite chạy bằng lệnh documented trong README và bao gồm isolation
      test Alpha/Beta.

## Tasks
- [x] F002-001 Chốt ORM models, enums, keys, timestamps, database constraints
      và indexes cho bảy domain entities.
- [x] F002-002 Tạo Alembic migration F002 và test apply trên PostgreSQL trống.
- [x] F002-003 Implement domain repositories/services cho membership, document
      ACL predicate và direct grants còn hiệu lực.
- [x] F002-004 Tích hợp authorization predicate vào document retrieval seam để
      filter trước retrieval/context construction.
- [x] F002-005 Implement append-only audit writer cho document retrieval allow
      và deny decisions.
- [x] F002-006 Viết fixtures và tests schema integrity, default deny, direct
      grant exception, audit logging, và Project Alpha/Project Beta isolation.
