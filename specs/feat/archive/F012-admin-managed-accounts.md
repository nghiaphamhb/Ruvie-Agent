# F012 - Khởi tạo administrator và cấp tài khoản do admin quản lý

Trạng thái: Đã triển khai và kiểm chứng F012-001–F012-010; AC-01–AC-24 đạt.
Ngày lập: 2026-10-20.
Cập nhật: 2026-10-21.
Dự án: Ruvie Agent.

## Goal

Cho công ty quản lý việc cấp tài khoản trong Ruvie Agent. Hệ thống chưa có tài
khoản chỉ mở khởi tạo admin đầu tiên. Sau khởi tạo, chỉ admin được tạo thêm tài
khoản và chọn vai trò hệ thống user hoặc admin. Người dùng đăng nhập bằng tài
khoản được cấp; không tự đăng ký sau khi hệ thống đã có tài khoản.

Spec này mô tả hành vi cần đạt và thiết kế dự kiến để người dùng duyệt, chưa xác
nhận các hành vi đã tồn tại. Tạo spec không phải hoàn thành các task triển khai.

### Nguồn và phạm vi đã thống nhất

- [Định hướng tài khoản](../to-be/admin-managed-accounts.md): admin cấp tài khoản,
  chọn user/admin, giữ phiên của người cấp và không tự cấp quyền tài nguyên.
- [Backlog quản trị còn lại](../to-be/administrator-operations.md): lưu các phần
  chưa thực hiện, đặc biệt khôi phục khi không còn admin và tự đổi mật khẩu.
- [Bài toán sản phẩm](../../docs/problem-definition.md) và
  [đề xuất luận văn](../../docs/thesis-proposal-ru.md): quản trị phục vụ hoạt động
  hỗ trợ kỹ thuật nội bộ và tuân thủ quyền truy cập.
- [Kiến trúc hiện tại](../../specs/02-architecture.md),
  [hướng dẫn chạy](../../README.md) và
  [hướng dẫn database](../../docs/database-setup.md).

Backlog tài khoản ban đầu chỉ ưu tiên admin đã đăng nhập tạo thêm tài khoản.
Theo phạm vi đã duyệt khi lập F012, feature này bao gồm thêm khởi tạo admin đầu
tiên và đóng đăng ký công khai để có luồng sử dụng hoàn chỉnh trên database mới.
Khôi phục quyền quản trị cho database đã có user vẫn nằm ngoài phạm vi.

## User Story

- Là người khởi tạo Ruvie Agent khi chưa có tài khoản nào, tôi muốn tạo admin
  đầu tiên để bắt đầu quản trị hệ thống.
- Là admin đã đăng nhập, tôi muốn cấp tài khoản user hoặc admin để nhân sự được
  sử dụng ứng dụng với đúng vai trò hệ thống.
- Là người được cấp tài khoản, tôi muốn đăng nhập bằng thông tin đã nhận và chỉ
  sử dụng chức năng/tài nguyên mình được phép.
- Là admin đang cấp tài khoản, tôi muốn biết kết quả và giữ nguyên phiên hiện
  tại để tiếp tục công việc.

## Scope

### In

- Vai trò hệ thống có đúng hai giá trị: user và admin; lưu bền vững trong PostgreSQL.
- Đọc trạng thái cần khởi tạo; chỉ tạo admin đầu tiên khi database có 0 user.
- Chặn đăng ký công khai khi đã có ít nhất một user, kể cả user không hoạt động.
- Khởi tạo thành công tạo tài khoản admin và phiên đăng nhập của chính người khởi tạo.
- Admin tạo thêm tài khoản bằng tên, email, mật khẩu ban đầu và vai trò; mặc định user.
- Khu vực quản trị tối thiểu: trang Người dùng, form tạo tài khoản và kiểm tra tài
  khoản theo email chính xác khi cần xác minh kết quả. Không xây bộ quản trị đầy đủ.
- Kiểm tra quyền admin khi đọc thông tin quản trị và khi tạo tài khoản.
- Phản hồi phiên đăng nhập có vai trò hệ thống; giao diện dùng vai trò để hiển thị điều hướng.
- Ghi audit tạo tài khoản thành công, không ghi mật khẩu hoặc session secret.
- Bảo toàn phiên của admin khi tạo tài khoản; không sinh phiên cho tài khoản được cấp.
- Ba locale vi-VN, en-US, ru-RU; theme, bàn phím, focus và trạng thái mạng phù hợp.
- Migration, kiểm tra cạnh tranh trên PostgreSQL, hồi quy xác thực và cô lập tài liệu.

### Out

- Khôi phục hoặc chọn tài khoản admin cho database đã có user nhưng chưa có admin.
- Nâng/hạ vai trò, sửa thông tin, tạm ngừng/kích hoạt hoặc xóa tài khoản đã có.
- Project/group management và cấp membership, quyền tài liệu, model hoặc công cụ.
- Tự đổi mật khẩu, quên mật khẩu, reset mật khẩu thay user và bắt buộc đổi mật khẩu lần đầu.
- Email mời, gửi mật khẩu tự động, nhập CSV, tạo hàng loạt hoặc tự động tạo mật khẩu.
- Quản trị LLM/provider/proxy, ngôn ngữ tổ chức, ticket và dashboard vận hành.
- Đưa mô hình auth, token localStorage hoặc runtime của references vào active app.
- Thay đổi retrieval, nội dung revision/chunk, embedding profile hoặc cách đọc blob.
- Thêm thư viện router, UI kit, queue hoặc một hệ thống phân quyền tổng quát.

### Thuật ngữ và quyền hạn

| Khái niệm | Ý nghĩa trong F012 |
| --- | --- |
| Vai trò hệ thống | user hoặc admin; xác định quyền quản trị hệ thống |
| Vai trò project | BIM_CAD_SPECIALIST, DEVELOPER, IT_SUPPORT; không thay thế vai trò hệ thống |
| Quyền tài nguyên | Quyền đọc tài liệu hoặc dùng tài nguyên cụ thể; được kiểm tra riêng |
| Admin đầu tiên | Tài khoản tạo qua luồng khởi tạo khi database chưa có user |
| Admin được cấp thêm | Tài khoản được một admin tạo với vai trò admin; có cùng quyền trong phạm vi F012 |

Không bổ sung vai trò superadmin hoặc pending. Không cần tạo user rồi nâng quyền
để có admin mới. Vai trò admin không mặc nhiên cho phép đọc mọi tài liệu hoặc
hội thoại, không vượt qua DocumentAccessService.

## Flow

### 1. Hiện trạng được xác minh trước khi triển khai F012

| Thành phần trước F012 | Hành vi trước F012 | Phần F012 cần bổ sung/thay đổi |
| --- | --- | --- |
| backend/ruvie/models/auth.py — User | Có danh tính, password_hash, is_active; chưa có vai trò hệ thống | Thêm system_role tách khỏi roles/memberships của project |
| backend/ruvie/services/auth.py — AuthService.register | Tạo user và session; không kiểm tra hệ thống đã có user | Giới hạn thành khởi tạo admin đầu tiên, kiểm tra trong giao dịch |
| backend/ruvie/api/auth.py — POST /auth/register | Đăng ký công khai, trả phiên | Giữ đường dẫn, đổi điều kiện nghiệp vụ sang khởi tạo một lần |
| backend/ruvie/contracts/auth.py — AuthUser | Chỉ trả id và display_name | Bổ sung system_role từ dữ liệu backend |
| frontend/src/App.svelte | Quản lý phiên, nhận kết quả đăng nhập/đăng ký, sở hữu workspace theo tài khoản | Đọc trạng thái khởi tạo và truyền vai trò; không nhận phiên mới từ admin tạo tài khoản |
| frontend/src/lib/features/auth/AuthPage.svelte | Chuyển login/register theo query và liên kết | Chỉ mở form khởi tạo khi server xác nhận cần khởi tạo |
| frontend/src/lib/pages/WorkspacePage.svelte | Ghép layout/features, sở hữu state theo phiên | Ghép trang admin nhưng giữ owners chat/documents/LLM khi chuyển view |
| backend/ruvie/services/audit.py — AuditEventWriter.append | Thêm event vào giao dịch của caller | Tái sử dụng ghi tạo tài khoản; không cần schema audit mới |
| frontend/vite.config.ts | Chưa proxy /admin | Proxy API /admin về backend khi phát triển |

Không mô tả trang quản trị, quyền admin hoặc khởi tạo một lần là chức năng hiện
đã triển khai.

Bảng trên ghi nhận nền tảng khi lập spec. Tiến độ sau triển khai từng task được
cập nhật tại mục Trạng thái triển khai ở cuối tài liệu.

### 2. Quy tắc chung về thông tin tài khoản

| Trường | Quy tắc |
| --- | --- |
| display_name | Bắt buộc; trim đầu/cuối; dài 1–255 ký tự sau trim |
| email | Bắt buộc; trim, chuẩn hóa chữ thường; dài 3–320; giữ kiểm tra email hiện có; duy nhất không phân biệt hoa/thường |
| password | Bắt buộc; dài 12–128 ký tự Unicode theo quy tắc hiện có; không trim, đổi hoa/thường hoặc cắt chuỗi |
| password_confirmation | Chỉ ở form khởi tạo đầu tiên; bắt buộc khớp password; không gửi lên API |
| system_role | Luồng khởi tạo không nhận từ client; luồng admin cấp tài khoản chọn user hoặc admin, mặc định user |

Không đổi chính sách đăng nhập của tài khoản cũ để áp điều kiện độ dài mật khẩu
mới lên thao tác đăng nhập. Email của tài khoản không hoạt động vẫn được xem là đã tồn tại.

Tên, email, mật khẩu và vai trò nhận kiểu dữ liệu nghiêm ngặt. Từ chối trường lạ
như actor_user_id, memberships, document_ids hoặc scopes. Riêng system_role là
lựa chọn hợp lệ trong yêu cầu do admin gửi, không phải bằng chứng quyền của người gửi.

### 3. EPC — Khởi tạo admin đầu tiên

Quy ước: lục giác là sự kiện/trạng thái; ô bo góc là hoạt động; vòng tròn XOR
chỉ chọn một nhánh. Nhãn trong ngoặc vuông xác định bên thực hiện. Nhánh lỗi kết
thúc lần thử hiện tại; điều kiện thử lại được mô tả sau sơ đồ.

