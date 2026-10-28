# Định hình bài toán Ruvie Agent

Cập nhật: 2026-10-10.

**Đề tài:** Phát triển agent hỗ trợ kỹ thuật nội bộ cho công ty Harmony.

**Bối cảnh tổ chức mục tiêu:** Harmony chuyên về phần mềm BIM/CAD và chuyển đổi số cho ngành kiến trúc, xây dựng. Phạm vi tập trung vào phần mềm nhân viên sử dụng trong công việc, đặc biệt là phần mềm nội bộ của công ty.

Tài liệu này xác định vấn đề cần giải quyết, người dùng, phạm vi và cách đánh giá. Phần hiện trạng mô tả ứng dụng active trong repository. Phần định hướng mô tả mục tiêu phát triển, chưa đồng nghĩa với chức năng đã triển khai.

## 1. Bối cảnh và vấn đề hiện tại

Theo bối cảnh công việc được xác định cho đề tài, nhân viên Harmony có thể gặp vấn đề khi cài đặt, cấu hình hoặc thao tác với phần mềm, đặc biệt là phần mềm nội bộ. Khi không biết nguyên nhân hoặc cách xử lý, nhân viên thường phải liên hệ bộ phận IT Support để được hướng dẫn.

Cách hỗ trợ này phát sinh hai vấn đề:

- Nhân viên phải chờ phản hồi, làm gián đoạn công việc và khó tự xử lý nếu lỗi xuất hiện lại.
- IT Support phải tiếp nhận nhiều yêu cầu, trong đó có những vấn đề lặp lại đã có hướng dẫn. Nhân sự hỗ trợ còn phải hỏi lại môi trường, thông báo lỗi và các bước người dùng đã thử trước khi chẩn đoán.

Nguồn kiến thức để giải quyết vấn đề có thể đã tồn tại nhưng nhân viên chưa biết tìm ở đâu hoặc chưa biết áp dụng. Các nguồn mục tiêu gồm:

- Hướng dẫn cài đặt và sử dụng phần mềm nội bộ.
- Tài liệu phần mềm BIM/CAD và plugin.
- Hướng dẫn thiết lập môi trường làm việc hoặc phát triển.
- Quy trình riêng của project.
- Hướng dẫn chẩn đoán và xử lý lỗi.
- Danh sách lỗi đã biết, lịch sử sự cố và cách giải quyết.

Một hướng dẫn có thể chỉ áp dụng cho một phiên bản phần mềm, plugin hoặc môi trường cụ thể. Người dùng còn cần biết mình có được phép sử dụng tài liệu đó không và làm thế nào để kiểm tra kết quả sau khi thực hiện.

Bài toán được đặt ra là giúp nhân viên tự xử lý các vấn đề phù hợp bằng hướng dẫn từ nguồn nội bộ được cấp quyền. Nếu vấn đề chưa giải quyết được, ứng dụng tự tổng hợp thông tin đã thu thập, tạo ticket và gửi đến IT Support qua tích hợp được cho phép. Nhân viên không phải mô tả lại toàn bộ từ đầu; IT Support nhận được thông tin đủ để tiếp tục xử lý.

Trợ lý cần hỗ trợ cả hai phía: hướng dẫn nhân viên tự xử lý và chuẩn bị thông tin có cấu trúc cho bộ phận IT Support. IT Support vẫn xử lý các vấn đề chưa thể giải quyết bằng hướng dẫn hoặc cần quyền chuyên môn.

RAG, cá nhân hóa, Skills và công cụ ngoài là các phương tiện để thực hiện bài toán này. Những yêu cầu quan trọng gồm:

