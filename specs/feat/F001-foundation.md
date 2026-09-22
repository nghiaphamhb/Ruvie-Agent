# F001 - Foundation

## Goal
Thiết lập nền tảng chạy và kiểm thử tối thiểu cho active application, để các
feature sau có một backend/frontend độc lập, cấu hình an toàn và PostgreSQL
migrate được.

## User Story
As a developer, I want a reproducible application foundation, so that I can
build and evaluate domain features without depending on `references/` or local
machine state.

## Scope
### In
- Scaffold active application tối thiểu: FastAPI backend và Svelte frontend.
- Cấu hình local qua `.env`, với `.env.example` không chứa secrets.
- Kết nối PostgreSQL qua `DATABASE_URL` và migration framework; migration đầu
  tiên có thể rỗng.
- Health/readiness endpoint cho backend.
- Test runner và một smoke test cho health endpoint.
- Documentation chạy local, test và kết nối PostgreSQL.

### Out
- Authentication, user/role/project schema và authorization.
- Upload, document ingestion, vector store, RAG và citations.
- Chat UI/completion endpoint.
- Skills, MCP/OpenAPI tools, compatibility registry và ticket integration.
- Copy, chạy hoặc deploy code trong `references/`.
- CI/CD, Docker image production và external secret manager.

## Flow
1. Developer sao chép `.env.example` thành `.env` và điền cấu hình local.
2. Developer chạy migration để chuẩn bị database.
3. Developer khởi động backend và frontend bằng documented commands.
4. Backend kết nối PostgreSQL và trả `200` từ health/readiness endpoint.
5. Test runner chạy smoke test, xác nhận backend khởi động và health endpoint
   hoạt động.

## Acceptance Criteria
- [x] Active application không import, chạy hoặc phụ thuộc runtime vào
      `references/`.
- [x] `.env` bị ignore và `.env.example` liệt kê mọi biến local bắt buộc mà
      không chứa secret thật.
- [ ] Migration có thể chạy trên một PostgreSQL database trống mà không cần
      thao tác thủ công.
- [x] Backend cung cấp `GET /health` và `GET /ready`; cả hai trả trạng thái
      thành công khi dependency tối thiểu sẵn sàng.
- [x] Có một lệnh documented để chạy backend, frontend, migration và test.
- [x] Có smoke test tự động cho health endpoint.
- [x] Không có feature domain, RAG, tool execution hoặc side effect nào được
      thêm trong feature này.

## Tasks
- [x] F001-001 Chọn cấu trúc thư mục active application và scaffold FastAPI +
      Svelte tối thiểu.
- [x] F001-002 Tạo configuration module, `.env.example` và validation cho
      biến cấu hình bắt buộc.
- [x] F001-003 Thiết lập PostgreSQL connection, migration framework và
      migration initial baseline.
- [x] F001-004 Thêm health/readiness endpoints và smoke test backend.
- [x] F001-005 Viết hướng dẫn local development, PostgreSQL migration và test
      vào README (by english).
