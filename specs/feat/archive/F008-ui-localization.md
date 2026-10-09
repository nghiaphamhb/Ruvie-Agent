# F008 - Đa ngôn ngữ giao diện Ruvie Agent

## Goal

Bổ sung English và Russian vào giao diện Ruvie Agent đang dùng tiếng Việt.
Người dùng chọn ngôn ngữ trước hoặc sau khi đăng nhập. Giao diện cập nhật ngay.
Người dùng tiếp tục công việc đang làm mà không cần tải lại trang.

Trạng thái: Spec đã được người dùng xác nhận phạm vi ngày 2026-10-09.
Các task triển khai và acceptance criteria bên dưới chưa được thực hiện.
Spec này không cấp yêu cầu triển khai mã.

### Hiện trạng đã kiểm tra

- Frontend dùng Svelte 5 và Vite. `frontend/package.json` chưa có dependency i18n.
- `frontend/src/main.ts` mount `App` ngay. Chưa có bước khởi tạo locale.
- `frontend/index.html` đặt `lang="vi"`. `App.svelte` có title và description
  bằng tiếng Việt.
- Nhãn, placeholder, trạng thái và thông báo lỗi nằm trực tiếp trong
  `App.svelte`, chín component và bốn API client.
- `ChatApiError` giữ `code`; ba loại lỗi API còn lại giữ HTTP `status`.
  Các constructor vẫn tạo thông báo bằng tiếng Việt.
- `App.svelte` và `LlmConnectionForm.svelte` lưu lỗi/thông báo thành chuỗi.
  `ChatTurn.error` cũng là chuỗi. Chỉ đổi nhãn component sẽ không đổi được
  ngôn ngữ của những thông báo đã lưu này.
- `DocumentUploadPanel.svelte::formatSize` dùng `toFixed(1)`.
  `CitationSources.svelte` ghép số lượng với chuỗi `nguồn tham khảo`.
- Các browser test đang tìm nhiều nhãn tiếng Việt. Khi có tự nhận locale,
  test phải chủ động thiết lập locale để không phụ thuộc máy chạy test.

### Nguồn legacy và cách thích nghi

Chỉ tham khảo các file dưới `references/` được nêu trong bảng. Không đọc hoặc
sử dụng bất kỳ thư mục `archive` nào. Không import runtime từ `references/`.

| Nguồn đã kiểm tra | Hành vi đáng tái sử dụng | Cách thích nghi cho active project |
| --- | --- | --- |
| `references/src/lib/i18n/index.ts::createI18nStore` | Svelte writable được cập nhật khi i18next khởi tạo hoặc đổi ngôn ngữ. | Port phần store tối thiểu vào frontend active. Đăng ký listener một lần. |
| `references/src/lib/i18n/index.ts::initI18n` | Danh sách locale được hỗ trợ, fallback và khởi tạo i18next. | Nạp tĩnh ba catalog. Chọn locale bằng quy tắc trong spec, không nhận `lang` từ query string. |
| `references/src/lib/i18n/index.ts::changeLanguage` | Đổi locale và cập nhật thuộc tính `lang` của tài liệu HTML. | Chỉ nhận ba locale hợp lệ. Không remount App hoặc gửi request nghiệp vụ. |
| `references/src/lib/i18n/locales/languages.json` | Một danh sách tập trung cho `vi-VN`, `ru-RU`, `en-US`. | Dùng tên bản địa Tiếng Việt, English, Русский. Bộ chọn và bộ khởi tạo dùng cùng danh sách. |
| `references/src/lib/i18n/locales/{vi-VN,en-US,ru-RU}/translation.json` | Bản dịch của những nhãn chung như Sign in, Password, Upload, Language. | Chọn từng chuỗi phù hợp, rà soát nghĩa và chuyển sang khóa ngữ nghĩa của Ruvie Agent. Không chép toàn bộ catalog. |
| `references/src/lib/components/chat/Settings/General.svelte` | Bộ chọn ngôn ngữ bằng native select. | Tạo component nhỏ dùng được ở màn hình đăng nhập và sidebar. Không port modal Settings hoặc các store legacy. |
| `references/src/routes/+layout.svelte` | Khởi tạo từ lựa chọn đã lưu và ngôn ngữ trình duyệt. | Đưa bước khởi tạo vào `frontend/src/main.ts`; không cần SvelteKit hoặc backend config locale. |
| `references/src/lib/utils/index.ts::bestMatchingLanguage` | Tìm ngôn ngữ được hỗ trợ từ danh sách ưu tiên của trình duyệt. | Viết resolver nhỏ, có kiểm tra exact tag và mã ngôn ngữ gốc. `en-GB` phải chọn được `en-US`. Không port file utils lớn. |
| `references/i18next-parser.config.ts` | Công cụ trích xuất catalog và cấu hình plural của legacy. | Chỉ tham khảo cách tổ chức. Không thêm parser vào feature này. Catalog nhỏ được kiểm tra bằng test. |

Các catalog legacy có nhiều giá trị rỗng. Catalog English phần lớn dùng
chuỗi khóa English làm nội dung fallback. Catalog active phải có bản dịch
English tường minh, không rỗng. Những câu riêng về cookie/CSRF, tài liệu được
phép đọc, stream và kết nối cá nhân phải được dịch theo hợp đồng active.

## User Story

Là người dùng Ruvie Agent, tôi muốn chọn Tiếng Việt, English hoặc Русский,
để đọc hướng dẫn, thao tác và thông báo lỗi bằng ngôn ngữ tôi hiểu.

Là người dùng đang làm việc, tôi muốn đổi ngôn ngữ mà không mất nội dung
đang nhập, tiến trình upload hoặc câu trả lời đang nhận.

## Scope

### In