~~~mermaid
flowchart TD
    opened{{"Ứng dụng được mở khi chưa đăng nhập"}}
    inspect("[Hệ thống] Đọc trạng thái khởi tạo")
    stateGate(("XOR"))
    unavailable{{"Chưa xác định được trạng thái; hiển thị lỗi và Thử lại"}}
    initialized{{"Đã có tài khoản; đăng ký công khai đóng"}}
    login("[Hệ thống] Hiển thị Đăng nhập")
    loginReady{{"Người dùng có thể đăng nhập"}}
    empty{{"Chưa có tài khoản; được phép khởi tạo"}}
    fill("[Người khởi tạo] Nhập tên, email, mật khẩu và xác nhận")
    submitted{{"Yêu cầu khởi tạo đã được gửi"}}
    create("[Hệ thống] Kiểm tra lại điều kiện và tạo admin cùng phiên")
    createGate(("XOR"))
    invalid{{"Thông tin không hợp lệ; cần sửa trước khi gửi lại"}}
    closed{{"Người khác đã khởi tạo; cần chuyển về Đăng nhập"}}
    failed{{"Khởi tạo thất bại; cần kiểm tra lại trạng thái trước khi thử lại"}}
    created{{"Admin và phiên đã được tạo; đăng ký công khai đóng"}}
    enter("[Hệ thống] Đăng nhập admin và mở Quản trị — Người dùng")
    ready{{"Admin đầu tiên có thể cấp thêm tài khoản"}}

    opened --> inspect --> stateGate
    stateGate --> unavailable
    stateGate --> initialized
    initialized --> login --> loginReady
    stateGate --> empty
    empty --> fill --> submitted --> create --> createGate
    createGate --> invalid
    createGate --> closed
    createGate --> failed
    createGate --> created
    created --> enter --> ready

    classDef event fill:#eef2ff,stroke:#6366f1,color:#111827
    classDef activity fill:#ecfdf5,stroke:#059669,color:#111827
    classDef connector fill:#fff7ed,stroke:#d97706,color:#111827
    class opened,unavailable,initialized,loginReady,empty,submitted,invalid,closed,failed,created,ready event
    class inspect,login,fill,create,enter activity
    class stateGate,createGate connector
~~~

### 4. Hành vi khởi tạo và đóng đăng ký

1. Khi chưa có phiên, giao diện đọc trạng thái khởi tạo từ server. Trong lúc đọc,
   hiển thị trạng thái đang kiểm tra; chưa cho gửi form khởi tạo.
2. Nếu database có 0 user, hiển thị **Tạo tài khoản quản trị viên**. Form có tên,
   email, mật khẩu và xác nhận mật khẩu; không có bộ chọn vai trò.
3. Người khởi tạo gửi form. Hệ thống kiểm tra Origin, dữ liệu và kiểm tra lại
   điều kiện 0 user trong giao dịch được bảo vệ trước yêu cầu đồng thời.
4. Nếu vẫn chưa có user, hệ thống tạo user với system_role=admin, tạo phiên và
   audit; tất cả cùng thành công hoặc cùng rollback.
5. Thành công: đặt cookie phiên hiện có, xóa các trường mật khẩu, nhận danh tính
   admin từ server và mở **Quản trị → Người dùng**.
6. Khi đã có ít nhất một user, người chưa đăng nhập chỉ thấy **Đăng nhập**.
   Bỏ lời mời/liên kết đăng ký công khai; không thêm công tắc bật lại đăng ký.
7. URL có form=register, Back/Forward hoặc form khởi tạo mở từ trước không tạo
   thêm tài khoản sau khởi tạo. Giao diện đưa về login và thông báo phù hợp.
8. Nếu nhiều người gửi đồng thời, chỉ một yêu cầu tạo được admin và session.
   Các yêu cầu còn lại nhận setup_already_completed và không nhận cookie phiên mới.
9. Khi lỗi lưu, rollback cả user/session/audit. Giao diện đọc lại trạng thái
   trước khi cho khởi tạo lại; không mặc định rằng database vẫn rỗng.
10. Khi mất phản hồi, không tự gửi lại. Đọc lại trạng thái: nếu đã có tài khoản,
    đưa về đăng nhập để người khởi tạo dùng thông tin vừa nhập. Không kết luận
    rằng tài khoản được tạo bởi yêu cầu của chính người đó chỉ dựa trên trạng thái.
11. Restart server, logout hoặc đổi trình duyệt không mở lại đăng ký khi database
    còn user. Không phân biệt user active/inactive khi quyết định đã khởi tạo.

GET trạng thái chỉ phục vụ giao diện. Điều kiện từ chối/tạo tài khoản phải được
kiểm tra tại thao tác ghi, không tin kết quả kiểm tra cũ hoặc trạng thái client.

### 5. EPC — Admin tạo user hoặc admin

~~~mermaid
flowchart TD
    needed{{"Có nhu cầu cấp tài khoản"}}
    prepare("[Admin] Mở Tạo tài khoản, nhập thông tin và chọn user hoặc admin")
    submitted{{"Yêu cầu cấp tài khoản đã được gửi"}}
    validate("[Hệ thống] Kiểm tra phiên, quyền admin, CSRF, dữ liệu và email")
    validationGate(("XOR"))
    rejected{{"Yêu cầu bị từ chối; lý do đã được thông báo"}}
    valid{{"Yêu cầu đáp ứng điều kiện cấp tài khoản"}}
    create("[Hệ thống] Tạo tài khoản và ghi audit")
    creationGate(("XOR"))
    failed{{"Lưu thất bại; không có tài khoản tạo dở"}}
    created{{"Tài khoản được tạo đúng vai trò; phiên admin được giữ nguyên"}}
    deliver("[Admin] Bàn giao thông tin qua kênh nội bộ phù hợp")
    completed{{"Người nhận đã có thông tin đăng nhập"}}

    needed --> prepare --> submitted --> validate --> validationGate
    validationGate --> rejected
    validationGate --> valid
    valid --> create --> creationGate
    creationGate --> failed
    creationGate --> created
    created --> deliver --> completed

    classDef event fill:#eef2ff,stroke:#6366f1,color:#111827
    classDef activity fill:#ecfdf5,stroke:#059669,color:#111827
    classDef connector fill:#fff7ed,stroke:#d97706,color:#111827
    class needed,submitted,rejected,valid,failed,created,completed event
    class prepare,validate,create,deliver activity
    class validationGate,creationGate connector
~~~

### 6. Admin tạo tài khoản user

1. Admin chọn **Quản trị → Người dùng** rồi mở **Tạo tài khoản**.
2. Mỗi lần mở form mới, tên/email/mật khẩu rỗng; vai trò mặc định là **Người dùng**.
3. Admin nhập thông tin. Form tạo thêm tài khoản không yêu cầu xác nhận mật khẩu.
   Có điều khiển hiện/ẩn mật khẩu khi nhập, tái sử dụng PasswordField.
4. Admin gửi. Giao diện kiểm tra đầu vào, focus trường lỗi đầu tiên và hiển thị
   lỗi cạnh trường. Backend tiếp tục kiểm tra độc lập.
5. Khi đang gửi, khóa gửi lặp và sửa dữ liệu của lần gửi đó; không tự retry POST.
   Form không cho đóng bằng Hủy/Escape trong trạng thái này. Logout hoặc hết phiên
   vẫn được xử lý; đóng trình duyệt không bảo đảm hủy thao tác đã đến server.
6. Hệ thống kiểm tra người gửi còn active và có system_role=admin, Origin và CSRF
   hợp lệ. Không tin role hoặc actor ID do trình duyệt khai.
7. Hệ thống tạo tài khoản active với system_role=user và ghi audit cùng giao dịch.
   Không tạo auth session cho tài khoản mới; không thay cookie hoặc CSRF của admin.
8. Thành công: đóng/reset form, xóa mật khẩu và hiển thị tên/email/vai trò của tài
   khoản vừa tạo. Thông báo dùng khóa dịch an toàn; không chứa mật khẩu.
9. Admin bàn giao thông tin đăng nhập qua kênh nội bộ phù hợp. Ứng dụng không gửi
   email và không lưu bản sao mật khẩu để admin xem lại.
10. Người nhận đăng nhập trong phiên khác hoặc sau khi admin đăng xuất. User vào
    workspace thông thường và không được truy cập khu vực/API quản trị.

### 7. Admin tạo thêm tài khoản admin

Dùng cùng luồng trên, nhưng admin chọn **Quản trị viên** trước khi gửi.

- Hiển thị giải thích ngay cạnh bộ chọn: tài khoản admin có quyền quản lý người
  dùng, tạo thêm admin và sử dụng các chức năng quản trị được cung cấp.
- Không tạo hộp phê duyệt hoặc một vai trò cấp cao khác. Admin hiện tại được
  tạo trực tiếp tài khoản admin trong cùng form.
- Backend chỉ chấp nhận system_role=user/admin sau khi xác minh người gửi là admin.
- Phản hồi thành công và thẻ kết quả phải nêu rõ vai trò **Quản trị viên**.
- Khi đăng nhập sau đó, admin mới có thể mở quản trị và tạo thêm user hoặc admin.
  F012 không tạo quan hệ admin chính/admin phụ để hạn chế luồng này.

User mới và admin mới đều không tự nhận Membership, AccessGrant hoặc vai trò
project. Quyền quản trị không được đưa vào readable-document predicate như một
điều kiện bỏ qua kiểm tra tài liệu.

### 8. Lỗi, hủy và kết quả chưa xác định

- Hủy trước khi gửi: đóng form, xóa mật khẩu và không tạo request.
- Lỗi 422/409: giữ tên/email/vai trò để sửa, xóa mật khẩu sau phản hồi của lần gửi;
  admin nhập lại mật khẩu trước lần gửi mới.
- Lỗi 401: xử lý hết phiên theo cơ chế hiện tại; xóa state quản trị và secret.
- Lỗi 403: không tự đăng xuất. Hiển thị mã lỗi an toàn; nếu quyền admin đã mất,
  rời khu vực quản trị. Lỗi Origin/CSRF không bị diễn giải thành mất quyền admin.
- Lỗi lưu đã xác định rollback: báo thất bại an toàn; không báo tạo thành công.
- Timeout, mất kết nối hoặc hủy nhận phản hồi: xem kết quả là **chưa xác định**.
  Không tự gửi lại và không khẳng định tài khoản chưa được tạo.
- Cho admin kiểm tra email chính xác đã gửi. Nếu tìm thấy tài khoản, hiển thị
  thông tin hiện có để đối chiếu; không khẳng định lần gửi trước đã thành công.
  Không ghi đè tên, vai trò hoặc mật khẩu của tài khoản đó.
- Nếu không tìm thấy, có thể cho nhập lại mật khẩu và gửi lại bằng thao tác chủ
  động. Yêu cầu cũ có thể hoàn tất muộn; unique email vẫn phải ngăn tạo bản trùng.
- Response muộn sau logout/đổi tài khoản không được cập nhật state của phiên mới.
- Mật khẩu không vào URL, localStorage, sessionStorage, toast, audit hoặc log.