- Tìm đúng hướng dẫn trong phạm vi người dùng được đọc.
- Xét đúng phần mềm, phiên bản, project và môi trường.
- Trình bày các bước phù hợp với khả năng của người dùng, kèm cách kiểm tra kết quả.
- Thu thập thêm thông tin khi chưa đủ cơ sở chẩn đoán.
- Giữ lại triệu chứng, môi trường và các bước đã thử để chuyển tiếp khi cần.
- Dùng dữ liệu trạng thái hiện tại khi tài liệu tĩnh chưa đủ để xác định nguyên nhân.

Phạm vi ưu tiên là hỗ trợ sử dụng phần mềm trong công ty, đặc biệt phần mềm nội bộ và BIM/CAD. Các vấn đề VPN hoặc tài khoản chỉ được đưa vào khi liên quan tới việc sử dụng các phần mềm đó và có quy trình hỗ trợ phù hợp.

## 2. Phát biểu bài toán

Xây dựng Ruvie Agent, một ứng dụng web giúp nhân viên Harmony tự xử lý vấn đề khi cài đặt và sử dụng phần mềm dựa trên nguồn kiến thức nội bộ được cấp quyền. Khi chưa giải quyết được, hệ thống tự tổng hợp hồ sơ sự cố, tạo và gửi ticket đến bộ phận IT Support theo luồng tích hợp đã được cho phép.

**Đầu vào:** Mô tả vấn đề, danh tính đã xác thực, quyền trong cơ sở dữ liệu và ngữ cảnh công việc đã được kiểm tra. Ngữ cảnh dự kiến gồm phần mềm/phiên bản, plugin/phiên bản, hệ điều hành, project, thông báo lỗi, log hoặc ảnh lỗi do người dùng cung cấp và các bước đã thử.

**Xử lý:** Thu thập thông tin còn thiếu; lọc tài liệu theo quyền; tìm hướng dẫn phù hợp; hướng dẫn người dùng thực hiện và kiểm tra kết quả. Nếu chưa xử lý được, tổng hợp thông tin để chuyển tiếp qua hệ thống ticket.

**Đầu ra:** Một trong hai kết quả:

1. Nhân viên có thể tự xử lý vấn đề theo hướng dẫn có nguồn và xác nhận được kết quả.
2. IT Support nhận ticket có nội dung rõ ràng để tiếp tục xử lý; nhân viên biết mã ticket và trạng thái gửi thành công hoặc thất bại.

Hồ sơ sự cố mục tiêu gồm triệu chứng, mức ảnh hưởng do người dùng cung cấp, môi trường, thông tin lỗi, bằng chứng được phép chia sẻ, hướng dẫn đã áp dụng và kết quả từng bước. Hệ thống không tự thu thập môi trường hoặc đọc log trên máy nhân viên khi chưa có cơ chế và quyền tương ứng.

Điều kiện xác định chưa xử lý được và cách xác nhận hoặc ủy quyền tạo/gửi ticket cần được chốt trong spec tích hợp. Việc tự động hóa không đồng nghĩa LLM được tùy ý gửi dữ liệu hoặc tạo ticket chỉ dựa trên suy đoán của nó.

**Mục tiêu nghiệp vụ:** Giảm thời gian nhân viên chờ hỗ trợ, giảm các yêu cầu lặp lại mà IT Support phải xử lý trực tiếp và nâng chất lượng thông tin của những yêu cầu cần chuyển tiếp. Đây là mục tiêu cần đo, chưa phải kết quả đã được chứng minh.

Câu hỏi nghiên cứu là: Agent sử dụng kiến thức nội bộ, ngữ cảnh công việc và chuyển tiếp có cấu trúc có thể giúp nhân viên tự xử lý vấn đề và hỗ trợ công việc của IT Support hiệu quả đến mức nào, đồng thời bảo đảm quyền truy cập và chất lượng hướng dẫn?

## 3. Người dùng và nhu cầu

Người dùng trực tiếp là nhân viên cần hỗ trợ khi sử dụng phần mềm. IT Support là bộ phận tiếp nhận các vấn đề chưa giải quyết được và sử dụng thông tin tổng hợp để tiếp tục chẩn đoán. Các nhóm dưới đây làm rõ nhu cầu; không giới hạn nhân viên sử dụng ứng dụng chỉ trong ba chức danh kỹ thuật.

