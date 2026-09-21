# Experimental Evaluation Plan
Version: 0.1

## 1. Mục tiêu

Đánh giá mức độ hệ thống đạt mục tiêu hỗ trợ kỹ thuật nội bộ cho BIM/CAD và Software teams.

Thực nghiệm tập trung vào:

- retrieval đúng tài liệu;
- answer đúng và phù hợp context;
- tuân thủ quyền;
- xử lý software/version context;
- chọn tool đúng;
- hoàn thành task;
- latency.

## 2. Configurations

Sử dụng cùng một application, cùng dataset, cùng LLM và cùng test scenarios.

### Configuration A — Baseline

- RAG;
- Access Control;
- không Personalization;
- không Skills;
- không Tools.

### Configuration B — Personalized RAG

- RAG;
- Access Control;
- Personalization theo role/project/software/version;
- không Tools.

### Configuration C — Proposed System

- RAG;
- Access Control;
- Personalization;
- Skills;
- External Tools.

## 3. Mục tiêu so sánh

### A vs B

Đánh giá ảnh hưởng của Personalization.

Câu hỏi:

- tài liệu retrieved có đúng software/version/project hơn không?
- answer có phù hợp role/context hơn không?
- task success có cải thiện không?

### B vs C

Đánh giá ảnh hưởng của Skills/Tools.

Câu hỏi:

- task cần current compatibility/status có được xử lý tốt hơn không?
- tool selection có đúng không?
- task completion có tăng không?
- latency tăng bao nhiêu?

## 4. Dataset

### 4.1. Public Documentation

- Autodesk/BIM/CAD documentation;
- plugin documentation;
- public troubleshooting docs;
- public GitHub issues.

### 4.2. Synthetic Internal Dataset

Tự tạo:

- Project Alpha;
- Project Beta;
- project setup guides;
- required plugin lists;
- internal troubleshooting docs;
- synthetic incidents;
- synthetic permissions.

### 4.3. Ticket Dataset

Có thể sử dụng:

- public/anonymized helpdesk dataset;
- synthetic tickets;
- hoặc kết hợp cả hai.

## 5. Test Scenario Groups

### Group 1 — Basic Technical Questions

Ví dụ:

- cách cài plugin;
- cách cấu hình software;
- cách tìm project setup guide.

Kiểm tra RAG cơ bản.

### Group 2 — Version-sensitive Questions

Ví dụ:

> Plugin X có tương thích với Revit 2026 không?

Kiểm tra personalization/context theo version.

### Group 3 — Project-sensitive Questions

Ví dụ:

- Project Alpha yêu cầu plugin nào?
- Project Beta dùng version nào?

Kiểm tra project-aware retrieval.

### Group 4 — Role-sensitive Questions

Cùng một vấn đề nhưng khác role.

Kiểm tra:

- response detail;
- resource selection;
- permission.

### Group 5 — Known Incident Retrieval

Ví dụ:

- tìm lỗi tương tự trong incident history;
- trả về resolution đã biết.

### Group 6 — Tool-required Tasks

Ví dụ:

- current plugin version;
- current compatibility;
- current service status.

### Group 7 — Ticket Escalation

Ví dụ:

- tổng hợp issue;
- tạo ticket;
- xác nhận ticket creation.

### Group 8 — Unauthorized Requests

Ví dụ:

- user Project Alpha yêu cầu Project Beta docs;
- user cố đọc ticket của người khác;
- user cố gọi tool ngoài quyền.

Expected result:

- deny đúng;
- không leak protected data.

## 6. Metrics

### Retrieval

- Recall@k;
- Precision@k;
- nDCG@k.

### Answer Quality

- Answer Correctness;
- Relevance;
- Groundedness.

### Context/Personalization

Có thể thêm:

- Context Compatibility Accuracy;
- Version Match Accuracy;
- Project Match Accuracy.

### Access Control

- Access Control Accuracy;
- Unauthorized Access Rate.

### Tool Use

- Tool Selection Accuracy;
- Tool Argument Accuracy.

### End-to-End

- Task Success Rate.

### Performance

- median latency;
- p95 latency.

## 7. Ground Truth

Mỗi scenario phải có:

- user profile;
- role;
- project;
- software/version;
- allowed resources;
- expected relevant documents;
- expected answer constraints;
- expected tool nếu cần;
- expected final state.

## 8. Controlled Variables

Khi so sánh A/B/C cần giữ cố định:

- LLM;
- embedding model;
- dataset;
- chunking strategy nếu có thể;
- test scenarios;
- user permissions;
- tool state;
- generation parameters.

## 9. Kết quả cần thu được

Thực nghiệm không giả định trước C chắc chắn tốt hơn A/B.

Kết quả cần cho phép xác định:

- personalization hữu ích trong tình huống nào;
- tool use cần thiết trong tình huống nào;
- trade-off về latency;
- lỗi điển hình của retrieval;
- lỗi permission;
- giới hạn của hệ thống.