### 9. Điều hướng và trải nghiệm

- Admin thấy mục **Quản trị** trong menu tài khoản. User không thấy mục này.
- Trang quản trị tối thiểu có tiêu đề **Người dùng**, nút **Tạo tài khoản**, form
  tạo và vùng kết quả/kiểm tra email. Chưa xây danh sách tìm kiếm tổng quát.
- Dự kiến dùng view **admin-users** trong workspace, phản ánh qua query
  **?view=admin-users**. Không thêm router hoặc đổi sang SvelteKit.
- Reload/Back/Forward ở view này vẫn kiểm tra session/role. User truy cập URL
  trực tiếp nhận thông báo không có quyền và về workspace, không được gửi request
  tạo tài khoản.
- Các request quản trị vẫn được bảo vệ server-side khi bỏ qua điều hướng UI.
- Chuyển qua lại chat/admin không remount workspace hoặc mất draft/chat/upload
  đang chạy. Mật khẩu trong form admin được xóa khi rời view; không giữ như draft.
- Hết phiên/logout hủy đăng ký nhận kết quả và xóa dữ liệu tài khoản theo cơ chế
  workspace; thao tác này không hứa rollback request đã đến server.
- Tái sử dụng theme, locale, toast và điều khiển hiện có; không thay visual style
  của toàn ứng dụng. Form đủ nhãn, focus lỗi, trạng thái đang gửi và thông báo đọc
  được bằng screen reader. Hủy/đóng trả focus về nút mở; hỗ trợ sáng/tối và màn hình hẹp.
- Ngôn ngữ UI đổi thì nhãn/lỗi đang hiển thị đổi theo; không mất dữ liệu đang nhập.

### 10. Hợp đồng HTTP dự kiến

Các endpoint setup/admin đã có backend qua F012-003/F012-005. Các hợp đồng dưới
đây tiếp tục được nghiệm thu cùng giao diện và các kiểm tra tích hợp còn lại.

| Endpoint | Quyền/điều kiện | Request | Response thành công |
| --- | --- | --- | --- |
| GET /auth/setup | Public; chỉ trả trạng thái khởi tạo | Không có body | 200, {requires_initial_admin: boolean} |
| POST /auth/register | Origin hợp lệ; database có 0 user tại thao tác ghi | display_name, email, password; không nhận system_role | 201, AuthResponse của admin đầu tiên và cookie phiên |
| POST /auth/login | Giữ luồng đăng nhập hiện tại | email, password | 200, AuthResponse có system_role và cookie |
| GET /auth/session | Phiên active | Cookie | 200, AuthResponse có system_role mới nhất từ DB |
| POST /admin/users | Phiên admin, Origin, CSRF | display_name, email, password, system_role; mặc định user khi bỏ trường | 201, {user: AdminAccountSummary}; không đặt cookie |
| GET /admin/users?email=... | Phiên admin; email chính xác bắt buộc | Email được chuẩn hóa; không hỗ trợ wildcard | 200, {users: []} hoặc {users: [AdminAccountSummary]} |

**AuthResponse** giữ cấu trúc hiện có và bổ sung vai trò vào user:

~~~json
{
  "user": {
    "id": "account-id",
    "display_name": "Nguyễn An",
    "system_role": "admin"
  },
  "csrf_token": "current-session-csrf"
}
~~~

**AdminAccountSummary** chỉ dành cho phản hồi quản trị: id, display_name, email,
system_role, is_active. Ví dụ yêu cầu admin cấp thêm tài khoản:

~~~json
{
  "display_name": "Trần Bình",
  "email": "binh@example.test",
  "password": "example-initial-password",
  "system_role": "user"
}
~~~

Giá trị trong ví dụ chỉ là dữ liệu giả. Response tạo tài khoản không có password,
password_hash, csrf_token hoặc token đăng nhập cho người nhận.

Lỗi dùng cấu trúc **{detail: {code, fields?}}**. fields chỉ chứa tên trường và
mã lỗi đã định nghĩa; không trả raw input hoặc nội dung exception.

| HTTP | code dự kiến | Ý nghĩa |
| --- | --- | --- |
| 401 | authentication_required | Chưa đăng nhập, phiên hết hạn hoặc user không active |
| 403 | admin_required | Đã xác thực nhưng không có quyền admin |
| 403 | origin_not_allowed / csrf_invalid | Kiểm tra request ghi không đạt |
| 409 | setup_already_completed | Đã có user khi xử lý yêu cầu khởi tạo |
| 409 | email_taken | Email đã tồn tại trong luồng admin cấp tài khoản |
| 422 | validation_error | Trường không hợp lệ, role lạ hoặc trường dư; có thể kèm fields |
| 503 | setup_unavailable | Không đọc được trạng thái khởi tạo; không mặc định database rỗng |
| 500 | account_creation_failed | Thao tác tạo/lưu thất bại; không lộ lỗi DB hoặc password |
| 503 | account_lookup_unavailable | Không xác minh được tài khoản theo email |

Không bắt buộc đổi mọi lỗi login/logout hiện có sang cấu trúc mới. Auth client
cần phân biệt setup_already_completed với email_taken thay vì suy luận chỉ từ 409.
Trường hợp input không hợp lệ vẫn luôn phải được redaction, kể cả khi request bị
từ chối trước khi chạy service.

GET setup, session và response quản trị dùng **Cache-Control: no-store**.
Không trả số lượng user, email admin, proxy hoặc cấu hình nhạy cảm ở endpoint public.
GET lookup trả tối đa một tài khoản, không trả mật khẩu và không có tác dụng đăng nhập.

### 11. Dữ liệu, giao dịch và ranh giới dự kiến

#### Vai trò và migration

- Bổ sung **User.system_role** kiểu chuỗi, NOT NULL, default/server default là user.
- Check constraint **ck_users_system_role** chỉ cho user/admin. Không dùng bảng
  RoleCode của project để xác định admin hệ thống.
- Dự kiến migration mới **0010_users_system_role.py**, nối sau
  **0009_users_email_lower_unique**. Nếu head thay đổi trước khi code, điều chỉnh
  tên/parent theo head thực tế; không sửa migration đã áp dụng.
- Tài khoản đã có nhận role user. Không tự nâng tài khoản đầu tiên, email cụ thể
  hoặc mọi tài khoản hiện có thành admin.
- Không sửa mật khẩu, active state, membership, grants, revision hoặc chunk khi migrate.
- Giữ unique index lower(email); duplicate đồng thời được xử lý từ constraint DB,
  không chỉ dựa vào một truy vấn kiểm tra trước khi insert.

**Giới hạn chuyển đổi:** database hiện có user sẽ không được khởi tạo và cũng
không tự có admin sau migration. Nếu thiếu admin, việc đưa feature vào sử dụng
bị chặn cho đến khi một quy trình cấp/khôi phục admin riêng được duyệt. F012 không
thêm lệnh nâng quyền ngầm hoặc xóa dữ liệu để đi vòng. Điều kiện rollout này phải
ghi trong hướng dẫn và báo rõ khi nghiệm thu trên dữ liệu cũ.

#### Khởi tạo một lần

- AuthService giữ quyền sở hữu use case khởi tạo. Dự kiến bổ sung
  get_setup_status() và đổi register() thành tạo admin đầu tiên.
- Dùng khóa giao dịch PostgreSQL chung cho khởi tạo, ví dụ advisory transaction
  lock có khóa cố định. Sau khi giữ khóa mới kiểm tra đã có user rồi insert.
- Không dùng SELECT FOR UPDATE trên tập user rỗng như cách bảo vệ duy nhất.
  Không sao chép thuật toán đếm user sau insert trong legacy như một bảo đảm cạnh tranh.
- Tạo User, stage session và append audit trong một giao dịch. Lỗi bất kỳ bước
  nào rollback toàn bộ. Chỉ đặt cookie sau commit thành công.
- register() không nhận role; service gán admin. Kết quả giữ dạng có cấu trúc
  RegisteredAccount/CreatedSession hiện có; HTTP serialization thuộc api/auth.py.

#### Admin cấp tài khoản

- Dự kiến service **AdminAccountService** trong services/admin.py, chỉ phụ trách
  tạo và lookup tài khoản. Không thêm repository/factory hoặc lớp auth mới.
- require_admin(actor_user_id) tra user active/system_role từ DB; có thể tái sử
  dụng trong dependency và trước thao tác service. Không tin quyền cache phía client.
- create_account(actor_user_id, command) kiểm tra lại admin trong giao dịch ghi,
  kiểm tra dữ liệu, hash mật khẩu bằng hash_password hiện có, tạo User và audit.
- Khi cần bảo đảm quyền không thay đổi giữa kiểm tra và commit, giữ khóa hàng actor
  trong giao dịch ghi. Không dùng role từ request để xác định actor.
- Kết quả là CreatedAccount chứa metadata an toàn; không gọi AuthService.create_session
  cho user mới và không gọi đường nhận phiên đăng ký trong frontend.
- lookup_account(actor_user_id, email) kiểm tra quyền và chỉ tìm email chuẩn hóa
  chính xác. Không tái sử dụng endpoint public để lộ danh sách tài khoản.

#### Request, audit và quyền tài liệu

- dependencies.py cung cấp get_admin_user_id dựa trên danh tính phiên và service
  xác minh admin. Route chỉ kiểm tra HTTP, gọi service và serialize.
- api/security.py tái sử dụng check_origin/verify_csrf và bổ sung hoặc dùng chung
  cơ chế redaction cho request có mật khẩu. Auth/register và admin/users phải có
  lỗi validation an toàn, kể cả invalid JSON, kiểu lạ hoặc trường dư.
- api/admin.py không query tài liệu/chunk, không tự cấp quyền project hoặc quyết
  định tài nguyên được đọc. main.py chỉ đăng ký router mới.
- Tái sử dụng AuditEventWriter.append, action dự kiến account.bootstrap/account.create,
  resource_type=user, resource_id là tài khoản mới; outcome=allow và reason là
  mã an toàn, chẳng hạn created_as_user/created_as_admin.
- Bootstrap audit có actor là admin vừa tạo sau flush. Tạo qua quản trị có actor
  là admin đang thao tác. Audit và User cùng giao dịch; lỗi audit rollback tạo tài khoản.
- Không giả actor cho request chưa xác thực. F012 không mở rộng audit thành hệ
  thống giám sát mọi lỗi hoặc thêm UI xem audit.
- Không sửa DocumentAccessService hoặc readable-document predicate để cho admin
  đọc toàn bộ tài liệu. Các bài kiểm tra quyền phải bao gồm cả admin mới.

### 12. Tái sử dụng và thích nghi từ references

