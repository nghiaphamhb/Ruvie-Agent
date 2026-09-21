# System Architecture

Version: 0.2

## 1. Mục tiêu kiến trúc

Kiến trúc phải hỗ trợ:

- nhiều role và nhiều project;
- document-level access control;
- personalization theo project, software, software version và plugin version;
- RAG có source citation;
- Skills và external tools có kiểm soát;
- đánh giá hệ thống đề xuất bằng scenario và metrics;
- audit cho truy cập bị từ chối và tool call.

Ruvie/OpenWebUI trong `references/` là implementation tham khảo. Active
application xây độc lập; không mặc định copy toàn bộ kiến trúc hoặc source của
reference.

## 2. High-Level Architecture

```text
User
  |
  v
Frontend ─────── confirmation UI for side-effect actions
  |
  v
Backend API
  |
  +--> Authentication ──> trusted identity
  |
  +--> Domain Authorization ──> authorized resource scope
  |          |                         |
  |          |                         +--> Audit event
  |          v
  |     User / Project Context
  |
  +--> Chat Orchestrator
         |
         +--> Retrieval Service ──> Vector Store / Document Store
         |          |
         |          +--> authorization filter → personalization/reranking
         |
         +--> Typed Tool Adapter ──> Compatibility Registry
         |          |                Ticket System
         |          +--> tool + object authorization → audit event
         |
         +--> LLM Provider
                  |
                  v
          streamed answer + citations
```

Thứ tự là bắt buộc: **Authentication → Authorization → Authorized Scope →
Retrieval → Personalization → LLM**. Personalization không được mở rộng phạm
vi dữ liệu đã được cấp quyền.

## 3. Các thành phần chính

### 3.1. Frontend

Trách nhiệm:

- login và quản lý session client;
- chat, upload/select document và project context;
- hiển thị streaming state, citations và trạng thái tool;
- hiển thị ticket draft;
- yêu cầu user xác nhận ngay trước tool có side effect.

Frontend không tự quyết định permission. Confirmation của frontend chỉ là UX;
backend phải xác minh confirmation token trước khi thực thi action.

### 3.2. Backend API

Trách nhiệm:

- xác thực request và cung cấp trusted identity;
- load domain context;
- gọi Authorization Service trước retrieval/tool execution;
- gọi Chat Orchestrator;
- trả streaming answer/citations;
- ghi audit events.

MVP API chỉ cần các nhóm endpoint: session, chat, files/knowledge, retrieval,
citations, compatibility lookup và ticket preparation/creation.

### 3.3. Authentication

Trách nhiệm:

- xác định user identity;
- session/token lifecycle;
- cung cấp trusted `user_id` cho backend;
- bảo vệ endpoint khỏi anonymous access.

JWT/password hashing/session dependency của Ruvie là tham khảo để adapt sau
security review; domain role không lấy trực tiếp từ role `admin/user/pending`
của reference.

### 3.4. Domain Authorization Service

Authorization Service là boundary trung tâm, không phải system prompt và không
do LLM quyết định.

Trách nhiệm:

- resolve role, project membership và explicit grants;
- kiểm tra quyền document/knowledge/skill/tool/ticket;
- tạo **authorized resource scope** cho retrieval;
- kiểm tra lại tool permission và object scope từ arguments;
- ghi `allow`/`deny` audit events.

Yêu cầu bất biến:

- resource không được phép không xuất hiện trong LLM context;
- tool được phép không đồng nghĩa với quyền đọc mọi object;
- deny không được tiết lộ metadata nhạy cảm của resource.

### 3.5. User and Working Context

Context tối thiểu:

```json
{
  "user_id": "u-001",
  "role": "bim_cad_specialist",
  "project_ids": ["project-alpha"],
  "team": "bim",
  "software": "Revit",
  "software_version": "2026",
  "plugin_id": "plugin-x",
  "plugin_version": "2.4"
}
```

Context do identity, membership và input đã validate tạo thành. Trường thiếu
không được suy đoán như một quyền mới.

### 3.6. Chat Orchestrator

Trách nhiệm:

1. nhận query, identity và validated working context;
2. yêu cầu authorized resource scope;
3. gọi Retrieval Service;
4. áp dụng personalization/reranking trên kết quả đã authorized;
5. quyết định có cần typed tool hay không;
6. gọi LLM với authorized context, tool result và citation provenance;
7. stream final answer.

Orchestrator không truy cập vector store hoặc external system theo đường tắt
ngoài Authorization Service/Tool Adapter.

### 3.7. Retrieval Service

Pipeline:

```text
Document ingestion
  → parse / normalize
  → chunk
  → embed
  → index with domain metadata

User query
  → authorized scope
  → retrieval filter
  → retrieve candidates
  → version/project-aware reranking
  → citations + authorized context
  → LLM
```

Document và chunk metadata tối thiểu:

