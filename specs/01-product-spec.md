# Product Specification
Version: 0.1

## 1. Tên sản phẩm

**Personalized RAG Assistant for Internal BIM/CAD & Software Technical Support**

Tên làm việc tiếng Nga:

**Персонализированный RAG-ассистент для внутренней технической поддержки BIM/CAD-программ и плагинов**

## 2. Bối cảnh

Hệ thống được định hướng cho một công ty phát triển phần mềm và giải pháp BIM/CAD.

Người dùng chính là các nhân viên kỹ thuật như:

- BIM/CAD Specialist;
- Software Developer;
- IT Support.

Trong quá trình làm việc, họ có thể gặp các vấn đề liên quan đến:

- cài đặt và cấu hình phần mềm BIM/CAD;
- cài đặt plugin;
- tương thích giữa plugin và phiên bản phần mềm;
- lỗi khởi động hoặc lỗi sử dụng plugin;
- thiết lập môi trường phát triển;
- tìm kiếm tài liệu kỹ thuật theo project;
- tra cứu known incidents;
- chuyển vấn đề chưa giải quyết được thành ticket.

## 3. Bài toán cần giải quyết

Thông tin kỹ thuật thường phân tán giữa nhiều nguồn:

- tài liệu chính thức của phần mềm;
- plugin documentation;
- project-specific instructions;
- troubleshooting guides;
- known incidents;
- GitHub issues;
- ticket history;
- thông tin phiên bản và compatibility.

Người dùng phải tự tìm kiếm và đối chiếu nhiều nguồn, trong khi câu trả lời phù hợp còn phụ thuộc vào:

- role;
- project;
- software;
- software version;
- plugin;
- plugin version;
- quyền truy cập.

RAG thông thường có thể tìm tài liệu liên quan nhưng chưa đủ để xử lý tốt các trường hợp cần:

- lọc theo quyền;
- xét phiên bản phần mềm/plugin;
- cá nhân hóa theo working context;
- lấy dữ liệu hiện tại từ external tools;
- chuyển tiếp sự cố sang ticket system.

## 4. Mục tiêu sản phẩm

Xây dựng một web application hỗ trợ kỹ thuật nội bộ có khả năng:

- tìm kiếm thông tin bằng RAG;
- lọc tài liệu theo quyền truy cập;
- cá nhân hóa retrieval và response theo context;
- truy xuất known incidents;
- sử dụng external tools khi cần dữ liệu hiện tại;
- hỗ trợ troubleshooting cơ bản;
- chuẩn bị và tạo ticket khi vấn đề chưa được giải quyết.

## 5. User Roles

### 5.1. BIM/CAD Specialist

Nhu cầu chính:

- hướng dẫn cài đặt Revit/Civil 3D/AutoCAD hoặc phần mềm tương tự;
- hướng dẫn cài plugin;
- kiểm tra compatibility;
- tìm tài liệu project;
- tra cứu known issues;
- nhận hướng dẫn troubleshooting.

### 5.2. Software Developer

Nhu cầu chính:

- development setup;
- API/plugin documentation;
- project technical documentation;
- troubleshooting development environment;
- log analysis trong phạm vi được phép;
- known incidents liên quan đến phần mềm/plugin.

### 5.3. IT Support

Nhu cầu chính:

- xem ticket;
- tra cứu incident history;
- xem compatibility và technical status;
- truy cập troubleshooting guides;
- tổng hợp thông tin trước khi escalation.

## 6. User Context

User Context có thể bao gồm:

- user_id;
- role;
- project;
- discipline/team;
- software;
- software version;
- plugin;
- plugin version;
- permissions.

Không phải mọi trường đều bắt buộc trong mọi request.

## 7. Nguyên tắc chính

### Access Control

Quyết định user được phép:

- xem document nào;
- xem project nào;
- sử dụng tool nào;
- đọc ticket nào.

### Personalization

Trong phạm vi đã được cho phép, hệ thống ưu tiên:

- tài liệu phù hợp với role;
- tài liệu đúng project;
- tài liệu đúng software/version;
- hướng dẫn phù hợp với technical level và task.

**Personalization không được mở rộng quyền truy cập.**

## 8. Main Use Cases

### UC-01: Tìm hướng dẫn cài đặt phần mềm/plugin

User hỏi cách cài đặt hoặc cấu hình.

System:

1. lấy user context;
2. kiểm tra quyền;
3. xác định software/version/plugin;
4. truy xuất tài liệu phù hợp;
5. tạo hướng dẫn.

### UC-02: Kiểm tra compatibility

Ví dụ:

> Plugin X có chạy trên Revit 2026 không?

System:

1. tìm documentation;
2. nếu cần dữ liệu hiện tại, gọi compatibility registry;
3. trả lời dựa trên version compatibility.

### UC-03: Troubleshoot lỗi plugin

User mô tả lỗi hoặc cung cấp log.

System:

1. xác định environment;
2. tìm known issues;
3. tìm troubleshooting docs;
4. có thể dùng Log Analysis Skill;
5. đưa ra checklist xử lý.

### UC-04: Tìm tài liệu theo project

User hỏi về một workflow thuộc Project A.

System:

1. kiểm tra membership/permission;
2. chỉ retrieval trong tập document được phép;
3. ưu tiên tài liệu của Project A;
4. trả lời có source.

### UC-05: Tạo ticket khi chưa giải quyết được

System:

1. tổng hợp issue;
2. tổng hợp environment;
3. tổng hợp các bước đã thử;
4. chuẩn bị ticket;
5. user xác nhận;
6. gọi ticket tool.

### UC-06: IT Support điều tra ticket

IT Support:

1. mở ticket;
2. lấy thông tin user/environment;
3. tìm incident tương tự;
4. kiểm tra compatibility/status;
5. tạo troubleshooting checklist.

## 9. In Scope

- authentication;
- role/permission;
- chat;
- document ingestion;
- RAG;
- source citation;
- project-aware retrieval;
- software/version-aware personalization;
- known incident retrieval;
- Skills;
- compatibility/status tool;
- ticket system integration;
- experimental evaluation.

## 10. Out of Scope

- tự động sửa BIM model;
- tự động thay đổi production environment;
- arbitrary shell commands;
- restart production services;
- deployment tự động;
- quản trị hạ tầng đầy đủ;
- password reset thật;
- customer-facing support;
- toàn bộ các bài toán IT Helpdesk chung.

## 11. Data Strategy

Nếu không có dữ liệu nội bộ từ doanh nghiệp, prototype sử dụng:

### Public data

- official Autodesk documentation;
- public plugin documentation;
- public GitHub issues;
- public technical troubleshooting sources;
- public helpdesk/ticket datasets nếu phù hợp.

### Synthetic organizational data

Tự tạo:

- Project Alpha;
- Project Beta;
- internal setup guides;
- project-specific plugin lists;
- internal troubleshooting guides;
- synthetic incident history;
- synthetic role/project permissions.

Synthetic data phải được ghi rõ là dữ liệu mô phỏng phục vụ đánh giá.

## 12. MVP

MVP đầu tiên gồm:

1. Login.
2. Hai role: BIM/CAD Specialist và IT Support.
3. Chat UI.
4. Document upload/indexing.
5. Basic RAG.
6. Project/document access control.
7. Source citation.
8. Hai project mô phỏng.
9. Một nhóm tài liệu BIM/CAD công khai.

Chưa bắt buộc trong MVP:

- Skills;
- ticket tool;
- compatibility tool;
- personalization nâng cao.