| Nguồn | Hành vi tham khảo | Điều chỉnh cho F012 |
| --- | --- | --- |
| references/backend/ruvie/routers/auths.py — signup_handler, signup | Onboarding admin đầu tiên và kiểm tra điều kiện đăng ký | Chỉ cho tạo khi có 0 user; bảo vệ cạnh tranh bằng giao dịch PostgreSQL; không nhận enable_signup để mở lại |
| references/backend/ruvie/routers/auths.py — add_user | Admin nhập thông tin và chọn role | Chỉ user/admin; giữ cookie session/CSRF active; không trả token của người nhận và không gán nhóm mặc định |
| references/backend/ruvie/utils/auth.py — get_admin_user | Giới hạn thao tác cho admin | Đọc role/active từ PostgreSQL qua identity hiện tại; không port JWT/header auth |
| references/src/lib/components/admin/Users/UserList/AddUserModal.svelte | Form tên/email/mật khẩu/role; reset form, loading và phản hồi | Thích nghi Svelte 5, i18n và theme hiện có; bỏ CSV, pending, localStorage.token và phụ thuộc legacy |
| references/src/routes/auth/+page.svelte | Chọn màn hình onboarding/login | Dùng trạng thái server; đóng đăng ký sau lần đầu kể cả URL/Back/Forward |

Ưu tiên tái sử dụng active code: password hash/verify, RegisterRequest validators,
session/cookie, PasswordField, toast, i18n, layout và state disposal. Chỉ port phần
legacy phù hợp; không import, chạy hoặc sửa references.

## Edge Cases

| Trường hợp | Hành vi yêu cầu | Kiểm chứng chính |
| --- | --- | --- |
| Database rỗng, nhiều yêu cầu khởi tạo với email khác nhau | Một admin và một session bootstrap; các yêu cầu còn lại bị chặn | Integration PostgreSQL với các request thực sự đồng thời |
| Tạo user trong lúc trạng thái setup phía client còn cũ | Kết quả POST quyết định; không tạo admin thứ hai qua public register | Kiểm tra form mở sẵn và gọi API trực tiếp |
| Chỉ có user inactive hoặc user không phải admin | Đăng ký vẫn đóng | Setup service/API và truy cập URL register |
| Đọc setup lỗi | Báo không kiểm tra được và cho Thử lại; không tự mở khởi tạo | Fake lỗi DB và kiểm tra UI |
| Dữ liệu nhập có password/token giả trong trường lạ | Từ chối và chỉ trả mã lỗi an toàn | Kiểm tra body lỗi, log được capture và cookie |
| Hai admin tạo cùng email khác hoa/thường | Một tài khoản duy nhất; request còn lại email_taken | PostgreSQL + unique index |
| Email trùng tài khoản inactive | Báo trùng; không kích hoạt hoặc đổi password/role tài khoản cũ | So sánh dữ liệu trước/sau |
| Session mất hiệu lực hoặc quyền admin thay đổi sau khi mở form | Không tạo tài khoản; xử lý 401/403 đúng nguyên nhân | Sửa quyền trong fixture giữa hai bước |
| Client giả user_id, role actor hoặc quyền project | Từ chối trường dư; quyền actor chỉ lấy từ phiên | API test truy cập trực tiếp |
| Mất phản hồi tạo tài khoản | Kết quả chưa xác định; không retry tự động; lookup email có bảo vệ | Browser/API mock request hoàn tất muộn |
| User mới được tạo nhưng chưa có quyền project | Đăng nhập được; không đọc nội dung riêng tư hoặc nhận citation vượt quyền | Retrieval/chat isolation với hai role |
| Lỗi hash, insert, stage session, audit hoặc commit | Rollback; không có tài khoản/session/audit tạo dở | Fault injection và kiểm tra dữ liệu |
| Tạo tài khoản thành công khi admin đang chat/upload | Phiên, CSRF, draft và work đang chạy vẫn thuộc admin cũ | Browser lifecycle check |
| Logout/đổi tài khoản khi request đang chạy | Xóa state; bỏ qua response cũ, không hiển thị cho phiên mới | Browser delayed response |
| Hủy form hoặc chuyển view trước khi gửi | Không có POST; mật khẩu bị xóa | Kiểm tra request count và mở lại form |
| Database cũ chưa có admin sau migration | Không nâng quyền ngầm, không mở signup; ghi rõ rollout bị chặn | Migration/data preservation test |

## Acceptance Criteria

Các mục dưới đây đã được đối chiếu với bằng chứng kiểm chứng tại cuối tài liệu.

- [x] AC-01: Database có 0 user hiển thị Tạo tài khoản quản trị viên với xác nhận mật khẩu và không có bộ chọn role.
- [x] AC-02: Bootstrap gán role admin phía server; tạo account, session và audit cùng giao dịch; thành công đăng nhập và mở Người dùng.
- [x] AC-03: Bootstrap cạnh tranh với các email khác nhau chỉ tạo một tài khoản và một phiên; yêu cầu còn lại không nhận phiên mới.
- [x] AC-04: Có bất kỳ user nào thì public register bị chặn; URL, form cũ, Back/Forward, restart và logout không mở lại đăng ký.
- [x] AC-05: Setup lỗi không bị hiểu là database rỗng; UI có trạng thái lỗi và Thử lại.
- [x] AC-06: Login/session trả system_role từ DB; user thường không thấy và không dùng được quản trị, kể cả API trực tiếp.
- [x] AC-07: Admin tạo được cả user và admin trong cùng form; default là user và lựa chọn admin có giải thích quyền.
- [x] AC-08: Tài khoản được cấp đăng nhập được với mật khẩu ban đầu; admin mới có thể tiếp tục cấp cả hai loại tài khoản.
- [x] AC-09: Tạo thêm tài khoản không phát session của người nhận, không đổi cookie/CSRF hoặc danh tính phiên admin.
- [x] AC-10: Input được chuẩn hóa/kiểm tra đúng giới hạn; password giữ nguyên; role lạ và trường dư bị từ chối.
- [x] AC-11: Email trùng, kể cả inactive/khác hoa thường/đồng thời, không tạo bản trùng và không đổi dữ liệu tài khoản đã có.
- [x] AC-12: Request ghi thiếu/sai Origin hoặc CSRF không tạo tài khoản; hết phiên hoặc không còn admin bị chặn.
- [x] AC-13: Lỗi validation/internal không trả password, password_hash, raw input hoặc SQL params; audit/log không có secret.
- [x] AC-14: Lỗi lưu/audit/session bootstrap rollback toàn bộ phần tạo dở; không đặt cookie thành công khi transaction lỗi.
- [x] AC-15: Lookup chỉ admin dùng được, yêu cầu email chính xác, trả tối đa một account summary và không có secret.
- [x] AC-16: Mất phản hồi không tự retry POST; UI phân biệt chưa xác định với thất bại và hỗ trợ kiểm tra email.
- [x] AC-17: Hủy/success/rời view/logout xóa password trong form; state không tồn tại trong browser storage.
- [x] AC-18: Response muộn không cập nhật phiên đã logout hoặc tài khoản khác; 403 không mặc nhiên logout.
- [x] AC-19: Chuyển admin/chat không remount owners hoặc làm mất draft/upload; tạo user không gọi acceptSession.
- [x] AC-20: User/admin mới không có membership/grant tự sinh; cả hai bị chặn khỏi nội dung/citation không được phép.
- [x] AC-21: Migration giữ nguyên user cũ, password, active state và quyền tài nguyên; default user, không nâng quyền ngầm.
- [x] AC-22: Ba locale, sáng/tối, màn hình hẹp, keyboard/focus và lỗi trường hoạt động nhất quán.
- [x] AC-23: Bộ test đăng ký cũ được cập nhật theo bootstrap-only mà vẫn giữ kiểm tra cookie, rollback, email và cô lập.
- [x] AC-24: Hướng dẫn ghi rõ điều kiện database cũ thiếu admin, giới hạn feature và cách chạy các kiểm tra thực tế.

## Tasks

### Danh sách tệp dự kiến

Đây là phạm vi code dự kiến để duyệt, không phải danh sách tệp đã thay đổi.
Cột chức năng nêu trách nhiệm và điểm vào chính. Không tạo sẵn module rỗng cho
các chức năng quản trị thuộc backlog.

#### Backend và database

| Tệp | Thao tác dự kiến | Chức năng/điểm vào |
| --- | --- | --- |
| backend/ruvie/models/auth.py | Sửa | User.system_role và check constraint |
| backend/migrations/versions/0010_users_system_role.py | Tạo | Thêm cột/constraint; giữ dữ liệu cũ; upgrade/downgrade |
| backend/ruvie/contracts/auth.py | Sửa | SetupStatusResponse; AuthUser.system_role; giữ RegisterRequest không nhận role |
| backend/ruvie/contracts/admin.py | Tạo | CreateAccountRequest, AdminAccountSummary, CreateAccountResponse, AccountLookupResponse |
| backend/ruvie/services/auth.py | Sửa | get_setup_status(); register() bootstrap-only; giữ password/session helpers |
| backend/ruvie/services/admin.py | Tạo | AdminAccountService.require_admin(), create_account(), lookup_account(); kết quả có cấu trúc |
| backend/ruvie/dependencies.py | Sửa | get_admin_user_id() dựa trên identity/session đáng tin cậy và service |
| backend/ruvie/api/security.py | Sửa | Tái sử dụng Origin/CSRF; dùng chung redaction cho request tài khoản chứa mật khẩu |
| backend/ruvie/api/auth.py | Sửa | GET setup, POST register bootstrap-only, serialize system_role và lỗi an toàn |
| backend/ruvie/api/admin.py | Tạo | POST/GET /admin/users; gọi service, encode HTTP; không sở hữu business rules |
| backend/ruvie/main.py | Sửa | Đăng ký admin router |
| backend/ruvie/services/audit.py | Tái sử dụng | AuditEventWriter.append; chưa cần đổi schema hoặc thêm hệ thống audit riêng |

#### Frontend