| Nhóm người dùng | Nhu cầu chính | Hướng trả lời phù hợp |
| --- | --- | --- |
| Nhân viên sử dụng phần mềm | Tự xử lý lỗi cài đặt/sử dụng và gửi yêu cầu hỗ trợ khi cần | Các bước dễ thực hiện, cách kiểm tra kết quả và thông tin chuyển tiếp rõ ràng |
| Chuyên viên BIM/CAD | Cài đặt phần mềm/plugin, tìm quy trình project, xử lý lỗi sử dụng và kiểm tra tương thích | Hướng dẫn từng bước, điều kiện áp dụng và lưu ý về phiên bản |
| Lập trình viên | Thiết lập môi trường, tra cứu API/plugin, tìm tài liệu kỹ thuật và phân tích lỗi | Chi tiết kỹ thuật, giả thuyết chẩn đoán và thông tin cần kiểm tra |
| IT Support | Tra cứu hướng dẫn chẩn đoán, lịch sử sự cố và thông tin để xử lý hoặc chuyển cấp | Checklist, bằng chứng, các bước đã thử và tóm tắt sự cố |
| Quản trị viên hệ thống, dự kiến | Quản lý thiết lập dùng chung và chính sách vận hành | Cấu hình có kiểm tra quyền và kết quả áp dụng rõ ràng |

Đây là mô tả nhu cầu. Vai trò không mặc nhiên cho phép đọc mọi tài liệu hoặc dùng mọi công cụ. Quyền cụ thể phải được xác định trên backend. Mã hiện tại có ba vai trò project: `BIM_CAD_SPECIALIST`, `DEVELOPER`, `IT_SUPPORT`; cơ chế quản trị settings còn cần thiết kế.

## 4. Phân biệt quyền truy cập và cá nhân hóa

**Kiểm soát truy cập** trả lời: Người dùng được phép đọc tài liệu nào và thực hiện thao tác nào?

**Cá nhân hóa** trả lời: Trong phạm vi đã được phép, tài liệu nào phù hợp hơn và nên trình bày câu trả lời ở mức độ nào?

Ví dụ, hai người cùng được phép đọc một hướng dẫn sửa lỗi plugin:

- Chuyên viên BIM/CAD nhận các bước thao tác và cách nhận biết kết quả.
- IT Support có thể nhận thêm hướng chẩn đoán và dữ liệu cần thu thập, nếu các dữ liệu đó cũng nằm trong quyền của họ.

Nếu một tài liệu chỉ dành cho lập trình viên, nhu cầu chẩn đoán của người dùng khác không tạo thêm quyền đọc tài liệu đó. Việc là thành viên của project cũng chưa đủ: vai trò phải thuộc tập được phép của tài liệu, hoặc người dùng phải có quyền đọc trực tiếp còn hiệu lực.

Backend phải lọc quyền trước khi chọn các đoạn kết quả, xây dựng ngữ cảnh cho LLM hoặc trả nội dung cho trình duyệt. Không giao quyết định quyền cho LLM hoặc tin phạm vi quyền do client tự khai.

## 5. Nền tảng đã có trong ứng dụng hiện tại

Ruvie Agent hiện có một nền tảng tra cứu và hỏi đáp tài liệu với các khả năng sau:

