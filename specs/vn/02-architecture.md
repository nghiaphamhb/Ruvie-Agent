# System Architecture
Version: 0.1

## 1. Mục tiêu kiến trúc

Kiến trúc phải hỗ trợ:

- nhiều role;
- nhiều project;
- document-level access control;
- personalization theo software/version/project;
- RAG;
- Skills;
- external tools;
- cấu hình bật/tắt từng thành phần phục vụ experiment.

## 2. High-Level Architecture

```text
User
  |
  v
Frontend
  |
  v
Backend API
  |
  +------------------------------+
  |                              |
  v                              v
Authentication               User Context
                                 |
                         Role / Project / Permissions
                                 |
                                 v
                         Chat Orchestrator
                    /          |           \
                   /           |            \
                  v            v             v
                RAG     Personalization    Tool Layer
                 |                         /         \
                 v                        v           v
          Knowledge Base          Compatibility   Ticket
                                  / Status Tool   System
```

## 3. Các thành phần chính

### 3.1. Frontend

Trách nhiệm:

- login;
- chat;
- upload/select document;
- hiển thị sources;
- hiển thị tool-call state;
- xác nhận trước action có side effect.

Frontend không tự quyết định permission.

### 3.2. Backend API

Trách nhiệm:

- nhận request;
- xác thực user;
- load user context;
- gọi Chat Orchestrator;
- trả response;
- ghi log/audit cần thiết.

### 3.3. Authentication

Trách nhiệm:

- xác định user identity;
- session/token;
- cung cấp trusted user_id.

### 3.4. Authorization

Trách nhiệm:

- kiểm tra document permission;
- kiểm tra project permission;
- kiểm tra skill permission;
- kiểm tra tool permission;
- kiểm tra object-level permission đối với ticket/resource.

Nguyên tắc:

**Unauthorized resource không được đưa vào LLM context.**

### 3.5. User Context

Dữ liệu sơ bộ:

```json
{
  "user_id": "u-001",
  "role": "bim_specialist",
  "projects": ["project-alpha"],
  "software": "Revit",
  "software_version": "2026",
  "permissions": []
}
```

### 3.6. Chat Orchestrator

Trách nhiệm:

- nhận query + user context;
- quyết định retrieval;
- quyết định có dùng Skill/tool hay không;
- thu thập context;
- gọi LLM;
- tạo final response.

Không được bypass Authorization.

### 3.7. RAG Module

Pipeline:

```text
Query
  ↓
User Context
  ↓
Authorized Resource Scope
  ↓
Retrieval
  ↓
Version/Project-aware Ranking
  ↓
Authorized Relevant Context
  ↓
LLM
```

RAG Module gồm:

- ingestion;
- parsing;
- chunking;
- embeddings;
- indexing;
- retrieval;
- metadata filtering;
- source tracking.

### 3.8. Personalization Module

Input:

- role;
- project;
- software;
- version;
- retrieved authorized documents.

Output có thể ảnh hưởng tới:

- metadata filtering;
- reranking;
- context prioritization;
- response style/level of detail.

Personalization không thay đổi permission.

### 3.9. Skills

Dự kiến:

- Troubleshooting Skill;
- Log Analysis Skill;
- Incident Summary Skill;
- Ticket Preparation Skill.

Skill availability phụ thuộc role/permission.

### 3.10. Tool Layer

Trách nhiệm:

- expose tool được phép;
- validate arguments;
- check permission;
- execute tool;
- return structured result;
- audit tool call.

Tool layer dự kiến kết nối qua MCP hoặc adapter tương đương.

## 4. External Systems

### 4.1. Compatibility / Technical Status Registry

Ví dụ:

- plugin version;
- supported Revit versions;
- known incompatibility;
- service availability.

Ví dụ tool:

```text
get_plugin_version(plugin_id)
get_compatibility(plugin_id, software, version)
get_service_status(service_id)
```

### 4.2. Ticket System

Ví dụ:

```text
create_ticket(...)
get_ticket(ticket_id)
get_my_tickets()
```

## 5. Data Stores

Dự kiến có:

- relational database cho users/roles/projects/permissions/tickets metadata;
- vector store cho embeddings;
- file/object storage cho raw documents;
- optional audit log storage.

## 6. Main Request Flow

```text
User Query
   ↓
Authenticate
   ↓
Load User Context
   ↓
Determine Authorized Scope
   ↓
Retrieve Documents
   ↓
Apply Personalization
   ↓
Need Tool?
   ├── No
   │    ↓
   │   Generate Answer
   │
   └── Yes
        ↓
     Check Tool Permission
        ↓
     Execute Tool
        ↓
     Tool Result
        ↓
     Generate Final Answer
```

## 7. Thiết kế phục vụ Experiment

Hệ thống phải có feature flags/configuration:

```yaml
personalization: false
skills: false
tools: false
```

hoặc:

```yaml
personalization: true
skills: true
tools: true
```

Điều này cho phép chạy nhiều configuration trên cùng một codebase.

## 8. Nguyên tắc thiết kế

- Authorization trước Personalization.
- Permission không do LLM tự quyết định.
- Tool execution luôn đi qua backend/tool layer.
- Mọi tool có side effect cần xác nhận khi phù hợp.
- RAG phải giữ source provenance.
- Business logic domain không nên nhét toàn bộ vào một system prompt.
- External integrations nên thông qua interface/adapter để có thể dùng mock service trong experiment.