- Ba locale: `vi-VN`, `en-US`, `ru-RU`. Cả ba dùng chiều chữ LTR.
- Bộ chọn ngôn ngữ trước và sau đăng nhập.
- Lưu lựa chọn theo trình duyệt và origin bằng `localStorage`.
- Tự nhận ngôn ngữ trình duyệt khi chưa có lựa chọn đã lưu hợp lệ.
- Dịch toàn bộ nội dung giao diện do ứng dụng tạo: nhãn, hướng dẫn,
  placeholder, tooltip, nội dung trợ năng, trạng thái, thông báo và lỗi an toàn.
- Cập nhật `html lang`, title và meta description theo locale đang áp dụng.
- Dịch lại thông báo đã hiển thị khi người dùng đổi locale.
- Định dạng số và kích thước file; xử lý số nhiều của số nguồn tham khảo.
- Kiểm thử tài nguyên dịch, hành vi đổi locale, state, hợp đồng request và layout.
- Tài liệu sử dụng và cách bổ sung chuỗi dịch trong README.

### Out

- Dịch câu hỏi, câu trả lời LLM, nội dung tài liệu hoặc nội dung citation.
- Thay prompt để ép LLM trả lời theo ngôn ngữ giao diện.
- Dịch tên tài khoản, project, file, tài liệu, model hoặc dữ liệu người dùng.
- Thay đổi mã HTTP, SSE event, error code, model ID, document ID hoặc revision ID.
- Dịch log server hoặc hiển thị nguyên văn lỗi/provider response từ backend.
- Lưu locale theo tài khoản trong PostgreSQL; đồng bộ giữa thiết bị.
- Đồng bộ trực tiếp locale giữa các tab đã mở. Tab khác đọc lại lựa chọn khi reload.
- Chọn ngôn ngữ bằng query string, cookie hoặc `Accept-Language` phía backend.
- Thêm màn hình Settings tổng quát, cấu hình locale quản trị hoặc API mới.
- Thay đổi ACL, CSRF, cookie, provider/proxy settings, ingestion hoặc migration.
- Thêm RTL, font tải từ bên ngoài, dịch tự động hoặc toàn bộ thư viện legacy.
- Đổi ngôn ngữ nội dung native browser như file picker, validation tooltip
  hoặc menu của select. Những nội dung đó phụ thuộc trình duyệt/hệ điều hành.

### Quyết định kiến trúc

**1. Lựa chọn locale là sở thích giao diện của trình duyệt.**

Dùng khóa mới `ruvie.ui.locale`. Giá trị lưu là một trong ba mã locale chuẩn.
Không đọc hoặc chuyển đổi khóa `locale` của legacy. Chỉ lưu locale, không lưu
API key, cookie, CSRF token, thông tin tài khoản hoặc tài liệu vào khóa này.
Đăng xuất không xóa locale. Hai tài khoản dùng cùng trình duyệt/origin dùng
cùng lựa chọn giao diện. Đây không phải thiết lập tài khoản hoặc ranh giới ACL.

**2. Quy tắc chọn locale và fallback bản dịch là hai quy tắc khác nhau.**

| Loại quyết định | Thứ tự |
| --- | --- |
| Locale ban đầu | `ruvie.ui.locale` hợp lệ → danh sách ngôn ngữ trình duyệt → `vi-VN`. |
| Bản dịch của một khóa | Catalog locale đang dùng → catalog `en-US`. |

Chỉ chấp nhận mã locale được hỗ trợ trong storage. Giá trị không hợp lệ hoặc
trống bị bỏ qua. Với trình duyệt, xử lý từng tag theo thứ tự ưu tiên:
kiểm tra exact locale trước, rồi ánh xạ mã gốc `vi`, `en`, `ru`.
Không dùng một match ưu tiên thấp hơn để vượt qua tag đầu tiên đã hỗ trợ.

| Đầu vào trình duyệt, không có lựa chọn lưu hợp lệ | Locale kết quả |
| --- | --- |
| `ru-RU` hoặc `ru` | `ru-RU` |
| `en-US`, `en-GB` hoặc `en` | `en-US` |
| `vi-VN` hoặc `vi` | `vi-VN` |
| `['fr-FR', 'ru-RU', 'en-US']` | `ru-RU` |
| `['en-GB', 'ru-RU']` | `en-US` |
| Chỉ có ngôn ngữ không hỗ trợ hoặc không có navigator | `vi-VN` |

Resolver không phân biệt hoa/thường ở tag trình duyệt. Tag lỗi không làm
ứng dụng crash. Chỉ lưu lựa chọn khi người dùng chủ động chọn trong UI;
locale tự nhận từ trình duyệt không tự ghi đè thành lựa chọn thủ công.

**3. Tái sử dụng i18next, giới hạn dependency.**

Thêm `i18next` vào frontend dependencies và cập nhật lockfile tương ứng.
Dùng Svelte writable có sẵn. Import tĩnh ba catalog JSON của active project.
Không thêm `i18next-browser-languagedetector`, `i18next-resources-to-backend`
hoặc `i18next-parser`. Không gọi CDN hoặc tải tài nguyên dịch qua API.

Khởi tạo một instance trước `mount`. Khởi tạo lặp lại không tạo thêm listener.
Store cập nhật sau khi ngôn ngữ có hiệu lực. Các component đọc translation
qua store để Svelte cập nhật nội dung. Không tính chuỗi dịch một lần trong
`const` hoặc lưu chuỗi dịch vào state lâu dài.

**4. Khóa dịch ổn định và thông báo có cấu trúc.**

Dùng khóa ngữ nghĩa dạng `auth.login`, `llm.errors.providerUnavailable`,
`upload.status.ready`. Không dùng cả câu English làm khóa mới.
Namespace duy nhất là `translation`; catalog dạng flat keys, cấu hình
`keySeparator: false`. Các nhóm tiền tố phục vụ quản lý, không tạo namespace
hoặc tải tài nguyên riêng.