| Tệp | Thao tác dự kiến | Chức năng/điểm vào |
| --- | --- | --- |
| frontend/src/App.svelte | Sửa | Đọc setup cho người chưa đăng nhập; nhận role từ session; chỉ bootstrap/login mới nhận phiên |
| frontend/src/lib/features/auth/auth-api.ts | Sửa | AuthUser.system_role, getSetupStatus(), xử lý setup_already_completed |
| frontend/src/lib/features/auth/auth-form.ts | Sửa có giới hạn | Tách helper validateAccountIdentity để dùng chung tên/email/password; validateRegistration vẫn kiểm tra confirmation |
| frontend/src/lib/features/auth/AuthPage.svelte | Sửa | Trạng thái setup/loading/error; giới hạn mode và URL đăng ký |
| frontend/src/lib/features/auth/RegisterForm.svelte | Sửa | Nhãn khởi tạo admin; giữ xác nhận mật khẩu và cleanup |
| frontend/src/lib/pages/WorkspacePage.svelte | Sửa | Ghép AdminPage, quản lý admin view/URL và vòng đời state; giữ owners hiện có |
| frontend/src/lib/pages/AdminPage.svelte | Tạo | Trang mỏng ghép panel quản trị; không trực tiếp gọi fetch hoặc chứa nghiệp vụ |
| frontend/src/lib/features/admin/AccountsPanel.svelte | Tạo | Tiêu đề, mở form, kết quả và kiểm tra email; không xây CRUD đầy đủ |
| frontend/src/lib/features/admin/CreateAccountForm.svelte | Tạo | Các trường/role, validation, focus, loading và password local |
| frontend/src/lib/features/admin/admin-api.ts | Tạo | createAccount(), lookupAccount(); safe errors và CSRF; không nhận phiên mới |
| frontend/src/lib/features/admin/admin-form.ts | Tạo | validateCreateAccount(); dùng helper identity, bổ sung role |
| frontend/src/lib/features/admin/admin-state.svelte.ts | Tạo | createAdminState(); trạng thái submit/unknown/lookup, disposal và stale response guard |
| frontend/src/lib/layout/AccountMenu.svelte | Sửa | Mục Quản trị chỉ hiện khi role admin; callback điều hướng |
| frontend/src/lib/layout/AppSidebar.svelte | Sửa | Bổ sung view admin-users và chuyển props/callback; không import page |
| frontend/src/lib/i18n/locales/vi-VN/translation.json | Sửa | Nhãn/hướng dẫn và lỗi bootstrap/admin bằng tiếng Việt |
| frontend/src/lib/i18n/locales/en-US/translation.json | Sửa | Bộ khóa tương ứng tiếng Anh |
| frontend/src/lib/i18n/locales/ru-RU/translation.json | Sửa | Bộ khóa tương ứng tiếng Nga |
| frontend/vite.config.ts | Sửa | Proxy /admin về backend trong development |

WorkspaceShell.svelte, PasswordField.svelte, AuthToastLayer.svelte, message()
và tokens theme được tái sử dụng. Không thay chúng chỉ để có một bản riêng cho
admin. Chỉ điều chỉnh helper auth-form trong phạm vi validation dùng chung.

State quản trị không lưu password thành draft trong owner. Form giữ password
cục bộ, gửi cho một lần xử lý, rồi xóa theo các điều kiện đã mô tả. Không dùng
một store toàn cục để giữ danh tính hoặc quyền admin từ client.

#### Kiểm thử và tài liệu

| Tệp | Thao tác dự kiến | Nội dung |
| --- | --- | --- |
| tests/test_f012_001_system_role.py | Tạo | Schema/migration, default/check constraint và giữ nguyên dữ liệu |
| tests/test_f012_002_bootstrap.py | Tạo | Setup/bootstrap, cạnh tranh PostgreSQL, session và rollback |
| tests/test_f012_003_admin_accounts.py | Tạo | Service tạo/lookup, cả hai role, audit, không sinh session/grants |
| tests/test_f012_004_admin_api.py | Tạo | Hợp đồng HTTP, Origin/CSRF/admin, redaction và không đổi cookie |
| tests/test_f012_005_accounts_e2e.py | Tạo | Hai role, isolation và luồng browser với PostgreSQL/provider giả |
| tests/test_f009_003_registration_service.py | Sửa | register() chỉ bootstrap; giữ validation/hash/rollback coverage |
| tests/test_f009_004_registration_api.py | Sửa | Đổi kỳ vọng public signup thành bootstrap; giữ cookie/error coverage |
| tests/test_f009_006_registration_e2e.py | Sửa | Thay public signup sau có user bằng admin create; giữ cạnh tranh và isolation |
| frontend/tests/auth-api.test.mjs | Sửa | Setup/role, phân biệt lỗi bootstrap và email_taken |
| frontend/tests/registration.test.mjs | Sửa | Hồi quy validation sau khi tách helper |
| frontend/tests/auth-browser.mjs | Sửa | Setup/đóng signup, form cũ, role trong session mocks |
| frontend/tests/auth-e2e.mjs | Sửa | Luồng browser auth mới; không kỳ vọng đăng ký công khai sau khởi tạo |
| frontend/tests/admin-api.test.mjs | Tạo | CSRF, shape response, safe errors và không retry |
| frontend/tests/admin-form.test.mjs | Tạo | Default/validation role, identity/password boundaries |
| frontend/tests/admin-state.test.mjs | Tạo | Kết quả chưa xác định, lookup và loại bỏ response muộn |
| frontend/tests/admin-browser.mjs | Tạo | Form và lifecycle, theme/locale/focus; API giả |
| frontend/tests/admin-e2e.mjs | Tạo | Browser driver cho backend/PostgreSQL thực trong môi trường test |
| README.md | Sửa khi triển khai | Onboarding/tài khoản, lệnh test backend/frontend/browser đầy đủ và điều kiện chạy |
| specs/02-architecture.md | Sửa khi triển khai | Vai trò hệ thống, API quản trị và state ownership sau khi có code |
| docs/database-setup.md | Sửa khi triển khai | Migration role, điều kiện dữ liệu cũ và giới hạn rollout |

Trước khi code, kiểm tra lại worktree. Không ghi đè các thay đổi sẵn có trong
WorkspacePage, catalogs hoặc test browser của người dùng. Nếu cần thêm tệp ngoài
danh sách, báo phạm vi và xin duyệt theo quy tắc repository.

### F012-001 — Vai trò hệ thống và migration

- [x] **Work:** Viết kiểm tra SQL/schema và dữ liệu cũ; thêm system_role/check
  constraint bằng migration mới; không nâng quyền tự động. Xác minh upgrade,
  downgrade rồi upgrade lại trên database dùng riêng cho test.
- **Where:** models/auth.py; migration 0010_users_system_role.py;
  tests/test_f012_001_system_role.py; tests/test_f009_002_email_uniqueness.py
  được điều chỉnh để test schema lịch sử bằng SQL thay vì model mới.
- **Done:** AC-21; giá trị ngoài user/admin bị DB từ chối, user cũ vẫn giữ
  password/active/grants, không có migration đã áp dụng nào bị sửa.
- **Phụ thuộc:** Không có.

### F012-002 — Contracts và lỗi tài khoản an toàn

- [x] **Work:** Viết test cho field limits, role/trường dư và payload nhạy cảm;
  bổ sung contracts setup/admin, role trong AuthUser và cơ chế redaction dùng chung.
  Giữ password nguyên văn và tách HTTP khỏi service.
- **Where:** contracts/auth.py; contracts/admin.py; api/security.py; phần
  RegistrationRoute trong api/auth.py; tests/test_f012_004_admin_api.py;
  assertion response trong tests/test_f009_004_registration_api.py.
- **Done:** AC-10, AC-13; lỗi chỉ chứa mã/field an toàn, không serialize input
  ngay cả khi validation chưa vào service.
- **Phụ thuộc:** F012-001.

### F012-003 — Khởi tạo admin đầu tiên

- [x] **Work:** Viết test setup và cạnh tranh trên PostgreSQL; đổi register()
  thành bootstrap-only; thêm khóa giao dịch, role gán server-side, audit và rollback.
  Cung cấp GET setup và trả role trong login/session.
- **Where:** services/auth.py; api/auth.py; contracts/auth.py;
  services/audit.py được tái sử dụng; tests/test_f012_002_bootstrap.py;
  các test registration F009 liên quan.
- **Done:** AC-01–AC-05, AC-14; nhiều email gửi đồng thời vẫn chỉ tạo một admin
  và session; tài khoản inactive hiện có cũng đóng signup.
- **Phụ thuộc:** F012-001, F012-002.

### F012-004 — Service admin cấp và kiểm tra tài khoản

- [x] **Work:** Viết test service trước; thêm require_admin/create_account/
  lookup_account. Kiểm tra quyền trong giao dịch, hash mật khẩu, insert User và audit;
  xử lý email constraint; không tạo session hoặc quyền tài nguyên.
- **Where:** services/admin.py; contracts/admin.py;
  AuditEventWriter.append và hash_password hiện có;
  tests/test_f012_003_admin_accounts.py.
- **Done:** AC-07–AC-11, AC-14–AC-16, AC-20; cả hai role được tạo đúng,
  duplicate không ghi đè, lookup đúng email và audit lỗi làm rollback.
- **Phụ thuộc:** F012-001, F012-002.

### F012-005 — API quản trị và bảo vệ request

- [x] **Work:** Viết test API; thêm dependency admin và router create/lookup;
  dùng Origin/CSRF/redaction, map lỗi service sang HTTP; đăng ký router và proxy.
  Xác minh response tạo tài khoản không có Set-Cookie hoặc secret người nhận.
- **Where:** dependencies.py; api/admin.py; api/security.py; main.py;
  frontend/vite.config.ts; tests/test_f012_004_admin_api.py.
- **Done:** AC-06, AC-09, AC-12–AC-15; user thường/API trực tiếp bị chặn,
  role giả không cấp quyền, create không thay phiên admin.
- **Phụ thuộc:** F012-002, F012-004.

### F012-006 — Frontend khởi tạo và đăng nhập

- [x] **Work:** Viết kiểm tra client/UI; đọc setup sau khi không có phiên, xử lý
  loading/error và đóng register theo server; cập nhật nhãn khởi tạo và role session.
  Xử lý setup_already_completed, URL cũ và kết quả mạng chưa xác định.
- **Where:** App.svelte; features/auth/auth-api.ts, AuthPage.svelte,
  RegisterForm.svelte; frontend/tests/auth-api.test.mjs, auth-browser.mjs,
  auth-e2e.mjs.
- **Done:** AC-01, AC-04–AC-06, AC-17; không lóe form signup khi setup chưa biết;
  chỉ bootstrap/login thay session, logout không mở lại signup.
- **Phụ thuộc:** F012-003.

### F012-007 — Giao diện admin tạo user/admin

- [x] **Work:** Viết kiểm tra form/state; tạo page mỏng, panel/form và API/state
  feature. Default user, giải thích quyền admin; xử lý submit, lỗi, unknown/lookup,
  cleanup và loại bỏ response muộn. Chỉ tách helper validation cần tái sử dụng.
- **Where:** pages/AdminPage.svelte; features/admin/AccountsPanel.svelte,
  CreateAccountForm.svelte, admin-api.ts, admin-form.ts, admin-state.svelte.ts;
  features/auth/auth-form.ts; các test admin-api/form/state.