| Khả năng | Hiện trạng |
| --- | --- |
| Xác thực | Đăng nhập bằng tài khoản được cấp, cookie session và danh tính được backend xác minh; chưa có đăng ký công khai |
| Project và quyền tài liệu | Liệt kê project theo membership; đọc tài liệu theo membership/vai trò hoặc quyền đọc trực tiếp còn hạn |
| Tiếp nhận tài liệu | Upload PDF hoặc văn bản UTF-8, tối đa 25 MiB, có metadata phần mềm và phiên bản |
| Lưu trữ | File gốc nằm trong LocalBlobStore riêng tư; dữ liệu ứng dụng và vector nằm trong PostgreSQL với pgvector |
| Ingestion | Worker riêng đọc file, trích xuất văn bản, chia đoạn, tạo embedding và đánh dấu revision READY sau khi xử lý thành công |
| Retrieval | Lọc tài liệu được đọc và revision READY trong SQL trước khi chọn kết quả theo độ tương đồng vector |
| Chat | Gửi ngữ cảnh đã được cấp quyền tới LLM, nhận câu trả lời qua stream và trả citation khi có kết quả tài liệu |
| Kết nối LLM | Lưu URL/key/model theo tài khoản trên backend; có cấu hình server dự phòng và SOCKS5 tùy chọn |
| Ngôn ngữ giao diện | Tiếng Việt, tiếng Anh, tiếng Nga; lưu lựa chọn thủ công trên trình duyệt |
| Audit | Ghi nhận các quyết định truy cập trong những luồng đã triển khai; bảng audit được bảo vệ khỏi sửa/xóa |

Luồng tiếp nhận tài liệu hiện tại gồm hai giai đoạn:

1. Upload service kiểm tra request/quyền, lưu file gốc và tạo document, revision pending cùng ingestion job.
2. Worker nhận job, đọc file đã lưu, tạo các đoạn và embedding, lưu vào PostgreSQL rồi đánh dấu hoàn tất.

pgvector là phần mở rộng của PostgreSQL. Vector embedding không nằm trong một database riêng. Chỉ revision READY mới được dùng để truy xuất nội dung cho RAG.

Các giới hạn hiện tại cần ghi rõ:

- Metadata phần mềm/phiên bản đã được lưu, nhưng chưa có cá nhân hóa hoặc xếp hạng chuyên biệt theo role/project/software/plugin version.
- Chat xử lý từng câu hỏi độc lập; lịch sử hiện giữ trong trang, chưa có hội thoại lưu bền vững theo tài khoản.
- Khi không có đoạn tài liệu phù hợp, mã hiện tại cho phép trả lời từ kiến thức chung và không nhận đó là nội dung có nguồn tài liệu nội bộ.
- Có citation không đồng nghĩa đã chứng minh mọi phát biểu trong câu trả lời đúng; chất lượng sử dụng nguồn cần được đánh giá riêng.
- HTTP upload hiện tạo document mới. Thêm revision vào cùng document đã có ở service nhưng chưa được cung cấp qua multipart route.
- Chưa có Skills nghiệp vụ, MCP runtime, công cụ trạng thái/tương thích hoặc tích hợp ticket trong active app.
- Chưa có trang quản trị settings hoặc ngôn ngữ mặc định của tổ chức. Locale giao diện không tự quyết định ngôn ngữ trả lời của LLM.

## 6. Mục tiêu phát triển tiếp theo

Ưu tiên phát triển một luồng hỗ trợ hoàn chỉnh: nhân viên mô tả vấn đề → nhận hướng dẫn từ nguồn nội bộ → thực hiện và kiểm tra kết quả → nếu chưa xử lý được, hệ thống tổng hợp và chuyển ticket tới IT Support. Các khả năng dưới đây là định hướng, chưa được coi là đã hoàn thành.

### 6.1. Cá nhân hóa trong phạm vi được cấp quyền

Sử dụng vai trò, project, phần mềm và phiên bản để ưu tiên tài liệu và chọn mức độ giải thích. Khi thiếu phiên bản hoặc môi trường, hỏi bổ sung thay vì tự chọn một hướng dẫn có thể không phù hợp.

Ngữ cảnh người dùng cung cấp là thông tin nghiệp vụ cần kiểm tra, không phải bằng chứng cấp quyền. Cá nhân hóa chỉ xử lý tập dữ liệu đã được phép.