Định nghĩa `MessageKey` và `UiMessage` để bắt lỗi khóa sai ở bước phát triển.
Dạng thông báo đề xuất:

```ts
// Contract dự kiến, chưa phải mã đã triển khai.
UiMessage = { key: MessageKey; params?: Record<string, string | number> }
```

State lỗi/thông báo dùng `UiMessage | null`. UI gọi translator khi render.
`ChatTurn.error` cũng chuyển sang dạng này. Trong contract tham số, `count`
luôn là number. Các tham số chứa giá trị hiển thị như `formattedCount` là string.
Không đưa dữ liệu nhạy cảm hoặc lỗi provider nguyên văn vào tham số dịch.

API error vẫn giữ `status` hoặc `code`. UI ánh xạ chúng sang khóa thông báo
an toàn. Không hiển thị `.message` hoặc `response.detail` tùy ý. Nếu cần giữ
`.message` cho tương thích với Error, nội dung đó chỉ là mô tả chẩn đoán cố
định và an toàn, không phải nguồn dịch mà UI sử dụng.

**5. Các file dự kiến.**

Tên file và interface mới trong bảng là đề xuất triển khai của spec.

| File | Trách nhiệm dự kiến |
| --- | --- |
| `frontend/src/lib/i18n/locales/languages.json` | Mã locale chuẩn và tên bản địa; nguồn duy nhất cho danh sách hỗ trợ. |
| `frontend/src/lib/i18n/locales/{vi-VN,en-US,ru-RU}/translation.json` | Ba catalog active, chỉ chứa chuỗi dùng trong Ruvie Agent. |
| `frontend/src/lib/i18n/locale.ts` | `resolveInitialLocale(saved, preferred)` và kiểm tra mã locale; xử lý độc lập với DOM để unit test. |
| `frontend/src/lib/i18n/index.ts` | `initI18n()`, `setLocale(locale)`, store và `formatFileSize(bytes, locale)`; storage/DOM chỉ dùng khi có môi trường browser. |
| `frontend/src/lib/i18n/messages.ts` | Contract `MessageKey`/`UiMessage` và ánh xạ error status/code sang khóa; không xử lý request. |
| `frontend/src/lib/components/LanguageSelector.svelte` | Native select có visible label, dùng cùng store và danh sách locale. |
| `frontend/src/main.ts`, `frontend/index.html` | Khởi tạo trước mount; HTML có locale fallback hợp lệ. |
| `frontend/src/App.svelte`, các component và API client trong inventory | Thay chuỗi UI, chuyển state thông báo, tích hợp selector và metadata. |
| `frontend/package.json`, `frontend/package-lock.json` | Dependency i18next; không cập nhật dependency không liên quan. |
| `frontend/tests/i18n.test.mjs`, `frontend/tests/i18n-browser.mjs` | Unit/catalog checks và hàm `runLocaleChecks` cho harness browser hiện tại. |
| Các test hiện có, `README.md` | Cố định locale baseline, thêm coverage đa ngôn ngữ và hướng dẫn sử dụng. |

**6. Inventory bắt buộc của giao diện.**

F008-001 phải rà soát từng dòng UI hiện có và lập bảng khóa cụ thể trong
`frontend/src/lib/i18n/message-inventory.md`. Bảng dưới là phạm vi tối thiểu.
Mỗi dòng inventory ghi file/callsite, nội dung hiện tại, khóa mới, tham số,
nguồn legacy hoặc bản dịch mới. Đánh dấu rõ chuỗi là dữ liệu/technical token
được giữ nguyên. Không tự loại chuỗi English hiện có khỏi phạm vi dịch.

| Nơi hiện tại | Nội dung phải xử lý |
| --- | --- |
| `App.svelte` | Tên view, heading, lời nhắc kết nối, kiểm tra session, lỗi login/logout/project/upload/model/chat, title và meta description. |
| `AppNavigation.svelte` | Tên view, nhãn điều hướng chính, đăng xuất, khu vực chọn ngôn ngữ. |
| `LoginForm.svelte` | Heading, mô tả tài khoản được cấp, nhãn password/email, nút login và trạng thái busy. |
| `LlmConnectionForm.svelte` | Base URL, API key tùy chọn, key help, connect/disconnect/clear/reload, nguồn personal/server/none, lỗi và success notice. |
| `ModelSelector.svelte` | Trigger/title, tiền tố model, search label/aria, listbox label, reload, loading, missing selection, empty catalog và no match. |
| `ChatConversation.svelte` | Welcome, hướng dẫn, nhãn hội thoại, loading/streaming và lỗi của từng turn. |
| `ChatComposer.svelte` | Nhãn câu hỏi, placeholder, aria-label/title nút gửi, hướng dẫn Enter/Shift+Enter và giới hạn lưu lịch sử. |
| `DocumentUploadPanel.svelte` | Heading, định dạng/giới hạn upload, project/file/title/software/version, empty project, loading, retry, trạng thái xử lý, refresh và nhãn error code. |
| `CitationSources.svelte` | Số nguồn, nhãn Citation/Document/Revision/Chunk/offset/hash/software. Giá trị metadata giữ nguyên. |
| `auth-api.ts` | Lỗi mạng, đăng nhập sai, yêu cầu thất bại và đăng xuất thất bại. Giữ HTTP status. |
| `llm-api.ts` | Ánh xạ 401/403/422/502/503 và lỗi mạng/fallback. Giữ nguyên ý nghĩa thông báo an toàn. |
| `documents-api.ts` | Session hết hạn và lỗi tài liệu; các khác biệt 404/upload/status tiếp tục được App xử lý. |
| `chat-api.ts`, `chat-turn.ts` | Tất cả `ChatErrorCode`, thông báo lỗi mỗi turn và fallback lỗi bất ngờ. Không sửa parser hoặc contract SSE. |