- **Done:** AC-07–AC-10, AC-15–AC-18; không retry POST ngầm, không giữ password
  trong storage/owner draft; response quản trị không được chuyển sang acceptSession.
- **Phụ thuộc:** F012-005, F012-006.

### F012-008 — Điều hướng, locale và bảo toàn workspace

- [x] **Work:** Ghép admin view/menu theo role, query/Back/Forward/reload; giữ
  owners đang hoạt động, xử lý 401/403 khác nhau. Bổ sung ba catalog và kiểm tra
  focus, theme, màn hình hẹp, cleanup khi chuyển view/logout.
- **Where:** pages/WorkspacePage.svelte; layout/AccountMenu.svelte,
  AppSidebar.svelte; ba translation.json; frontend/tests/admin-browser.mjs.
  Tái sử dụng WorkspaceShell, PasswordField và toast hiện có.
- **Done:** AC-06, AC-17–AC-19, AC-22; user không vào quản trị bằng URL, admin
  chuyển view không mất chat/upload, catalog giữ cùng bộ khóa.
- **Phụ thuộc:** F012-007.

### F012-009 — Tích hợp và hồi quy

- [x] **Work:** Kiểm tra bootstrap trên database rỗng và admin create trên
  database test có dữ liệu; login cả hai role; kiểm tra doc/citation isolation,
  concurrency, cookie và late response. Cập nhật test F009 để giữ coverage hữu
  ích, không xóa test chỉ vì hợp đồng signup thay đổi.
- **Where:** tests/test_f012_005_accounts_e2e.py;
  tests/test_f009_003_registration_service.py,
  test_f009_004_registration_api.py, test_f009_006_registration_e2e.py;
  frontend/tests/registration.test.mjs, auth-browser.mjs, auth-e2e.mjs,
  admin-browser.mjs, admin-e2e.mjs.
- **Done:** AC-03, AC-08–AC-09, AC-11–AC-14, AC-18–AC-23; có bằng chứng test
  PostgreSQL thực cho cạnh tranh, không dùng SQLite làm bằng chứng thay thế.
- **Phụ thuộc:** F012-003–F012-008.

### F012-010 — Hướng dẫn và nghiệm thu feature

- [x] **Work:** Cập nhật README/architecture/database setup theo hành vi đã code.
  README hiện chưa mô tả lệnh chạy full backend suite; bổ sung lệnh thực tế theo
  unittest hiện có, PYTHONPATH và yêu cầu Docker/browser trước khi nghiệm thu.
  Chạy required checks, ghi pass/fail/skip từ output và đối chiếu từng AC.
- **Where:** README.md; specs/02-architecture.md; docs/database-setup.md;
  toàn bộ test F012 và các kiểm tra hồi quy liên quan.
- **Done:** AC-24; full backend suite, migration SQL và PostgreSQL integration,
  frontend tests/lint/format-check/build cùng browser checks được báo đúng trạng
  thái. Không ghi đạt cho kiểm tra bị skip/chưa chạy.
- **Phụ thuộc:** F012-009.

### Kế hoạch kiểm chứng khi triển khai

- Backend dùng unittest hiện có. Tái sử dụng hạ tầng PostgreSQL/provider giả
  trong tests/test_f005_007_e2e.py và test migration từ F009; không gọi provider thật.
- Test bootstrap cần database rỗng dùng riêng. Không xóa user của database dev
  hoặc sửa seed chung thành admin hàng loạt để làm test pass.
- Kiểm tra cạnh tranh thực với nhiều connection/request: bootstrap dùng email
  khác nhau; admin create dùng cùng email có khác hoa/thường.
- Fault injection ở stage session/audit/commit phải xác minh dữ liệu sau rollback,
  không chỉ kiểm tra HTTP status.
- Frontend unit dùng cơ chế Node test hiện có; browser giả kiểm tra UI/state,
  browser với backend/PostgreSQL kiểm tra hợp đồng và phiên thực.
- Chạy full backend suite theo hướng dẫn sẽ cập nhật trong README; chạy frontend
  tests, lint, format-check, build và các browser checks liên quan. Không dùng
  lệnh format ghi đè toàn frontend khi chỉ muốn kiểm tra.
- SQL upgrade/downgrade và fixtures chạy trong môi trường test tách biệt. Nếu thiếu
  Docker/browser/runtime, báo giới hạn và chưa đánh dấu task/AC phụ thuộc là đạt.

### Trạng thái triển khai

- F012-001 hoàn thành ngày 2026-10-21. Test mới có 8 bài đạt; test hồi quy
  migration email có 3 bài đạt. Full backend suite chạy 178 bài: 176 đạt,
  0 lỗi/thất bại và 2 skip vì chưa build frontend/cấu hình Playwright/browser.
  Các kiểm tra PostgreSQL của task 01 đã chạy và đạt, không bị skip.
- Đã kiểm tra SQL rồi migrate database ứng dụng từ 0008 qua 0009 lên
  0010_users_system_role. Đối chiếu trước/sau xác nhận migration giữ nguyên dữ liệu.
- Sau migration, theo phê duyệt riêng của người dùng, đã backup tại
  logs/database-backups/ruvie-before-user-reset-20261021.dump rồi xóa 2 user,
  22 audit event liên quan và dữ liệu phụ thuộc tài khoản. Đây là thao tác reset
  được yêu cầu riêng, không nằm trong migration. Đã khôi phục và xác minh trigger
  audit; giữ nguyên nội dung 3 tài liệu, 3 revision và 5 chunk.
- F012-002 hoàn thành ngày 2026-10-21. Đã bổ sung contracts setup/admin,
  trả system_role từ database trong login/session và dùng chung AccountCreationRoute
  để kiểm tra Origin trước khi parse, trả lỗi validation chỉ có mã/field cho phép.
  Tái sử dụng validator của RegisterRequest; password giữ nguyên và bị ẩn khỏi repr.
  Tham khảo SignupForm/AddUserForm tại references/backend/ruvie/models/auths.py;
  chỉ dùng ý tưởng kế thừa contract, không mang role pending hay runtime legacy vào.
- Test F012-002 có 20 bài đạt. Hồi quy auth có 7 bài đạt; hồi quy đăng ký có 5 bài
  đạt sau khi cập nhật assertion system_role theo phê duyệt. Full backend suite:
  198 bài chạy, 196 đạt, 0 lỗi/thất bại, 2 skip do thiếu build frontend/cấu hình
  Playwright/browser. Lệnh: `.venv/Scripts/python.exe -B -m unittest discover -s tests -p 'test_*.py'`.
  Task 02 không migrate hoặc thay đổi dữ liệu database ứng dụng.
- F012-003 hoàn thành ngày 2026-10-21. GET /auth/setup trả trạng thái không có
  user; lỗi đọc trả 503 setup_unavailable. POST /auth/register chỉ khởi tạo khi
  chưa có bất kỳ user nào, kể cả inactive. Service lấy PostgreSQL advisory
  transaction lock trước khi kiểm tra, gán role admin phía server và lưu
  user/session/audit cùng giao dịch. Chỉ đặt cookie sau commit thành công.
  Khi đã có user, trả 409 setup_already_completed; lỗi tạo trả mã an toàn
  account_creation_failed và rollback. Không tự cấp membership hoặc document grant.
- Tái sử dụng RegisterRequest, SetupStatusResponse, AccountCreationRoute,
  hash_password, _stage_session và AuditEventWriter.append. Tham khảo
  signup_handler tại references/backend/ruvie/routers/auths.py; không sao chép
  cách đếm user sau insert hoặc gán nhóm mặc định của legacy.
- Test bootstrap mới: 13/13 đạt trên PostgreSQL thực, gồm 4 email đồng thời,
  các role/trạng thái active, lỗi đọc setup và rollback sau hash/session/audit/commit.
  Kiểm chứng mutation trong bộ nhớ: bỏ khóa làm test cạnh tranh thất bại vì
  tạo 4 admin; không sửa source trong kiểm chứng này. Hồi quy F009 service/API:
  13/13 đạt. Hồi quy PostgreSQL F009: 3 đạt, 1 browser skip; admin mới vẫn bị
  chặn khỏi nội dung tài liệu không có ACL. Full backend suite: 211 bài chạy,
  209 đạt, 0 lỗi/thất bại, 2 browser skip vì thiếu build frontend/cấu hình
  Playwright/browser. Lệnh: `.venv/Scripts/python.exe -B -m unittest discover -s tests -p 'test_*.py'`.
  Task 03 chỉ dùng database test riêng; không migrate, xóa user hoặc tự tạo admin
  trong database ứng dụng.
- F012-004 hoàn thành ngày 2026-10-21. AdminAccountService có require_admin,
  create_account và lookup_account. Quyền actor được đọc lại từ database;
  thao tác tạo giữ khóa hàng actor đến commit/rollback. Tạo tài khoản active với
  role user mặc định hoặc admin được chọn; User và audit account.create cùng
  giao dịch. Chỉ hai constraint email được ánh xạ thành EmailTaken. Kết quả là
  CreatedAccount chứa AdminAccountSummary, không chứa ORM credentials/session.
- Lookup dùng AccountLookupRequest để chuẩn hóa/kiểm tra email chính xác;
  trả tối đa một summary, gồm cả inactive. Actor và tài khoản được tra cứu đều
  được refresh từ database, tránh role/trạng thái cũ trong identity map của ORM.
  Không tạo session, membership, grant hoặc thay đổi phiên admin đang thao tác.
- Tái sử dụng CreateAccountRequest/RegisterRequest, hash_password và
  AuditEventWriter.append. Đã đối chiếu add_user tại
  references/backend/ruvie/routers/auths.py; không mang JWT của người nhận,
  gán nhóm mặc định hoặc log exception chứa dữ liệu nhạy cảm sang service mới.
- F012-004 có 16 test đạt trong full suite: 11 test service và 5 test PostgreSQL.
  Coverage gồm role/active mới nhất, admin mới cấp tiếp cả hai role, email trùng
  inactive/khác hoa thường, cạnh tranh giữa hai admin, khóa actor khi bị hạ quyền,
  rollback audit/commit, bảo toàn phiên và default-deny tài liệu của cả hai role.
  Test hồi quy contracts/redaction F012 có 20/20 đạt. Sau khi khởi động lại Docker
  engine, full backend suite chạy 227 bài: 225 đạt, 0 lỗi/thất bại và 2 browser
  skip do thiếu build frontend/cấu hình Playwright/browser. Lệnh:
  `.venv/Scripts/python.exe -B -m unittest discover -s tests -p 'test_*.py'`.
  Task 04 chỉ dùng database test riêng, không migrate hoặc đổi dữ liệu ứng dụng.
