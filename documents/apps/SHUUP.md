[NAVIGATION](../NAVIGATION.md)

# 🛍️ Shuup

Tra ID và cơ chế chọn app tại [APPS](../APPS.md). Adapter tích hợp [shuup/shuup](https://github.com/shuup/shuup), tag v3.1.0, bằng distribution có SHA-256 khóa tại [source-lock.json](../../apps/shuup/config/source-lock.json). Storefront dùng theme fuzcake riêng trên view thương mại, CSS/JS và cơ chế giá/giỏ hàng của Shuup upstream. Navigation, menu CMS/mở rộng, ngôn ngữ, tài khoản, basket và placeholder front_content dùng thành phần native. Quản trị sử dụng các module upstream với dữ liệu cửa hàng được đặt tên nhất quán.

Hồ sơ Excel, nhập kết quả và ảnh BVA/EP/decision: [SHUUP_CUSTOMER_REPORT](../guides/SHUUP_CUSTOMER_REPORT.md). Lệnh `cmdc.cmd report --app shuup` luôn xuất Excel; thêm `--media` để tạo PNG/SVG hoặc `--results reports/output.xml` để đưa một lần chạy tự động vào sheet Truy vết. Kết quả ca nghiệp vụ không được suy ra từ ID Robot.

## Chọn cách chạy

- Lần đầu chỉ mở cửa hàng: setup --app shuup; lệnh đã start web.
- Chuẩn bị và chạy suite mặc định ngay: setup --app shuup --run-tests.
- Chuẩn bị browser để chạy sau: setup --app shuup --with-robot; tùy chọn này không chạy test.
- App đã có, chỉ chạy UI: robot --app shuup; tự build browser có cache và bảo đảm web chạy. Không bắt buộc robot-init trước.
- Chỉ mở lại app sau down: start --app shuup; không cần setup lại.

Validate kiểm tra nội bộ trong container, dryrun kiểm tra cấu trúc, robot thực thi UI; đây là các lựa chọn theo mục tiêu. Phạm vi cụ thể tại [COMMANDS](../guides/COMMANDS.md); cách viết/chạy test tại [WORKFLOWS](../guides/WORKFLOWS.md). Các khối lệnh bên dưới minh họa từng công việc, không yêu cầu chạy hết mỗi phiên.

## Khởi tạo và truy cập

```bat
cmdc.cmd setup --app shuup
cmdc.cmd urls --app shuup
cmdc.cmd status --app shuup
```

Urls trả hai điểm vào có thể mở bằng browser: cửa hàng và quản trị. Trong từng hành trình, dùng link, menu, nút và form. Quản trị bắt đầu tại liên kết Administration; email trong .env cũng là username đăng nhập. Customer/staff/admin có secret riêng, được sinh khi khởi tạo.

Cấu hình tại apps/shuup/.env, sinh từ [.env.template](../../apps/shuup/.env.template). Dữ liệu SQLite, media, static và email thử nằm trong apps/shuup/.runtime/data; reports/backups thuộc app. Root không chứa secret của Shuup. Namespace Docker là robot-web-shuup.

## Bộ kiểm thử customer đầy đủ

Chạy robot --app shuup --customer sau setup, hoặc setup --app shuup --run-tests --customer để chuẩn bị và chạy trong một lệnh. Bộ ca đi từ đăng ký/kích hoạt email/đăng nhập tới tìm ba sản phẩm, giỏ, coupon, địa chỉ, giao hàng, COD và mở lại đúng đơn. Các probe âm độc lập áp EP/BVA; một E2E kiểm các rule và dữ liệu persisted. Chọn --customer-stage hoặc --customer-case thay cho bộ lọc Robot ở suite động này.

Setup tạo notification email đăng ký native khi shop chưa có script cho event đó; giữ script hiện hữu kể cả bị tắt. Không bỏ activation; thư local nằm trong .runtime/data/mail và suite đọc thư của khách vừa đăng ký. Nội dung đầy đủ: [phân tích/bảng ca](../guides/SHUUP_CUSTOMER_TEST_DESIGN.md), [đọc selector/keyword/Python](../guides/SHUUP_CUSTOMER_TEST_CODE.md). --design vẫn dành cho ví; smoke mặc định vẫn dùng để kiểm catalogue/admin/layout nhanh.

## Nghiệp vụ mẫu

fuzcake là cửa hàng nước hoa với 16 sản phẩm, bốn nhóm hương, hình ảnh người dùng cung cấp, nhận diện, trang giới thiệu, giao hàng và đối tác thanh toán. Nguồn fuzcake-data và cách nhận dữ liệu theo [SHARED_DATA](../guides/SHARED_DATA.md). Trang chủ nối đến sản phẩm thực trong database; giá và ảnh đã chỉnh qua quản trị được dùng khi hiển thị.

Customer duyệt catalogue, mở sản phẩm, thao tác giỏ hàng và đặt đơn theo phương thức giao hàng/thanh toán thủ công. Ba dịch vụ giao hàng hư cấu có phí riêng. Cửa hàng mới dùng USD; database cũ giữ USD/EUR hiện hữu và các mức giá khởi tạo được diễn giải theo tiền tệ đó. Không tự quy đổi hoặc thay tiền tệ của đơn và giá đã có. Quản trị dùng module sản phẩm, đơn hàng và khách hàng gốc của Shuup. Staff thuộc nhóm Boutique operations với quyền dashboard theo shop; quyền quản trị khác được cấp chủ động.

Menu Wallet mở ví cục bộ sau đăng nhập. Customer khởi tạo có sổ giao dịch, thẻ che số và ví điện tử được liên kết; nạp ví tạo giao dịch mô phỏng với token chống gửi lặp. Số dư chỉ cộng các dòng posted. Ví không gọi cổng thanh toán và không tự thanh toán đơn checkout Shuup. Đơn và vận đơn lịch sử trong JSON là dữ liệu tham chiếu, tách khỏi đơn Shuup phát sinh qua checkout.

Seed giữ mật khẩu, giá, tồn kho, theme tùy chỉnh và dữ liệu đã tồn tại. Khi database chưa có cửa hàng, seed gọi initializer upstream; chạy lại không gọi initializer để tránh đặt lại theme. Các nhãn Default Shop/Store và nhãn supplier/type mặc định được chuyển khi còn khớp scaffold; nội dung đã chỉnh được giữ. Bộ sản phẩm backpack/mug/notebook của database cũ vẫn giữ ID và quan hệ đơn hàng; trang chủ giới thiệu bộ sưu tập nước hoa. Dữ liệu mới dùng SKU/reference riêng, không ghi đè sản phẩm cũ.

Đổi mật khẩu tài khoản cũ qua manage changepassword hoặc chức năng quản trị; chỉnh .env không tự thay mật khẩu database. Với bản cài mới, danh tính Avery Vale, Mira Solen và Rowan Pike được gán theo vai trò; database cũ giữ thông tin tài khoản hiện hữu. Giữ .env và .runtime khi cập nhật source, rồi chạy setup --app shuup để áp dụng migration và bổ sung dữ liệu.

## Tài nguyên và phiên bản

Runtime thông thường chỉ có một web container với SQLite và xử lý task đồng bộ của upstream, không thêm PostgreSQL/Redis. Mặc định một thread, trần web/tools 512 MiB; browser có trần riêng 1024 MiB và chỉ build khi chọn Robot. Các con số là trần cấu hình, không phải RAM tối thiểu đã đo hoặc bảo đảm fit trên mọi máy.

Shuup v3.1.0 dùng dependency Django/Python thế hệ cũ. App image dùng Python 3.8.20 và constraints tương thích; Robot ở image Python 3.12 riêng. Target này dành cho kiểm thử local qua loopback; không triển khai như một cửa hàng production. Việc sửa metadata toml/pytz của wheel được ghi trong source lock, giữ nguyên mã ứng dụng, assets và giấy phép upstream.

## Kiểm thử và vận hành

| Mục tiêu | Cách gọi độc lập sau setup |
| --- | --- |
| Regression nội bộ/backend | `cmdc.cmd validate --app shuup` |
| Kiểm tra cấu trúc suite | `cmdc.cmd robot --app shuup --dryrun` |
| Chạy hành trình trên browser | `cmdc.cmd robot --app shuup` |
| Dừng và giữ dữ liệu | `cmdc.cmd down --app shuup` |

Chọn dòng phù hợp; không yêu cầu chạy validate và dryrun trước mỗi lượt UI. Khi cần kiểm tra cả backend lẫn UI, chạy validate rồi robot và dừng nếu bước đầu lỗi.

Validate chạy kiểm tra Django, unit cấu hình/sinh dữ liệu, HTTP và quy ước source/tài liệu. Robot smoke mở sản phẩm từ catalogue và đăng nhập quản trị qua form. Phạm vi smoke không chứng minh toàn bộ checkout hoặc hành trình seller; ghi nhận kết quả browser riêng theo [TESTING](../guides/TESTING.md).

Generate mặc định dùng mô hình ví và xuất suite DataDriver single-fault. Mô hình số lượng Rose Nocturne/thanh toán cũ chỉ dùng khi generate --legacy. Setup hỗ trợ --with-robot và --run-tests; giữ build cache để tránh tải lại dependency.

Backup lưu SQLite/media trong ZIP, bảo quản .env cùng bản sao dữ liệu. Restore cần --yes, chạy migration cho database phục hồi và giữ web dừng tới khi start lại. Reset db/data/all và destroy theo [COMMANDS](../guides/COMMANDS.md); cache của app này không phải cache RAM WSL. Trước khi chuyển app, down lựa chọn đang chạy.

## Catalogue và phản hồi giao diện

The collection trỏ tới route native shuup:all-categories. Liên kết theme cũ có view products được chuyển cho AllCategoriesView gốc để tiếp tục dùng bộ lọc và quyền hiển thị native. Các thẻ sản phẩm trên trang chủ do product_highlight trong placeholder front_content tạo; phần quản trị vẫn chỉnh được nội dung này.

Context processor chỉ tải nhóm hương cho trang chủ; trang sản phẩm, tài khoản và checkout dùng dữ liệu của view native. Static đã collect được lập chỉ mục khi web khởi động. Media tải lên vẫn được nhận trong lúc chạy; response giỏ hàng, checkout và tài khoản không được bọc cache toàn trang.

Khi phản hồi chậm, đối chiếu thời gian request trong Network của browser và resources --app shuup: phân biệt request HTML, ảnh/static, thumbnail lần đầu và áp lực RAM/CPU. WEB_THREADS là lựa chọn có chú thích trong .env.template; giữ giá trị đã cấu hình và đo trước/sau khi điều chỉnh. Nguyên tắc hiệu năng này không thay thế số đo trên máy vận hành.

## Khi khởi tạo thất bại

Build image và khởi tạo database là hai bước riêng. Nếu lỗi ở Initialize database and store data, đọc host task log được in ra và file apps/shuup/.runtime/django-<step>.log tương ứng. Thông báo nêu migrate, seed_demo, collectstatic hoặc reindex_product_catalog; các bước sau lỗi chưa được chạy.

Nếu lỗi báo shuup.core và storefront cùng khai báo SHUUP_PRICING_MODULE, kiểm tra StorefrontConfig.default_settings_module trỏ đến .default_settings. Shuup quét các tên viết hoa trong module mặc định của từng app; cấu hình dự án vẫn dùng storefront.settings để nhập và ghi đè giá trị upstream. Module storefront.default_settings chỉ khai báo mặc định thuộc app cục bộ, không import cấu hình dự án.

Sau khi cập nhật source sửa lỗi này, giữ .env và .runtime, rồi chạy:

```bat
cmdc.cmd setup --app shuup
cmdc.cmd validate --app shuup
```

Migrate nạp registry trước khi thao tác database. Sửa module mặc định không cần xóa database hay tạo lại tài khoản. Với bước Django đã chạy thành công, log tương ứng được cập nhật trạng thái OK để diagnostics không hiển thị lại lỗi của lần trước.

Adapter chuyển đường dẫn database/storage/email thành chuỗi để tương thích Django 2.2. Khi thay source sửa lỗi tương thích, giữ nguyên .env và .runtime, rồi chạy lại setup --app shuup. Migration và seed tiếp tục theo dữ liệu đã có; không dùng reset/destroy để xử lý lỗi kiểu đường dẫn.

Build lại dùng cache dependency sẵn có khi Docker vẫn giữ các layer. Chỉ xem lịch sử build khi bước build thất bại; logs --app shuup phục vụ tiến trình web, không thay thế log của tools container khởi tạo đã kết thúc.

## Thông tin khách hàng và mã giảm giá

Tài khoản CUSTOMER có PersonContact native và địa chỉ thanh toán/giao hàng mặc định từ customer-home trong fuzcake-data/records/store.json. Hai bản ghi địa chỉ độc lập để chỉnh Billing information không làm đổi Shipping information. Setup chỉ bổ sung mặc định còn thiếu, giữ địa chỉ và thông tin đã sửa; tài khoản khác không được gán địa chỉ của khách hàng mẫu.

COUPON_CODE trong apps/shuup/.env.template mặc định FUZCAKE10: mã cố định giảm 10% tiền hàng qua BasketCampaign native, không giảm phí dịch vụ. Dùng tại ô mã giảm giá của giỏ hàng. Mã không có thời hạn hoặc giới hạn lượt dùng trong dữ liệu khởi tạo để lặp hành trình kiểm thử. Để trống bỏ qua tạo campaign mới. Chỉ dùng 1–12 ký tự ASCII chữ/số/_/-; mã đang thuộc coupon khác khiến seed dừng với hướng dẫn đổi cấu hình, không chiếm dụng coupon đó.

Setup bổ sung khóa cấu hình còn thiếu vào .env. Campaign chỉ tạo lần đầu; thay COUPON_CODE sau đó không đổi mã, tỷ lệ, trạng thái hoặc lịch sử đã có. Quản lý campaign hiện hữu qua quản trị Shuup. Giữ .env và .runtime khi chạy lại setup.

## Checkout, session và thiết kế test

Checkout native lưu địa chỉ chưa persist trong session. Adapter dùng CheckoutJSONSerializer với tag allowlist cho MutableAddress/CompanyContact, không dùng pickle và không import class từ payload; session JSON cũ vẫn đọc được. Lỗi request được ghi giới hạn dung lượng tại .runtime/data/request-errors.log, đọc bằng cmdc diagnostics --app shuup. Log có thể chứa nội dung exception nên cần xem lại trước khi chia sẻ.

Khi Continue báo 500, lấy traceback từ diagnostics và đối chiếu bước lỗi; không suy nguyên nhân chỉ từ ảnh trang lỗi. Giữ .env/.runtime, cập nhật source rồi setup; không reset database để xử lý serializer. Regression native storage và browser Continue nằm trong validate/robot.

Generate mặc định xuất suite DataDriver single-fault. [AUTOMATED_TEST_DESIGN](../guides/AUTOMATED_TEST_DESIGN.md) mô tả model, thư viện, giảm ca, oracle và lệnh robot --design. Generate --legacy giữ CSV cũ để đọc lại.

## Mã nguồn và giấy phép

Mã adapter, Docker, cấu hình và tests nằm trong apps/shuup; package tích hợp Django là storefront. [SHUUP_LICENSE](../licenses/SHUUP_LICENSE) giữ văn bản OSL-3.0 đi kèm nguồn khóa; metadata setup upstream có classifier khác nên tham chiếu văn bản LICENSE trực tiếp. Phạm vi bên thứ ba tại [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md).

[NAVIGATION](../NAVIGATION.md)