### 6.2. Quy trình chuyên biệt bằng Skills

Skill là một quy trình được định nghĩa để xử lý một loại nhiệm vụ. Các Skill dự kiến:

- Chẩn đoán lỗi: thu thập triệu chứng và đề xuất thứ tự kiểm tra.
- Phân tích log: phân tích log người dùng được phép cung cấp.
- Tóm tắt sự cố: tổng hợp môi trường, bằng chứng và các bước đã thử.
- Chuẩn bị ticket: tạo bản nháp đủ thông tin để bộ phận hỗ trợ tiếp nhận.

Skills nghiệp vụ này thuộc sản phẩm Ruvie Agent. Các file `SKILL.md` hướng dẫn công cụ phát triển trong repository không đồng nghĩa sản phẩm đã có hệ thống Skills.

### 6.3. Công cụ ngoài qua MCP hoặc adapter có kiểm soát

MCP là giao thức có thể dùng để kết nối trợ lý với công cụ ngoài. Bước đầu chỉ cần xem xét hai nhóm tích hợp:

1. Tra cứu dữ liệu hiện tại: trạng thái dịch vụ hoặc thông tin tương thích phần mềm/plugin.
2. Ticket: tra cứu ticket được cấp quyền, chuẩn bị và tạo yêu cầu hỗ trợ.

Ví dụ, tài liệu mô tả cách xử lý lỗi truy cập dịch vụ. Nếu công cụ trạng thái xác nhận dịch vụ đang gián đoạn, trợ lý có thể giải thích rằng người dùng không cần tiếp tục thay đổi cấu hình cục bộ. Kết quả công cụ phải ghi rõ nguồn và thời điểm lấy dữ liệu.

Backend phải kiểm tra cả quyền dùng công cụ lẫn quyền với đối tượng cụ thể trong tham số. Tích hợp ticket tự động tạo và gửi hồ sơ đã tổng hợp theo điều kiện chuyển tiếp và cơ chế xác nhận/ủy quyền được chốt trong spec. Người nhận chỉ được nhận thông tin thuộc phạm vi chia sẻ cho phép. Hệ thống phải ghi nhận kết quả, báo mã ticket hoặc lỗi gửi và tránh tạo trùng khi thử lại.

### 6.4. Thiết lập quản trị

Bổ sung quyền quản trị và giao diện thiết lập dùng chung, gồm chế độ kết nối LLM trực tiếp/qua proxy và ngôn ngữ mặc định của tổ chức. Hai thiết lập độc lập; người dùng thường không tự thay đổi proxy của backend.

## 7. Phạm vi và các tình huống đại diện

Phạm vi trước mắt là hoàn thiện và đánh giá hỏi đáp tài liệu có phân quyền. Cá nhân hóa, Skills và công cụ ngoài phát triển theo các mốc tiếp theo.

| Tình huống | Kết quả cần đạt | Mức hỗ trợ hiện tại |
| --- | --- | --- |
| Hỏi cách cài một plugin từ tài liệu đã upload | Trả hướng dẫn và citation đến đoạn được phép đọc | Đã có nền tảng RAG; độ đúng của hướng dẫn cần đánh giá |
| Hỏi quy trình thuộc project khác, không có quyền tài liệu | Không đưa nội dung bị cấm vào kết quả hoặc ngữ cảnh LLM | Đã có lọc quyền; không phải mọi câu hỏi đều có thông báo từ chối riêng |
| Hỏi plugin có tương thích với một phiên bản phần mềm không | Xét đúng phiên bản; hỏi thêm khi thiếu dữ liệu; dùng nguồn tương thích khi cần | Có tra cứu tài liệu cơ bản; cá nhân hóa phiên bản/công cụ chưa có |
| Hai vai trò hỏi cùng một lỗi | Cùng tuân thủ quyền; cách giải thích phù hợp từng vai trò | Chưa có cá nhân hóa chuyên biệt |
| Người dùng báo một dịch vụ không truy cập được | Phân biệt lỗi cục bộ với gián đoạn chung bằng dữ liệu trạng thái hiện tại | Công cụ trạng thái chưa có |
| Vấn đề chưa giải quyết được | Tự tổng hợp triệu chứng, môi trường, bằng chứng và bước đã thử; tạo/gửi ticket theo luồng được cho phép; báo mã ticket hoặc lỗi gửi | Skills và ticket integration chưa có |