- F012-005 hoàn thành ngày 2026-10-21. Đã có POST /admin/users và
  GET /admin/users?email=... trong router đăng ký tại main.py, cùng proxy /admin
  tại vite.config.ts. Dependency get_admin_user_id lấy danh tính từ cookie và
  gọi service xác minh role/active mới nhất; service vẫn kiểm tra lại trước ghi.
  POST kiểm tra Origin trước parse và xác minh CSRF theo cookie hiện tại.
- AdminRoute chuyển lỗi nghiệp vụ thành mã HTTP an toàn, che lỗi body/query
  và lỗi nội bộ; mọi response của hai endpoint có Cache-Control: no-store.
  POST trả 201 với metadata, không đặt cookie hoặc trả session của người nhận.
  GET dùng AccountLookupRequest để kiểm tra email chính xác và từ chối query dư.
  Không đổi hợp đồng lỗi login/logout hoặc tự đăng xuất admin khi gặp 403.
- Tái sử dụng AccountCreationRoute, verify_csrf và AdminAccountService;
  tách account_validation_detail để dùng chung redaction body/query. Tham khảo
  add_user tại references/backend/ruvie/routers/auths.py và get_admin_user tại
  references/backend/ruvie/utils/auth.py; dùng cookie/CSRF và 403 cho thiếu quyền
  theo active spec, không port JWT người nhận hoặc role lấy từ client.
- Test F012 contracts/API có 36/36 đạt, gồm 16 test mới (14 API và 2 PostgreSQL).
  Kiểm tra quyền, role giả, inactive/expired/demotion, Origin/CSRF, validation,
  email trùng, lookup, lỗi nội bộ, no-store và bảo toàn phiên. PostgreSQL xác nhận
  router thực tạo cả hai role và lỗi audit rollback toàn bộ tài khoản tạo dở.
  Full backend suite: 243 bài chạy, 241 đạt, 0 lỗi/thất bại, 2 browser skip do
  thiếu build frontend trên đĩa/cấu hình Playwright. Lệnh:
  `.venv/Scripts/python.exe -B -m unittest discover -s tests -p 'test_*.py'`.
  Test riêng: cùng lệnh discover với `-p 'test_f012_004_admin_api.py' -v`.
- Frontend: `npm --prefix frontend test` có 45/45 đạt; ESLint và Prettier chỉ
  kiểm tra vite.config.ts đều đạt. Từ frontend/, đã chạy
  `.\node_modules\.bin\eslint.cmd vite.config.ts` và
  `.\node_modules\.bin\prettier.cmd --check vite.config.ts`.
  Import trực tiếp config xác nhận /admin trỏ http://127.0.0.1:8000. Build production
  đạt qua Vite API với configFile=false, build.write=false; không tạo output build.
  Task 05 không migrate hoặc thay đổi dữ liệu database ứng dụng.
- F012-001–F012-005 và AC-03/AC-09/AC-12/AC-15/AC-21 được đánh dấu hoàn thành.
  Các AC còn lại giữ nguyên để nghiệm thu đầy đủ với giao diện và tích hợp;
  Tại thời điểm hoàn tất task 05, F012-006–F012-010 chưa hoàn thành.
- F012-006 hoàn thành ngày 2026-10-21. App.svelte đọc session trước, rồi đọc
  setup khi chưa đăng nhập. Không hiển thị form khi đang đọc hoặc setup lỗi;
  lỗi có Thử lại. Chỉ database rỗng mở form tạo admin; URL cũ, lịch sử điều hướng
  và logout không mở lại đăng ký khi hệ thống đã khởi tạo. Bộ đếm thế hệ loại bỏ
  phản hồi session/setup cũ, kể cả hai lần Thử lại chồng nhau.
- auth-api.ts kiểm tra chặt boolean setup, role và session trả về; GET session/setup
  dùng no-store. Phân biệt setup_already_completed với email_taken và mã 409 lạ.
  Khi mất phản hồi hoặc kết quả chưa rõ, chỉ đọc lại setup; không tự lặp POST,
  không suy ra danh tính từ trạng thái setup. AuthPage giữ giao diện hiện tại;
  RegisterForm xóa password/confirmation sau phản hồi và khi rời form, hiển thị
  lỗi trường gắn với aria-describedby. Ba locale có nhãn và lỗi tương ứng.
- Tái sử dụng validator, PasswordField, toast, cookie/CSRF và workspace hiện có.
  Tham khảo luồng signup tại references/backend/ruvie/routers/auths.py; frontend
  tuân theo bootstrap-only và role do server trả về, không nhận role từ form.
  Bootstrap thành công hiện vào workspace với phiên admin. Mở Người dùng và
  điều hướng theo role thuộc task 07/08; AC-02/AC-06/AC-17 vẫn chưa nghiệm thu
  toàn feature. Chưa có giao diện quản trị tạo tài khoản.
- Kiểm tra task 06: `npm --prefix frontend test` đạt 51/51, không skip;
  `npm --prefix frontend run lint`, `npm --prefix frontend run format:check`
  và `npm --prefix frontend run build` đều đạt.
  `node frontend/tests/auth-browser.mjs` đạt 70 kiểm tra, gồm setup loading/error,
  Retry cạnh tranh, URL/history, mật khẩu, locale/layout và mất phản hồi sau commit.
  Theme browser đạt 10 kiểm tra; LLM với RUVIE_ENTER_ONLY=1 đạt 16 kiểm tra.
  Browser dùng RUVIE_PLAYWRIGHT_PATH trỏ module Playwright đã cài và
  RUVIE_BROWSER_PATH trỏ Chromium đã cài; ảnh kiểm thử chỉ ghi vào logs/ đã duyệt.
- Sau bản sửa cuối, `.venv/Scripts/python.exe -B -m unittest discover -s tests
  -p 'test_f009_006_registration_e2e.py' -v` đạt 4/4, không skip, với PostgreSQL
  thực và trình duyệt: bootstrap/reload/logout/login, chặn tạo lại, cạnh tranh,
  rollback session và cô lập tài liệu. Chỉ dùng database test riêng; không migrate
  hoặc thay đổi tài khoản trong database ứng dụng. Task 06 không sửa backend;
  full backend suite gần nhất ở task 05 có 243 bài chạy như ghi phía trên.
- Hồi quy browser rộng hơn còn lỗi: workspace sidebar/mobile layout; model search
  mất giá trị khi đổi locale; UX tìm tab settings-general không còn tồn tại;
  upload tìm nút Kết nối LLM trong Chat; layout và accessibility không thấy
  account-trigger sau đổi viewport. Đã build đối chứng bằng bốn file auth từ HEAD,
  giữ các file UI khác hiện tại: các lỗi tương ứng vẫn xuất hiện (workspace lỗi
  mobile layout sớm hơn). Không sửa các phần UI ngoài phạm vi hoặc nới assertion.
  Vì vậy không tuyên bố toàn bộ browser regression đạt; cần xử lý riêng trước
  khi nghiệm thu tích hợp toàn feature ở task 09.
- F012-007 hoàn thành ngày 2026-10-22. Tạo AdminPage, AccountsPanel và
  CreateAccountForm trong frontend. Page chỉ ghép feature và quản lý vòng đời;
  một instance gắn với một phiên actor. Khi task 08 ghép điều hướng, nơi quản lý
  phiên phải hủy/remount page khi đổi actor hoặc phiên. Chưa nối page vào menu.
- Form mới luôn rỗng, role mặc định user; chọn được admin và có giải thích quyền.
  Không yêu cầu xác nhận mật khẩu. Tái sử dụng PasswordField và tách
  validateAccountIdentity từ auth-form.ts; bootstrap vẫn kiểm tra confirmation,
  login giữ chính sách cũ. Mật khẩu giữ nguyên khoảng trắng và đếm Unicode như
  backend. Lỗi có aria-describedby, focus trường lỗi; đóng/thành công trả focus
  về nút mở. Khóa sửa/gửi/Hủy/Escape khi request đang chạy. Xóa password sau phản
  hồi hoặc khi unmount; metadata state không chứa password draft.
- admin-api.ts cung cấp createAccount và lookupAccount. Chỉ gửi bốn trường
  người nhận; dùng cookie/CSRF hiện tại và no-store. Runtime kiểm tra summary,
  role, active boolean và số lượng lookup; chỉ trả metadata cho phép, bỏ trường
  dư. Lỗi chỉ giữ status, mã an toàn và field message; không giữ body lỗi thô.
  Không trả session, không gọi acceptSession và không tự retry POST.
- createAdminState quản lý tạo/lookup, chống gửi lặp và bỏ response muộn bằng
  generation/dispose. 401 xóa state và gọi onexpired; chỉ 403 admin_required
  gọi onforbidden. Origin/CSRF lỗi không đăng xuất. Lỗi rollback đã biết cho phép
  sửa và chủ động gửi mới. Network/body lỗi hoặc mã không rõ giữ trạng thái chưa
  xác định. Lookup dùng đúng email đã gửi; match chỉ để đối chiếu, không xác nhận
  POST trước thành công hoặc ghi đè account. Lookup rỗng mới mở lại gửi trong
  luồng chưa xác định; lookup lỗi không tự mở lại. Lỗi email_taken đã biết không
  bị chuyển thành kết quả tạo chưa xác định khi lookup tìm thấy tài khoản.
- Tham khảo reset form và role user mặc định từ
  references/src/lib/components/admin/Users/UserList/AddUserModal.svelte.
  Tái sử dụng active PasswordField, validator và mẫu generation/dispose của
  createLlmState. Không port token localStorage, CSV, pending role hay runtime
  legacy. CSS dùng token hiện có; chưa bổ sung thư viện hoặc backend/migration.
- Thêm admin-api.test.mjs, admin-form.test.mjs, admin-state.test.mjs: 15 test mới.
  Đã chạy RED trước implementation. Kiểm tra thật component qua SSR và Chromium;
  chỉ giả lập ranh giới HTTP, không thay state/form bằng mock. Browser xác minh
  focus lỗi, xóa password, giữ tên/email/role khi lỗi, khóa Hủy/Escape, reset form,
  kết quả unknown/lookup và cleanup khi rời page; viewport 390px không tràn ngang.
  Ảnh kiểm tra tại logs/admin-task007.png. Vite test cache nằm trong
  frontend/dist/.admin-test-cache, cùng phạm vi output build đã được duyệt.