Tên thương hiệu `Ruvie Agent`, URL, API, HTTP, PDF, UTF-8, LLM, ID, keybinding
và đơn vị binary B/KiB/MiB có thể giữ nguyên token kỹ thuật. Câu chứa các token
này vẫn phải có khóa dịch. Giá trị do người dùng/backend cung cấp không được
đưa qua translator như thể là khóa.

## Flow

### A. Mở ứng dụng

1. `main.ts` gọi `initI18n()` trước khi mount App.
2. Bộ khởi tạo đọc `ruvie.ui.locale` trong try/catch.
3. Resolver áp dụng thứ tự locale đã chốt. Nếu storage không dùng được,
   resolver vẫn dùng navigator hoặc fallback tiếng Việt.
4. i18next khởi tạo với ba catalog đã bundle và fallback bản dịch `en-US`.
5. Store và `document.documentElement.lang` nhận locale chuẩn.
6. App mount một lần. Nội dung đầu tiên của App dùng locale đã chọn.
7. App tiếp tục luồng kiểm tra session và gọi API hiện có. Locale không được
   thêm vào request nghiệp vụ.

### B. Người dùng đổi ngôn ngữ

1. Trước đăng nhập, người dùng chọn ở phía phải topbar.
   Sau đăng nhập, người dùng chọn trong sidebar, phía trên khu vực tài khoản.
2. Bộ chọn luôn có visible label đã dịch. Option giữ tên bản địa cố định:
   Tiếng Việt, English, Русский. Không dùng cờ quốc gia làm nhãn ngôn ngữ.
3. `setLocale` kiểm tra mã bằng danh sách hỗ trợ. Giá trị không hợp lệ không
   thay đổi store, DOM hoặc storage.
4. i18next áp dụng locale; store và `html lang` cập nhật thống nhất.
5. Nhãn, metadata và tất cả `UiMessage` đang hiển thị render lại.
6. Lưu mã locale vào `ruvie.ui.locale`. Lỗi ghi storage không hủy lựa chọn
   hiện tại và không làm gián đoạn ứng dụng.
7. Focus vẫn ở bộ chọn. Không điều hướng, remount panel, gọi lại API, abort
   stream, submit form hoặc khởi động lại polling.

Bộ chọn không bị khóa bởi `authBusy`, `uploadBusy`, `llmBusy` hoặc chat busy.
Tài nguyên đã có sẵn nên đổi locale không cần tải mạng. Khi người dùng chọn
liên tiếp, lựa chọn hợp lệ cuối cùng phải là giá trị hiển thị và được lưu.
Chỉ có selector của layout hiện tại tham gia thứ tự tab; không có ID trùng.

### C. Hiển thị lỗi và dữ liệu động

1. API client trả dữ liệu hoặc ném loại lỗi hiện có kèm status/code.
2. App/component chọn `UiMessage` tương ứng. Lỗi không nhận diện được chọn
   một khóa generic an toàn, không dùng raw error text.
3. UI dịch `UiMessage` theo locale hiện tại. Khi đổi locale, cùng thông báo
   render lại mà không cần tái tạo lỗi hoặc request.
4. Câu trả lời LLM, tên model, tên tài liệu và metadata vẫn hiển thị nguyên văn.
5. Svelte render bản dịch và tham số dưới dạng text. Không dùng `{@html}`
   hoặc HTML do catalog/provider cung cấp.

### D. Số lượng và kích thước file

- Khóa số nguồn: `citations.count`, tham số `count` và `formattedCount`.
- English có dạng one/other. Russian có one/few/many/other theo i18next và
  Intl.PluralRules. Vietnamese dùng dạng phù hợp của locale, không ép dạng English.
- Các plural sibling có thể khác số lượng giữa các locale. Test so sánh nhóm
  khóa logic và các dạng bắt buộc của từng ngôn ngữ, không ép ba JSON có cùng
  danh sách suffix.
- Chuỗi English đề xuất: `{{formattedCount}} source` / `{{formattedCount}} sources`.
- Chuỗi Russian đề xuất: `{{formattedCount}} источник`, `{{formattedCount}} источника`,
  `{{formattedCount}} источников`; dạng other phải được định nghĩa đầy đủ.
- Chuỗi Vietnamese: `{{formattedCount}} nguồn tham khảo`.
- Format số dùng `Intl.NumberFormat(locale)`. Thuật toán kích thước giữ ngưỡng
  hiện tại: dưới 1024 là B, dưới 1024² là KiB, còn lại là MiB.
  B là số nguyên; KiB/MiB có đúng một chữ số thập phân. Chỉ thay định dạng số,
  không đổi bytes thực tế hoặc giới hạn 25 MiB.

## Edge Cases