Ngoài phạm vi hiện tại:

- Tự động sửa mô hình BIM/CAD hoặc điều khiển phần mềm trên máy người dùng.
- Chạy lệnh hệ thống tùy ý, khởi động lại dịch vụ production hoặc tự triển khai.
- Thay thế toàn bộ nhân sự IT Support hoặc toàn bộ hệ thống quản trị hạ tầng.
- Hỗ trợ khách hàng bên ngoài, đa tổ chức hoặc mọi bài toán IT Helpdesk.
- Tự động mở rộng quyền tài liệu/công cụ dựa trên yêu cầu của người dùng.

## 8. Dữ liệu và yêu cầu chất lượng

Bộ dữ liệu mục tiêu gồm tài liệu phần mềm/plugin, hướng dẫn project, quy trình chẩn đoán và lịch sử sự cố. Mỗi nguồn cần có chủ đề, phiên bản áp dụng, nguồn gốc và quy tắc quyền rõ ràng.

Nếu chưa có dữ liệu nội bộ doanh nghiệp, sử dụng tài liệu công khai phù hợp và dữ liệu tổ chức mô phỏng. Các project, quyền, sự cố và ticket mô phỏng phải được gắn nhãn; không trình bày chúng như dữ liệu thật của Harmony.

Mỗi tình huống đánh giá cần xác định người dùng, quyền, câu hỏi, ngữ cảnh, nguồn được phép dùng và kết quả mong đợi. Nếu có công cụ, cần cố định dữ liệu trả về hoặc ghi trạng thái tại thời điểm thử nghiệm.

Yêu cầu xuyên suốt:

- Không để dữ liệu bị cấm lọt vào kết quả, prompt hoặc citation.
- Giữ file gốc riêng tư; không trả đường dẫn lưu trữ nội bộ cho trình duyệt.
- Bảo toàn nội dung revision/chunk và khả năng đối chiếu citation; không ghi đè nội dung đã phát hành.
- Tách dữ liệu tài liệu và kết quả công cụ khỏi chỉ dẫn điều khiển trợ lý.
- Lỗi kết nối hoặc xử lý phải có trạng thái rõ ràng, không lộ API key hoặc nội dung riêng tư.
- Khi thiếu bằng chứng, phân biệt kiến thức chung với thông tin xác nhận từ tài liệu hoặc công cụ.

## 9. Kế hoạch đánh giá

Đánh giá một phiên bản triển khai xác định theo [kế hoạch thực nghiệm](../specs/04-experiment-plan.md). Chỉ chấm các khả năng đã triển khai ở mốc đó; ghi rõ phần chưa có và các kiểm tra chưa thực hiện.