```json
{
  "document_id": "doc-123",
  "project_id": "project-alpha",
  "document_type": "plugin_guide",
  "allowed_roles": ["bim_cad_specialist", "it_support"],
  "software": "Revit",
  "software_versions": ["2025", "2026"],
  "plugin_id": "plugin-x",
  "plugin_versions": ["2.4"],
  "sensitivity": "internal",
  "source_uri": "..."
}
```

The vector query itself must be constrained to the authorized scope. Filtering
after retrieval is not acceptable. Citation must preserve document id, title,
chunk/location and source URI through to the UI.

### 3.8. Personalization Service

Input:

- authorized retrieved documents;
- project membership;
- role/team;
- software/plugin and versions;
- user task and technical level.

Allowed effects:

- rank/filter within the authorized set;
- choose answer detail/style;
- select compatible documents or tool query parameters.

Forbidden effect: add project, document, ticket or tool access.

### 3.9. Skills

Planned Skills:

- Troubleshooting;
- Log Analysis;
- Incident Summary;
- Ticket Preparation.

Skills are reviewed workflows with typed input/output. The MVP must not use
database-stored executable Python functions, arbitrary prompt artifacts or
unreviewed dynamic code as Skills.

### 3.10. Typed Tool Adapter

Tool Adapter exposes only declared operations:

```text
get_plugin_version(plugin_id)
get_compatibility(plugin_id, software, version)
get_service_status(service_id)
get_ticket(ticket_id)
get_my_tickets()
prepare_ticket(...)
create_ticket(confirmed_draft_id)
```

For every call it must:

1. validate the arguments against a typed schema;
2. check tool permission;
3. check project/resource scope from the arguments;
4. require a valid confirmation for side effects;
5. execute through a domain adapter;
6. return structured output and record an audit event.

MCP or OpenAPI can be transport implementations behind this interface; user
supplied arbitrary tool servers and terminal/shell execution are out of scope.

## 4. External Systems

### 4.1. Compatibility / Technical Status Registry

Read-only domain adapter for:

- plugin and latest version;
- supported software versions;
- known incompatibilities;
- approved technical/service status.

Use a mock registry for the initial experiment. The adapter allows replacement
with an organizational system later without changing orchestration code.

### 4.2. Ticket System

Ticket flow:

```text
Issue + context + attempted steps
  → prepare_ticket
  → user reviews draft
  → backend records confirmation
  → create_ticket
  → ticket reference + audit event
```

`create_ticket` is the first external side effect and is never triggered solely
from a model response.

## 5. Data Stores

| Store | Responsibility |
|---|---|
| PostgreSQL relational DB | users, roles, projects, memberships, grants, ticket metadata, confirmation records |
| Document/object storage | original uploaded files and normalized document content |
| Vector store | embeddings, chunk text and retrieval metadata |
| Audit store | access decisions, retrieval scope identifiers, tool attempts/results and ticket actions |

PostgreSQL là source of truth cho authorization và dùng migration để quản lý
schema. Vector store là index, không phải authority về permission.

## 6. Main request flows

### 6.1. Answer with RAG

```text
User query
  → Authenticate
  → Load validated user/working context
  → Resolve authorized scope
  → Retrieve only within that scope
  → Personalize/rerank authorized candidates
  → Generate answer with citations
  → Stream answer and audit result
```

### 6.2. Answer requiring a tool

```text
User query
  → Authenticate and resolve scope
  → Determine eligible typed tool
  → Validate arguments
  → Re-check tool + object authorization
  → Execute read-only adapter
  → Generate answer with tool provenance
```

### 6.3. Ticket creation

```text
User query
  → prepare ticket draft
  → user confirmation
  → validate confirmation + authorization again
  → create ticket
  → return ticket id and audit event
```

## 7. Experiment execution

Thực nghiệm đánh giá một phiên bản xác định của hệ thống đề xuất bằng dataset,
scenario và metrics trong `04-experiment-plan.md`; không duy trì các biến thể
A/B/C hoặc feature flags chỉ để so sánh.

Mỗi lần chạy phải ghi nhận application revision, PostgreSQL schema migration,
LLM, embedding model, dataset version, user permissions, trạng thái tool và
generation parameters để kết quả tái lập được.

## 8. Design constraints

- Authorization precedes retrieval and personalization.
- Permission is not decided by the LLM or frontend.
- Unauthorized resources never enter LLM context, tool result or citation.
- The vector store must receive an authorized filter/scope before query.
- Tool execution always passes through the Typed Tool Adapter.
- Side-effect actions require explicit confirmation and a second authorization
  check.
- RAG and tool outputs retain source provenance.
- Domain logic does not live entirely in a system prompt.
- External integrations are adapters so mock services can support experiments.
- No arbitrary shell commands, dynamic DB-stored Python tools/filters or
  unreviewed user-supplied tool servers in the MVP.