| Tình huống | Hành vi yêu cầu |
| --- | --- |
| Storage không có giá trị, trống hoặc locale không hỗ trợ | Bỏ qua storage, dùng navigator rồi fallback tiếng Việt. |
| localStorage bị chặn hoặc ném lỗi | App vẫn mở và đổi locale được trong phiên hiện tại. Reload dùng resolver bình thường; không hứa lưu thành công. |
| Browser tag `en-GB`, `ru`, khác hoa/thường hoặc tag lỗi | Dùng mapping đã chốt; tag lỗi không crash. |
| Người dùng đăng xuất rồi đăng nhập tài khoản khác | Giữ locale của trình duyệt; dữ liệu tài khoản vẫn được clear theo luồng hiện tại. |
| Đổi locale khi email/password/API key/search/draft/file đã có | Giữ nguyên giá trị, không đưa vào storage hoặc nội dung dịch. |
| Đổi locale trong lúc login/connect/model save/upload/polling/chat đang chạy | Giữ cùng request và state; trạng thái/response mới render theo locale hiện tại. |
| Đổi locale khi error hoặc success notice đã hiện | Dịch lại từ cùng khóa/tham số, không gọi request để tạo lại thông báo. |
| API trả 401 khi đang đổi locale | Luồng clearSession hiện tại vẫn chạy. Màn hình login dùng locale đang áp dụng. |
| Khóa dịch không có hoặc có giá trị rỗng trong locale hiện tại | Dùng English, không hiện chuỗi rỗng. Bản phát hành phải qua catalog test để không có thiếu hụt này. |
| Khóa không có cả trong English | Đây là lỗi phát triển. Test phải fail; không được coi việc hiện raw key là kết quả chấp nhận được. |
| Bản dịch chứa placeholder thiếu hoặc không khớp | Test catalog fail trước phát hành. Không ghép câu bằng nhiều mảnh để né placeholder. |
| Tham số chứa ký tự HTML | Render dạng text; không tạo HTML/script hoặc dùng tham số làm khóa dịch. |
| Nhãn Russian dài, tài khoản/tên file/model dài | Control vẫn đọc và thao tác được; cho wrap/reflow phù hợp, không mất focus hoặc che nút. |
| Native validation/file chooser dùng ngôn ngữ khác | Không can thiệp ngôn ngữ browser/OS; nhãn và hướng dẫn do App tạo vẫn phải dịch. |
| Test chạy trong Node/SSR không có window/document/navigator | Import resolver/API client không crash. Khởi tạo test chủ động dùng locale; không truy cập DOM ở top level không được bảo vệ. |
| Nhiều tab mở cùng origin | Không đồng bộ live trong feature này. Khi reload, tab đọc lại giá trị lưu gần nhất. |

## Acceptance Criteria

- [x] AC-01: UI chỉ cung cấp ba locale vi-VN/en-US/ru-RU với tên bản địa đã chốt.
- [x] AC-02: Người dùng chọn được locale trước đăng nhập và sau đăng nhập bằng
  chuột hoặc bàn phím; control có visible label và focus rõ.
- [x] AC-03: Locale khởi tạo đúng toàn bộ bảng mapping, ưu tiên storage hợp lệ
  hơn navigator và dùng tiếng Việt khi không có match.
- [x] AC-04: Storage lỗi/giá trị giả không làm ứng dụng crash hoặc tạo locale tùy ý.
- [x] AC-05: Khởi tạo i18n hoàn tất trước mount App; không có frame nội dung App
  tiếng Việt rồi mới đổi sang locale đã chọn.
- [x] AC-06: Đổi locale cập nhật html lang, title, description và toàn bộ inventory
  UI, gồm aria-label/title/placeholder cùng trạng thái và thông báo đã hiện.
- [x] AC-07: Lựa chọn thủ công còn hiệu lực sau reload và logout/login trên cùng
  origin; không được mô tả là preference lưu theo tài khoản hoặc thiết bị khác.
- [x] AC-08: Đổi locale giữ email/password, API key đang nhập, search model,
  draft chat, selected model/project/file, các metadata upload và active view.
- [x] AC-09: Đổi locale không gửi request nghiệp vụ mới, gửi trùng upload/chat,
  abort stream hoặc làm restart polling. Polling bình thường vẫn có thể tiếp tục.
- [x] AC-10: Stream đang chạy tiếp tục tới completed/error; response/status mới
  dùng locale hiện tại. Logout/401 vẫn chặn stale response như trước.
- [x] AC-11: Câu trả lời, câu hỏi, tên tài liệu/model/project/file/tài khoản và
  giá trị citation/error code không bị dịch hoặc thay đổi.
- [x] AC-12: Catalog English đầy đủ và không rỗng. Vietnamese/Russian có đủ khóa
  logic, plural forms và placeholder tương ứng cho inventory đã rà soát.
- [x] AC-13: Fallback khóa thiếu/rỗng sang English có test; khóa thiếu trong
  English hoặc placeholder sai làm test fail.
- [x] AC-14: Số nguồn đúng với 0, 1, 2, 5, 11, 21, 22, 25 ở Russian;
  English đúng singular/plural, Vietnamese đúng cùng một dạng.
- [x] AC-15: File size giữ thuật toán binary, đơn vị và giới hạn hiện tại;
  dấu thập phân/format số theo locale, có test tại 1023/1024/1536/1048576 bytes.
- [x] AC-16: Safe errors của auth/LLM/documents/chat hiển thị đủ ba locale;
  không rò key, cookie, CSRF, provider response hoặc raw exception.
- [x] AC-17: Backend API/SSE/ACL contract không đổi. Không gửi locale trong
  payload nghiệp vụ; không thêm API, migration hoặc quyền từ client.
- [x] AC-18: Ba locale đạt layout checks ở 1280x720, 1024x600 và 640x360 CSS
  pixels tại scale 2 như harness hiện tại; không overflow ngang trang hoặc
  làm control không truy cập được. Font hiện tại hiển thị Cyrillic rõ.
- [x] AC-19: `npm test`, frontend build và fake-API browser harness trong README
  đều qua; các regression check đã có tiếp tục chạy với locale baseline xác định.
- [x] AC-20: README mô tả chọn/lưu locale, giới hạn phạm vi dịch và cách thêm
  khóa; ghi nguồn legacy đã port và các khác biệt của active project.

## Tasks

Các file/interface mới là đề xuất. Không đánh dấu task xong chỉ vì đã viết spec.
Thứ tự triển khai: F008-001 → F008-002 → F008-003 → F008-004 → F008-005 →
F008-006 → F008-007. Mỗi task triển khai bắt đầu bằng test phù hợp với behavior.

