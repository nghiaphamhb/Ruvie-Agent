# OpenWebUI Analysis Specification
Version: 0.1
Status: To be completed after source-code analysis

## 1. Mục tiêu

OpenWebUI (hiện tại tôi đổi tên là Ruvie, vị trí nằm ở /references) được sử dụng như **reference implementation**, không phải mặc định là codebase cuối cùng của sản phẩm.

Mục tiêu phân tích:

- hiểu architecture;
- hiểu chat flow;
- hiểu RAG flow;
- hiểu auth/user management;
- hiểu tool calling;
- xác định phần có thể reuse;
- xác định phần cần adapt/rewrite;
- tránh copy toàn bộ codebase không cần thiết.

## 2. Nguyên tắc

Mỗi component phải được phân loại:

- REUSE;
- ADAPT;
- REWRITE;
- IGNORE.

Không sửa code OpenWebUI trong phase phân tích đầu tiên.

## 3. Khu vực cần phân tích

### Frontend

- chat UI;
- message rendering;
- streaming;
- file upload;
- source display.

### Backend

- API structure;
- authentication;
- user model;
- database access;
- chat processing.

### RAG

- document ingestion;
- chunking;
- embeddings;
- vector store;
- retrieval;
- source tracking.

### Tools

- tool registration;
- tool selection;
- tool execution;
- validation;
- MCP support nếu có.

### Configuration

- environment variables;
- model/provider configuration;
- feature flags.

## 4. Repository Map

Cần tạo sơ đồ:

```text
OpenWebUI
├── frontend
├── backend
├── auth
├── chat
├── RAG
├── tools
├── database
└── configuration
```

Với mỗi phần ghi:

- folder;
- entry point;
- main files;
- main classes/functions;
- dependencies.

## 5. Flow Analysis

### 5.1. Login Flow

```text
UI
 ↓
API
 ↓
Authentication
 ↓
Database
 ↓
Session / Token
```

### 5.2. Chat Flow

```text
User Input
 ↓
Frontend
 ↓
Backend
 ↓
LLM / Orchestrator
 ↓
Streaming
 ↓
Frontend
```

### 5.3. RAG Flow

```text
Document Upload
 ↓
Parsing
 ↓
Chunking
 ↓
Embedding
 ↓
Vector Store
```

Query:

```text
Query
 ↓
Retrieval
 ↓
Context
 ↓
Generation
```

### 5.4. Tool Flow

```text
Query
 ↓
Tool Selection
 ↓
Validation
 ↓
Execution
 ↓
Tool Result
 ↓
Final Response
```

## 6. Mapping với project mới

| Component | OpenWebUI | Project cần | Decision |
|---|---|---|---|
| Chat UI | TBD | Có | TBD |
| Streaming | TBD | Có | TBD |
| Authentication | TBD | Có | TBD |
| User management | TBD | Có | TBD |
| RAG | TBD | Có | TBD |
| Source citation | TBD | Có | TBD |
| Project-aware ACL | TBD | Có | REWRITE/BUILD |
| Software/version personalization | TBD | Có | BUILD |
| Skills | TBD | Có | TBD |
| MCP/tools | TBD | Có | TBD |
| Compatibility Registry | Không domain-specific | Có | BUILD |
| Ticket integration | Không domain-specific | Có | BUILD |
| Experiment framework | Không thesis-specific | Có | BUILD |

## 7. Reuse Rules

Nếu reuse/adapt code:

Ghi lại:

- source repository;
- version/commit;
- original path;
- license;
- reused lines/components;
- modification;
- reason.

Tạo thêm sau này:

`THIRD_PARTY_NOTICES.md`

## 8. Kết quả đầu ra của analysis

Sau khi hoàn thành phải có:

1. Repository Map.
2. Login Flow.
3. Chat Flow.
4. RAG Flow.
5. Tool Flow.
6. REUSE / ADAPT / REWRITE / IGNORE table.
7. Danh sách technical decisions.
8. Danh sách component project phải tự xây.
9. Input để cập nhật `02-architecture.md` lên version 0.2.
