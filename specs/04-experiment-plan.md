# Experimental Evaluation Plan

Version: 0.2

## 1. Mục tiêu

Đánh giá mức độ hệ thống đề xuất hỗ trợ kỹ thuật nội bộ cho BIM/CAD và Software
teams. Thực nghiệm đánh giá một implementation xác định, không so sánh các
configuration A/B/C.

Các trọng tâm:

- retrieval đúng tài liệu;
- answer đúng, grounded và phù hợp context;
- tuân thủ quyền;
- xử lý software/plugin version context;
- chọn và gọi tool đúng;
- hoàn thành task;
- latency.

## 2. System under evaluation

System under evaluation gồm các thành phần đã được implement cho mốc đánh giá:

- RAG và source citation;
- project/document access control;
- personalization theo role/project/software/version;
- Skills đã được review;
- typed external tools;
- ticket confirmation flow nếu ticket integration đã được bật.

Mỗi báo cáo phải ghi rõ application revision, PostgreSQL schema migration, LLM,
embedding model, dataset version, permissions, tool state và generation
parameters. Một capability chưa được implement sẽ được ghi là out of scope của
lần chạy, không tạo configuration thay thế.

## 3. Dataset

### 3.1. Public Documentation

- Autodesk/BIM/CAD documentation;
- plugin documentation;
- public troubleshooting docs;
- public GitHub issues.

### 3.2. Synthetic Internal Dataset

Tự tạo và gắn nhãn rõ dữ liệu mô phỏng:

- Project Alpha;
- Project Beta;
- project setup guides;
- required plugin lists;
- internal troubleshooting docs;
- synthetic incidents;
- synthetic permissions.

### 3.3. Ticket Dataset

Có thể sử dụng:

- public/anonymized helpdesk dataset;
- synthetic tickets;
- hoặc kết hợp cả hai.

## 4. Test Scenario Groups

### Group 1 — Basic Technical Questions

Ví dụ:

- cách cài plugin;
- cách cấu hình software;
- cách tìm project setup guide.

Kiểm tra RAG cơ bản và citation.

### Group 2 — Version-sensitive Questions

Ví dụ:

> Plugin X có tương thích với Revit 2026 không?

Kiểm tra software/plugin version context và compatibility lookup khi phù hợp.

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
- chuẩn bị ticket;
- xác nhận ticket creation;
- kiểm tra audit event.

### Group 8 — Unauthorized Requests

Ví dụ:

- user Project Alpha yêu cầu Project Beta docs;
- user cố đọc ticket của người khác;
- user cố gọi tool ngoài quyền.

Expected result:

- deny đúng;
- không leak protected data;
- có audit event cho access denial.

## 5. Metrics

### Retrieval

- Recall@k;
- Precision@k;
- nDCG@k.

### Answer Quality

- Answer Correctness;
- Relevance;
- Groundedness;
- Citation Accuracy.

### Context and Access Control

- Context Compatibility Accuracy;
- Version Match Accuracy;
- Project Match Accuracy;
- Access Control Accuracy;
- Unauthorized Access Rate.

### Tool Use

- Tool Selection Accuracy;
- Tool Argument Accuracy;
- Confirmation Compliance for side effects.

### End-to-End and Performance

- Task Success Rate;
- median latency;
- p95 latency.

## 6. Ground Truth

Mỗi scenario phải có:

- user profile, role và project membership;
- software/plugin version context;
- allowed resources;
- expected relevant documents;
- expected answer constraints và citations;
- expected tool/arguments nếu cần;
- expected final state;
- expected audit outcome cho denial hoặc side effect.

## 7. Controlled execution

Trong một batch evaluation, giữ cố định:

- application revision và PostgreSQL migration revision;
- LLM và embedding model;
- dataset và chunking strategy;
- test scenarios;
- user permissions;
- tool state;
- generation parameters.

Nếu một thành phần thay đổi, ghi thành một experiment run mới thay vì dùng
feature flag để tạo configuration so sánh.

## 8. Kết quả cần thu được

Kết quả cần cho phép xác định:

- hệ thống xử lý tốt nhóm scenario nào;
- lỗi retrieval, citation, permission và tool điển hình;
- trade-off latency của implementation hiện tại;
- giới hạn kỹ thuật và dữ liệu;
- hạng mục cần cải thiện trong iteration tiếp theo.