- [x] **F008-001 — Inventory chuỗi và bản đồ tái sử dụng legacy**
  - **Work:** Rà soát toàn bộ callsite trong bảng inventory. Phân biệt UI text,
    dữ liệu bên ngoài và technical token. Chốt khóa ngữ nghĩa và placeholder.
    Ghi rõ chuỗi port từ catalog legacy hoặc cần dịch mới. Lập bảng ánh xạ
    từng status/code và từng nhánh fallback ở App/component; giữ nghĩa hiện tại.
  - **Where:** Tạo `frontend/src/lib/i18n/message-inventory.md`. Đọc các component,
    API client và nguồn references đã liệt kê; không thay logic ứng dụng ở task này.
  - **Done:** Không bỏ sót title/meta, accessible text, empty/error/busy state,
    các nhãn English hiện có hoặc thông báo đã được lưu trong state. Từng chuỗi
    có disposition rõ; key/placeholder không phụ thuộc nội dung tài liệu/provider.

- [x] **F008-002 — Core i18n, khởi tạo và lưu locale**
  - **Work:** Thêm i18next và lockfile. Tạo registry locale, resolver thuần và
    store tối thiểu dựa trên legacy. Dùng ba catalog static, fallback English,
    `returnEmptyString: false`, cấu hình flat keys. Khởi tạo trước mount;
    chỉ dùng DOM/storage trong môi trường phù hợp. `setLocale` kiểm tra mã,
    cập nhật store/lang và lưu lựa chọn; xử lý storage lỗi và chọn liên tiếp.
    Khởi tạo lặp lại không nhân listener. Định nghĩa contract MessageKey/UiMessage.
  - **Where:** `frontend/package.json`, `frontend/package-lock.json`,
    `frontend/src/main.ts`, `frontend/index.html`, `frontend/src/lib/i18n/`.
    Unit tests tại `frontend/tests/i18n.test.mjs`.
  - **Done:** AC-01/03/04/05/07 có unit hoặc browser coverage. Imports dùng được
    trong harness Node hiện tại; JSON imports tương thích Node và Vite.
    Không thêm detector/backend/parser, fetch translation hoặc query-string override.

- [x] **F008-003 — Catalog Tiếng Việt, English và Russian**
  - **Work:** Điền đủ bản dịch theo inventory. Port có chọn lọc những nhãn
    legacy phù hợp, viết mới câu riêng của active contract. English có value
    tường minh, không dùng giá trị rỗng. Dùng câu hoàn chỉnh và interpolation;
    định nghĩa plural group cho citations. Rà soát thuật ngữ giữa các panel.
    Thêm kiểm tra logical key coverage, giá trị không rỗng, plural và placeholder.
  - **Where:** Ba `frontend/src/lib/i18n/locales/<locale>/translation.json`,
    inventory và `frontend/tests/i18n.test.mjs`.
  - **Done:** Catalog checks qua cho toàn bộ inventory. Không có catalog/key
    thừa của legacy hoặc HTML động. Russian đọc đúng Cyrillic; phạm vi thiếu
    dịch đã biết không được che bằng fallback để coi feature hoàn tất.

- [x] **F008-004 — Bộ chọn ngôn ngữ ở login và sidebar**
  - **Work:** Tạo LanguageSelector với native select, visible label, tên bản
    địa và ID riêng cho vị trí login/sidebar. Đưa selector vào topbar khi chưa
    đăng nhập và sidebar trước account footer khi đã đăng nhập. Control vẫn
    dùng được trong trạng thái busy. Dùng theme/focus/min-height hiện có;
    chỉnh CSS cục bộ nếu nhãn dài gây chật, không redesign layout.
  - **Where:** `frontend/src/lib/components/LanguageSelector.svelte`,
    `frontend/src/App.svelte`, `AppNavigation.svelte`; `frontend/src/app.css`
    chỉ khi cần cho reflow; browser test locale.
  - **Done:** Người dùng Tab tới selector và dùng phím để chọn cả ba locale.
    Không có control/ID trùng, không mất focus hoặc remount form. Đổi ngôn ngữ
    không gọi onselect view/onlogout/submit. Mỗi layout chỉ có selector hoạt động.

- [x] **F008-005 — Dịch toàn bộ UI và thông báo có cấu trúc**
  - **Work:** Thay các chuỗi theo inventory bằng translation reactive.
    Chuyển error/notice state và props từ string sang UiMessage/null tại mọi
    nơi liên quan. ChatTurn giữ message reference để lỗi cũ render lại.
    API errors giữ code/status, UI mapping chọn khóa safe; không dùng raw body.
    Chuyển viewLabels/nav items sang key; render trạng thái upload/model/chat
    tại thời điểm hiển thị. Dịch title/meta/accessibility text. Giữ các key
    identity, event handler, cookie/CSRF và request sequencing hiện tại.
  - **Where:** `frontend/src/App.svelte`; chín component trong inventory;
    `frontend/src/lib/{auth-api,llm-api,documents-api,chat-api,chat-turn}.ts`;
    `frontend/src/lib/i18n/messages.ts`. Test API/form hiện có và browser locale.
  - **Done:** AC-06/08/10/11/16/17 được kiểm tra. Đổi locale dịch được cả lỗi đã
    hiện và notice đã lưu; không còn chuỗi UI ngoài catalog trừ allowlist có
    lý do. Module API không phụ thuộc DOM; behavior auth/session/SSE không đổi.

- [x] **F008-006 — Plural, số và kích thước file**
  - **Work:** Dùng plural count cho summary citation; truyền raw count để chọn
    dạng và formattedCount để hiển thị. Format số bằng Intl.NumberFormat.
    Chuyển formatSize hiện có sang helper dùng locale với cùng ngưỡng/precision.
    Test English/Vi/Ru và các số lượng 0/1/2/5/11/21/22/25; test ngưỡng bytes.
  - **Where:** `CitationSources.svelte`, `DocumentUploadPanel.svelte`, helper
    trong `frontend/src/lib/i18n/index.ts`, catalog và `i18n.test.mjs`.
  - **Done:** AC-14/15 qua. Không đổi số byte/ordinal/offset/hash trong data,
    không thay request hoặc giới hạn upload. Count trong message reference
    render lại được khi đổi locale mà không cần tạo citation mới.
    `formattedCount` được tính lại khi render từ raw count và locale hiện tại;
    không lưu số đã format theo locale cũ vào state lâu dài.

