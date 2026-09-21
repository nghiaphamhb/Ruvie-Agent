# Access Control Specification
Version: 0.1

## 1. Mục tiêu

Đảm bảo user chỉ được truy cập:

- đúng project;
- đúng document;
- đúng ticket;
- đúng Skill;
- đúng tool;
- đúng phạm vi dữ liệu của tool.

## 2. Subjects

Subject chính là User.

Thuộc tính có thể gồm:

- user_id;
- role;
- projects;
- team/discipline;
- explicit permissions.

## 3. Roles

### BIM_CAD_SPECIALIST

Có thể:

- đọc general BIM/CAD docs;
- đọc project docs của project mình tham gia;
- tra cứu plugin setup/compatibility;
- tạo ticket cho issue của mình.

### DEVELOPER

Có thể:

- đọc development docs;
- đọc project technical docs;
- đọc plugin/API docs;
- dùng log-analysis trong phạm vi được phép;
- tạo ticket.

### IT_SUPPORT

Có thể:

- đọc troubleshooting guides;
- đọc incident history;
- đọc ticket theo permission;
- dùng technical status/compatibility tools;
- xử lý escalation.

## 4. Resources

### Documents

- general technical docs;
- software docs;
- plugin docs;
- project docs;
- troubleshooting docs;
- incident docs.

### Skills

- Troubleshooting;
- Log Analysis;
- Incident Summary;
- Ticket Preparation.

### Tools

- get_plugin_version;
- get_compatibility;
- get_service_status;
- get_ticket;
- create_ticket.

### Business Objects

- project;
- ticket;
- incident;
- plugin record;
- service record.

## 5. Permission Model

Mô hình ban đầu:

**RBAC + resource/project constraints**

Role quyết định permission cơ bản.

Project/resource metadata quyết định phạm vi cụ thể.

Ví dụ:

```text
role = BIM_CAD_SPECIALIST
project = Project Alpha
```

không đồng nghĩa với quyền đọc Project Beta.

## 6. Document Metadata

Ví dụ:

```json
{
  "document_id": "doc-123",
  "document_type": "plugin_guide",
  "project_id": "project-alpha",
  "allowed_roles": ["BIM_CAD_SPECIALIST", "IT_SUPPORT"],
  "software": "Revit",
  "software_version": ["2025", "2026"],
  "plugin_id": "plugin-x",
  "sensitivity": "internal"
}
```

## 7. Permission Matrix sơ bộ

| Resource / Action | BIM/CAD Specialist | Developer | IT Support |
|---|---|---|---|
| General BIM/CAD docs | Yes | Limited | Yes |
| Own project docs | Yes | Yes | Yes |
| Other project docs | No | No | By permission |
| Plugin installation docs | Yes | Yes | Yes |
| Developer API docs | Limited | Yes | Yes |
| Known incidents | Limited | Limited | Yes |
| Troubleshooting guides | Yes | Yes | Yes |
| Read own ticket | Yes | Yes | Yes |
| Read arbitrary ticket | No | No | By permission |
| Create ticket | Yes | Yes | Yes |
| Compatibility tool | Yes | Yes | Yes |
| Detailed service status | Limited | Limited | Yes |
| Log Analysis Skill | Limited | Yes | Yes |

Bảng này là bản v0.1 và sẽ được điều chỉnh theo use cases thực tế.

## 8. Retrieval Authorization Flow

```text
Query
  ↓
Authenticated User
  ↓
Resolve Allowed Projects / Documents
  ↓
Filter Search Space
  ↓
Retrieve
  ↓
Optional Personalization / Reranking
  ↓
LLM Context
```

Yêu cầu:

**Không được retrieve rồi mới để LLM tự loại tài liệu không được phép.**

## 9. Tool Authorization Flow

```text
Tool Request
   ↓
Check Tool Permission
   ↓
Validate Arguments
   ↓
Check Resource Scope
   ↓
Execute
```

Ví dụ:

User được phép dùng `get_ticket` không đồng nghĩa với quyền đọc mọi ticket.

## 10. Personalization Rule

Thứ tự bắt buộc:

```text
Authorization
    ↓
Personalization
```

Không hợp lệ:

```text
Personalization
    ↓
Expand Resource Set
    ↓
Bypass Authorization
```

## 11. Security Acceptance Criteria

- User không retrieve document ngoài quyền.
- Document ngoài quyền không xuất hiện trong LLM context.
- User không truy cập project khác.
- User không gọi unauthorized tool.
- Allowed tool không được dùng để truy cập unauthorized object.
- Personalization không làm thay đổi permission.
- Tool call và access denial có audit log.