- Với RUVIE_PLAYWRIGHT_PATH và RUVIE_BROWSER_PATH cấu hình như task 06,
  `npm --prefix frontend test` đạt 66/66, 0 fail, 0 skip. Browser component test
  bỏ qua nếu thiếu RUVIE_PLAYWRIGHT_PATH; các test còn lại không phụ thuộc browser.
  `npm --prefix frontend run lint`, `npm --prefix frontend run format:check`,
  `npm --prefix frontend run build` đều đạt. `node frontend/tests/auth-browser.mjs`
  đạt 70 kiểm tra hồi quy sau khi tách validator. Build riêng AdminPage bằng Vite
  lib entry, write=false cũng đạt; xác nhận API quản trị có trong bundle bộ nhớ.
  Task 07 chỉ sửa frontend; không chạy lại backend suite hoặc ghi database ứng dụng.
- F012-007 đã hoàn thành ở cấp component/API/state. Nhãn quản trị mới hiện dùng
  tiếng Việt; nhãn/lỗi auth tái sử dụng catalog hiện có. Task 08 bổ sung ba locale,
  menu, URL/history, kiểm tra role phía giao diện và bảo toàn workspace. Task 09
  kiểm tra browser tới backend thực, đăng nhập người nhận và các AC tích hợp.
  Không đánh dấu thêm AC toàn feature ở task 07; các lỗi browser hồi quy rộng
  đã ghi ở task 06 vẫn cần xử lý riêng, không tuyên bố đã khắc phục.
- F012-008 hoàn thành ngày 2026-10-22 sau khi kiểm chứng hồi quy auth.
  WorkspacePage ghép AdminPage trong
  cùng shell; chỉ mount trang quản trị khi view admin-users đang mở và role hợp lệ.
  Query view hỗ trợ các view hiện có, pushState/replaceState và popstate; view lạ
  về chat, giữ query không liên quan. Trước mỗi lần vào quản trị, đọc session mới
  từ server; so khớp actor/CSRF và role. Lỗi đọc quyền không tự logout; generation
  bỏ qua phản hồi navigation cũ. User thường không mount quản trị hoặc gửi API admin.
- AppSidebar truyền canAdmin xuống AccountMenu. Menu thêm Quản trị chỉ cho admin,
  dùng cùng tương tác bàn phím/popover hiện có. Khi API trả admin_required,
  workspace đóng quản trị và ẩn mục mở lại trong phiên hiện tại; CSRF/Origin lỗi
  giữ phiên và view. 401 dùng cơ chế hết phiên hiện có. AdminPage và state task 07
  được tái sử dụng nguyên trạng; unmount khi rời view/logout để cleanup secret và
  response muộn. Chat/documents/LLM owners không remount khi đổi view.
- App.svelte đặt view=admin-users sau bootstrap thành công; login/session restore
  tiếp tục giữ query để workspace kiểm tra. Logout/hết phiên xóa query view để
  tài khoản sau không nhận view quản trị từ phiên cũ. AccountsPanel có tiêu đề
  nhận focus; panel/form dùng khóa dịch và mã lỗi an toàn. Bổ sung 30 khóa admin
  ở cả vi-VN/en-US/ru-RU. Đổi locale cập nhật nhãn, lỗi và kết quả đang hiển thị,
  giữ dữ liệu form. Escape trong menu/dialog không đóng nhầm form phía dưới;
  icon hiện/ẩn password có màu phù hợp trên nền tối của trang quản trị.
- Tái sử dụng WorkspaceShell, PasswordField, cơ chế workspace keyed theo actor/CSRF
  và callback task 07. Tham khảo điều kiện role=admin trong
  references/src/lib/components/layout/Sidebar/UserMenu.svelte; không port router,
  runtime legacy hoặc lấy URL làm quyền. Không thêm dependency/backend/migration.
- Thêm frontend/tests/admin-browser.mjs. Chạy trên production build và Chromium
  với HTTP giả lập: 25 nhóm đạt. Coverage gồm user URL trực tiếp, reload/history,
  giữ draft/stream chat và File/upload đang chạy, ba locale và đổi chữ lỗi/kết quả,
  sáng/tối, 390px không tràn ngang, focus/menu bàn phím, 401/403 từng loại, role mới
  từ session, session read lỗi/chậm, logout khi POST chưa xong và bootstrap mở đúng
  quản trị. Ảnh đã xem tại logs/admin-task008-dark.png và admin-task008-mobile.png.
  Test chờ sidebar hoàn tất chuyển động trước kiểm tra/screenshot mobile.
- Với RUVIE_PLAYWRIGHT_PATH/RUVIE_BROWSER_PATH như task 06,
  `npm --prefix frontend test` đạt 66/66, 0 fail, 0 skip; admin-form browser dùng
  locale vi-VN rõ ràng sau khi bỏ nhãn Việt hardcode. `node frontend/tests/theme-browser.mjs`
  đạt 10 kiểm tra. Lint, format:check, build và scoped diff check đều đạt.
- Sau phê duyệt bổ sung, đã sửa đúng selector logoutFromMenu trong
  frontend/tests/workspace-actions.mjs sang menuitem có tên Đăng xuất/Sign out/Выйти.
  Selector cũ khớp cả Quản trị và Đăng xuất; không sửa hoặc nới các assertion auth.
  Chạy lại `node frontend/tests/auth-browser.mjs`: 70 kiểm tra đạt;
  `node frontend/tests/theme-browser.mjs`: 10 kiểm tra đạt. ESLint và Prettier
  kiểm tra riêng helper đều đạt. F012-008 được đánh dấu hoàn thành; các AC tích hợp
  toàn feature tiếp tục nghiệm thu ở task 09, không tự đánh dấu từ mock HTTP.
  Các lỗi hồi quy workspace/settings đã ghi ở task 06 không được sửa trong task này.
- F012-009 hoàn thành ngày 2026-10-22. Thêm test_f012_005_accounts_e2e.py và
  admin-e2e.mjs, tái sử dụng PostgreSQL/container/provider/blob fixture F005 và
  cách mở Uvicorn/browser của F009. Ba test mới đạt trên database thật: tạo hai
  role qua HTTP, đăng nhập riêng, không có grant/membership, status tài liệu bị
  chặn, retrieval/citation/context không có dữ liệu riêng; E2E UI tạo và cấp tiếp
  tài khoản; header no-store trên setup/session và session 401. Browser thật đạt
  9 nhóm, xác nhận 5 account/5 audit với đúng actor, cookie/CSRF người cấp không đổi,
  email trùng không ghi đè, mất phản hồi sau commit không POST lại và lookup không
  được báo là tạo thành công. Không dùng mock thay cho backend trong E2E này.
- Nghiệm thu phát hiện thiếu Cache-Control: no-store trên auth. Sau duyệt bổ sung,
  RegistrationRoute bọc handler và HTTPException để bổ sung header; giữ nguyên
  status/body. Auth E2E cũng xác nhận bootstrap mở Người dùng và proxy /admin.
  Full backend baseline: 247 bài, 245 đạt/2 lỗi/0 skip. Sau sửa no-store và locator
  LLM E2E đã duyệt: 247/247 đạt, 0 fail/0 skip, trong 427.280 giây. Lệnh theo README:
  `.venv/Scripts/python.exe -B -m unittest discover -s tests -p 'test_*.py'` với
  PYTHONPATH=tests;backend và biến browser được cấu hình. Không chạy hai suite backend
  đồng thời; không migrate hoặc sửa database ứng dụng.
- SQL offline 0009:head xác nhận chỉ thêm system_role, default user và constraint;
  upgrade/downgrade bảo toàn dữ liệu được kiểm tra trong full suite trên PostgreSQL.
  Frontend unit: 66/66 đạt, 0 skip; lint, format-check, build và scoped diff đều đạt.
  Browser đã đạt: admin 25 nhóm, auth 70, theme 10, workspace 33, UX F011 49.
  Full LLM browser sau cập nhật fixture/locator cũ theo phê duyệt đạt 82 kiểm tra;
  trạng thái nghiệm thu cuối của task 010 được ghi phía dưới.
- README bổ sung bootstrap, cấp tài khoản, unknown/lookup, giới hạn feature,
  Docker/Playwright và lệnh full suite. Architecture cập nhật admin service/view,
  role tách biệt ACL và vòng đời state. Database setup mô tả migration 0010 và
  database cũ thiếu admin: không nâng quyền ngầm, không mở lại đăng ký, chưa có
  recovery CLI/SQL. Các thay đổi test/helper đã duyệt giữ kiểm tra phiên/quyền và
  dữ liệu; cập nhật tab Appearance, toolbar model, drawer geometry/transition và
  phân biệt quay lại Chat với New chat. Không mang runtime legacy vào ứng dụng.

- F012-010 hoàn thành ngày 2026-10-22. Full LLM browser sau cập nhật fixture/locator
  theo duyệt bổ sung đạt 82 kiểm tra, gồm locale, provider/key semantics, model
  reload, lỗi, khóa thao tác, account isolation, upload và layout. Workspace đạt
  33, UX F011 đạt 49. Các lỗi cũ được đối chiếu và sửa ở test/helper, không bỏ
  coverage: toolbar thay model trong Settings ẩn, Appearance thay General, setup
  stub đóng bootstrap, drawer đóng/mở theo state và geometry sau transition,
  chat draft không bị New chat reset ngoài ý định. Kiểm tra model không hợp lệ
  xác minh không có POST chat thay vì giả định nút luôn disabled. LLM E2E kiểm
  tra toolbar và selected_model_id qua API sau reload; giữ hai account/citation.
- Đối chiếu AC: AC-01–AC-05 dùng bootstrap PostgreSQL/F009 E2E và auth browser;
  AC-06–AC-11 dùng admin contracts/service/API, admin E2E và browser; AC-12–AC-15
  dùng Origin/CSRF/redaction/rollback/lookup tests trên SQLite và PostgreSQL;
  AC-16–AC-19 dùng lost-response E2E, state tests và admin browser (late response,
  password cleanup, giữ chat/upload); AC-20 dùng retrieval/chat/context isolation
  của cả hai role với PostgreSQL thực và provider giả local;
  AC-21 dùng migration preservation/constraint tests và SQL review; AC-22 dùng
  ba catalog, admin/theme/locale/layout/accessibility browser; AC-23 dùng F009
  trong full suite; AC-24 dùng README/architecture/database setup đã cập nhật.
  Tất cả AC và task được đánh dấu theo các kết quả trên, không tính skip là pass.
- Tổng kiểm chứng cuối: backend 247/247, frontend unit 66/66, không skip; admin
  browser 25 nhóm, auth 70, theme 10, workspace 33, UX 49, LLM 82. Lint,
  format-check, production build và diff check đạt. SQL 0009:head chỉ được sinh
  offline; migrate/downgrade chỉ chạy ở database test. Không migrate/reset, tạo
  account hoặc thay đổi nội dung trong database ứng dụng. Các giới hạn chủ động
  của feature (recovery, reset password, sửa role, vô hiệu hóa, danh sách tổng quát)
  vẫn ngoài phạm vi như README/spec đã mô tả.