- [x] **F008-007 — Browser regression, layout và tài liệu**
  - **Work:** Tạo `runLocaleChecks` và gọi từ harness fake-API hiện tại.
    Test login và ba panel ở mỗi locale. Cố định baseline vi-VN cho regression
    cũ bằng browser context/storage phù hợp; không xóa assertion để né đổi nhãn.
    Test đổi locale giữa delayed request, upload/polling, SSE và displayed error.
    Đối chiếu request count/body, state và dữ liệu bên ngoài trước/sau đổi.
    Chạy layout ở ba kích thước hiện có cho cả ba locale. Cập nhật README về
    locale và cách thêm khóa; ghi nguồn legacy và những phần không port.
  - **Where:** `frontend/tests/i18n-browser.mjs`, `llm-browser.mjs`,
    `layout-browser.mjs`, `upload-browser.mjs`, `llm-e2e.mjs` và các unit/form
    tests hiện có; `README.md`. Không sửa backend production.
  - **Done:** Chạy các lệnh frontend test/build/browser đã được README hướng
    dẫn. Báo pass/fail/skip và điều kiện Playwright/browser còn thiếu.
    Nếu thay backend test fixture/harness tích hợp, chạy thêm backend suite
    theo README. Không dùng key/provider/dev database thật để làm test locale.
    Browser check bị skip chưa đủ để đánh dấu task này hoàn tất.

### Ma trận kiểm thử tối thiểu

| Nhóm | Kịch bản và assertion chính |
| --- | --- |
| Resolver | Storage hợp lệ thắng navigator; storage giả bị bỏ qua; exact/base tag và thứ tự ưu tiên theo bảng. |
| Storage | Đọc/ghi bị chặn vẫn dùng được UI; đổi locale không tạo entry chứa dữ liệu ngoài mã locale. |
| Catalog | English đầy đủ; các locale có đủ logical keys/plural/placeholder; thiếu/rỗng có fallback test riêng. |
| Đăng nhập | Ba locale hiển thị label, busy, lỗi sai credentials và lỗi mạng; đổi locale giữ input. |
| Session | Reload giữ lựa chọn; logout/login khác tài khoản giữ locale và không giữ dữ liệu tài khoản cũ. |
| LLM | Dịch lỗi 401/403/422/502/503, notices và source personal/server/none; giữ URL/key đang nhập và selected model. |
| Model | Giữ search text, selected ID và catalog; đổi locale không GET models hoặc PATCH lại selection. |
| Upload | Giữ project/file/title/software/version; không POST trùng; polling tiếp tục với revision cũ và nhãn mới. |
| Stream | Giữ question/answer, không POST chat lần hai hoặc abort; completed/citations/error còn đúng. |
| Existing error | Lỗi chat cũ, upload error, model error và success notice chuyển sang locale mới không cần request mới. |
| Data/XSS | Tên model/tài liệu/answer chứa HTML vẫn là text; không dịch external data hoặc hiện raw provider error. |
| Plural/format | Russian/English/Vi theo các count đã nêu; size boundaries và dấu thập phân theo locale. |
| Request contract | Không thêm locale vào payload/header; network traffic khi đổi locale chỉ có request nghiệp vụ vốn đang chạy. |
| Layout/a11y | Ba locale, ba viewport; selector focus/label/tab order; nhãn Russian dài và dữ liệu dài không che control. |

Spec hoàn tất khi tài liệu được lưu và rà soát. Feature chỉ hoàn tất khi toàn
bộ task cùng acceptance criteria được triển khai và xác minh; các checkbox
được đánh dấu sau khi triển khai và kiểm tra thành công.


## Implementation verification — 2026-10-09

Hoàn tất F008-001 đến F008-007 và AC-01 đến AC-20. Phạm vi triển khai chỉ
thêm locale giao diện. Các thay đổi proxy/backend và layout có sẵn trong
worktree được giữ nguyên. Không thay hợp đồng API, SSE, ACL hoặc schema.

### File và trách nhiệm

Các đường dẫn dưới đây tính từ repository root. Component dùng cùng store,
không remount khi đổi locale; các form giữ state và request đang chạy.