| Tiêu chí | Cách đánh giá |
| --- | --- |
| Độ đúng của retrieval | Recall@k, Precision@k, nDCG@k trên tập đoạn liên quan mà người dùng được phép đọc |
| Độ đúng của câu trả lời | Đối chiếu đáp án và nguồn; kiểm tra hướng dẫn có đúng điều kiện, phiên bản và bằng chứng không |
| Độ đúng của quyền truy cập | Kiểm tra trường hợp cho phép/từ chối, grant hết hạn và request vượt quyền; ghi riêng mọi trường hợp rò rỉ dữ liệu |
| Mức phù hợp của cá nhân hóa | Khi đã có chức năng: kiểm tra tài liệu ưu tiên và mức chi tiết theo cùng role/project/version đã xác định |
| Độ đúng của chọn Skill/công cụ | Khi đã có chức năng: chọn đúng quy trình/công cụ, tham số, quyền và xử lý kết quả/lỗi |
| Tỷ lệ tự xử lý thành công | Tỷ lệ tình huống nhân viên xác nhận giải quyết được bằng hướng dẫn mà không cần IT Support xử lý trực tiếp |
| Chất lượng chuyển tiếp | Ticket đủ thông tin cần thiết, gửi đúng nơi được phép, không trùng và không có dữ liệu vượt quyền |
| Tỷ lệ hoàn thành nhiệm vụ | Tỷ lệ tình huống đạt kết quả mong đợi, kể cả hỏi bổ sung hoặc chuyển tiếp đúng thay vì đưa kết luận sai |
| Độ trễ | Thời gian retrieval, thời gian tới token đầu tiên và tổng thời gian xử lý; tách phần chờ provider/công cụ khi đo được |

Để đánh giá mục tiêu nghiệp vụ, cần đo thời gian từ khi báo lỗi tới khi nhận hướng dẫn có thể thực hiện, số yêu cầu IT Support xử lý trực tiếp và số lần phải hỏi lại thông tin khi nhận ticket. Nếu muốn kết luận giảm thời gian chờ hoặc giảm tải IT Support, cần dữ liệu về quy trình hỗ trợ trước khi dùng Ruvie làm mốc đối chiếu. Không suy ra hiệu quả thực tế chỉ từ các tình huống mô phỏng.

Báo cáo phải ghi phiên bản mã, migration, dataset, LLM, embedding profile và thiết lập chạy. Không kết luận hiệu quả cá nhân hóa hoặc MCP từ một mốc mới chỉ có RAG cơ bản. Ngưỡng chất lượng và mục tiêu độ trễ cần được chốt trước từng đợt đánh giá; tài liệu này không đặt số liệu khi chưa có phép đo.

## 10. Kết quả mong đợi và cơ sở tài liệu

Kết quả mong đợi là một prototype giúp nhân viên Harmony tự xử lý các vấn đề phù hợp từ nguồn nội bộ và chuyển tiếp các vấn đề còn lại tới IT Support với hồ sơ đầy đủ. Prototype cần kiểm chứng khả năng tự xử lý, chất lượng hướng dẫn, quyền truy cập và chất lượng chuyển tiếp. Cá nhân hóa và công cụ được bổ sung theo từng mốc để phục vụ luồng hỗ trợ này.

Tài liệu này dựa trên mẫu đề bài và phần làm rõ bối cảnh, mục tiêu tự xử lý/chuyển ticket do người dùng cung cấp, đồng thời đối chiếu:

- [Product specification](../specs/01-product-spec.md): bối cảnh BIM/CAD, người dùng và phạm vi sản phẩm.
- [Architecture](../specs/02-architecture.md) và [access control](../specs/03-access-control.md): định hướng và ranh giới quyền.
- [README](../README.md): chức năng và cấu hình đang sử dụng.
- Mã active: `backend/ruvie/services/{projects,access,retrieval,chat,llm}.py`, `backend/ruvie/services/documents/`, `backend/ruvie/api/documents.py`, `backend/ruvie/models/projects.py` và `frontend/src/lib/i18n/`.
- [Visual specifications](../specs/visual/README.md): kiến trúc runtime, ERD và sequence.
- [Locale backlog](../specs/to-be/ui-localization-evolution.md) và [kế hoạch quản trị](../specs/to-be/admin-roadmap.md): yêu cầu tương lai đã ghi nhận.

Tài liệu định hình bài toán không thay thế feature spec, API contract hoặc kế hoạch triển khai chi tiết. Mọi khả năng mới cần được cụ thể hóa và kiểm chứng trước khi ghi nhận là đã hoàn thành.