| File | Thay đổi chính và lý do |
| --- | --- |
| `frontend/package.json` | Thêm duy nhất dependency runtime i18next; không thêm detector/backend/parser. |
| `frontend/package-lock.json` | Khóa dependency i18next theo bản npm đã cài. |
| `frontend/src/lib/i18n/locale.ts` | `isLocale` kiểm tra registry; `resolveInitialLocale(saved, preferred)` trả mã hỗ trợ theo storage, navigator và fallback Vietnamese. Resolver không cần DOM. |
| `frontend/src/lib/i18n/index.ts` | `initI18n` nạp tĩnh, khởi tạo một lần; `setLocale` đổi store/HTML và lưu lựa chọn thủ công; `formatFileSize(bytes, locale)` trả chuỗi binary size theo Intl. `snapshot` dịch thông báo và tính formattedCount ở lúc render. |
| `frontend/src/lib/i18n/messages.ts` | `MessageKey`, `UiMessage`, `message` và `llmErrorMessage` giữ key/params an toàn; không giữ bản dịch cũ trong state. |
| `frontend/src/lib/i18n/locales/languages.json` | Registry ba locale và tên bản địa, dùng chung cho selector/resolver. |
| `frontend/src/lib/i18n/locales/vi-VN/translation.json` | Catalog Vietnamese tường minh; plural source count và tham số thống nhất. |
| `frontend/src/lib/i18n/locales/en-US/translation.json` | Catalog English tường minh và nguồn fallback bản dịch. |
| `frontend/src/lib/i18n/locales/ru-RU/translation.json` | Catalog Russian, gồm one/few/many/other của số nguồn. |
| `frontend/src/lib/i18n/message-inventory.md` | Bản đồ khóa, callsite trước locale, nguồn legacy, tham số và allowlist dữ liệu/token. |
| `frontend/src/main.ts` | Chờ initI18n trước mount, tránh hiển thị nhầm locale ở frame đầu. |
| `frontend/index.html` | HTML fallback lang là vi-VN. |
| `frontend/src/App.svelte` | Dịch heading/title/meta và auth/model/upload/chat fallback; chuyển state lỗi sang UiMessage; đặt selector ở login topbar. |
| `frontend/src/lib/chat-turn.ts` | ChatTurn.error giữ UiMessage hoặc null; lỗi turn cũ dịch lại khi locale đổi. |
| `frontend/src/lib/auth-api.ts` | AuthApiError giữ safe UiMessage và HTTP status; fetch cookie/CSRF giữ nguyên. |
| `frontend/src/lib/llm-api.ts` | LlmApiError ánh xạ status sang safe key; không hiện payload provider có thể chứa secret. |
| `frontend/src/lib/documents-api.ts` | DocumentsApiError giữ safe key và status; multipart/polling contract giữ nguyên. |
| `frontend/src/lib/chat-api.ts` | ChatApiError giữ code và safe key; parser/SSE/fetch giữ nguyên, API không phụ thuộc DOM. |
| `frontend/src/lib/components/LanguageSelector.svelte` | Native select có visible label, keyboard/focus, dùng tên bản địa; không bị khóa bởi busy operation. |
| `frontend/src/lib/components/AppNavigation.svelte` | Dịch navigation/logout, thêm selector trên account; tên account giữ nguyên. |
| `frontend/src/lib/components/LoginForm.svelte` | Dịch label/busy/error; giữ email/password khi locale đổi. |
| `frontend/src/lib/components/LlmConnectionForm.svelte` | Dịch URL/key/help/action/source/busy; error và notice giữ key, URL/key nhập giữ nguyên. |
| `frontend/src/lib/components/ModelSelector.svelte` | Dịch label/search/empty/error/prefix; tên model/search/catalog/selection giữ nguyên. |
| `frontend/src/lib/components/DocumentUploadPanel.svelte` | Dịch form/status/error; file size dùng locale; metadata/file/project và polling giữ nguyên. |
| `frontend/src/lib/components/ChatComposer.svelte` | Dịch label/placeholder/send/hint; draft và IME handling giữ nguyên. |
| `frontend/src/lib/components/ChatConversation.svelte` | Dịch welcome/conversation/loading/error; câu hỏi/answer vẫn là plain text nguyên văn. |
| `frontend/src/lib/components/CitationSources.svelte` | Summary dùng plural raw count; dịch metadata labels, giữ source data và trạng thái expanded. |
| `README.md` | Hướng dẫn chọn/lưu locale, phạm vi dịch, thêm khóa và chạy kiểm tra. |

### Test và kết quả

Chạy từ `frontend/`, với RUVIE_PLAYWRIGHT_PATH và RUVIE_BROWSER_PATH được
thiết lập theo README cho browser harness:

- `npm.cmd test`: **28 pass, 0 fail, 0 skip**. Resolver, idempotence, catalog
  logical keys/placeholders, English callsites, fallback thiếu/rỗng, safe errors
  cả ba locale, plural Russian/English/Vi và binary size boundaries.
- `npm.cmd run build`: **pass**. Built bundle nạp ba catalog tĩnh.
- `node tests/llm-browser.mjs`: **66 checks pass, 0 fail, 0 skip**. Bao gồm
  hồi quy có sẵn và locale checks: native keyboard, storage lỗi/giả, input/file/
  search/selection, lỗi cũ/notices, delayed login/model/connect, upload/polling,
  SSE completed/error, không request trùng, source expanded, plain-text data,
  9 tổ hợp locale/viewport và không horizontal overflow.

Chạy từ repository root, với Node/browser paths theo README:

- `.venv/Scripts/python.exe -m unittest discover -s tests`:
  **146 pass, 0 fail, 0 skip**; disposable PostgreSQL/provider và browser backend
  integration chạy thật. Không dùng development DB hoặc API key thật.
- `git diff --check -- frontend README.md specs/feat/F008-ui-localization.md`:
  **pass**, không có lỗi whitespace.

`i18n.test.mjs` bổ sung unit/catalog checks; `i18n-browser.mjs` bổ sung fake-API
locale scenarios. `llm-browser.mjs` gọi runLocaleChecks. `llm-form.test.mjs`
khởi tạo locale trước SSR render. `llm-browser.mjs`, `layout-browser.mjs`,
`upload-browser.mjs`, `llm-e2e.mjs` cố định baseline vi-VN để hồi quy không
phụ thuộc ngôn ngữ máy chạy.

### Tái sử dụng và giới hạn

Đã thích nghi languageChanged/store và cập nhật HTML từ
`references/src/lib/i18n/index.ts`, registry names và một số bản dịch chung từ
legacy catalogs. Inventory ghi khóa legacy cụ thể. Core active thay detector/
dynamic import và literal keys bằng resolver thuần, static catalogs và semantic
keys. Không import hoặc chạy runtime references.

Locale thuộc browser origin; không đồng bộ theo tài khoản/thiết bị/tab đang mở.
Chỉ dịch giao diện, không ép ngôn ngữ câu trả lời LLM hay dịch nội dung tài liệu.
Nếu storage bị chặn, lựa chọn vẫn dùng được trong phiên nhưng không bảo đảm lưu
sau reload. Không còn kiểm tra bắt buộc chưa chạy hoặc task F008 chưa hoàn tất.
