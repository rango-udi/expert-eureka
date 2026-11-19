[NAVIGATION](../NAVIGATION.md)

# 🛍️ Wowy

Tra ID và lựa chọn tại [APPS](../APPS.md). Adapter tích hợp [manjurulhoque/wowy](https://github.com/manjurulhoque/wowy) theo commit khóa trong [source-lock.json](../../apps/wowy/config/source-lock.json). Mô hình sản phẩm, tài khoản, giỏ, đơn hàng và phần lớn trang quản trị được giữ từ upstream; settings, dữ liệu khởi tạo và xử lý checkout cục bộ nằm trong apps/wowy.

## Chọn cách chạy

- Lần đầu chỉ mở cửa hàng: setup --app wowy; lệnh đã start web.
- Chuẩn bị và chạy suite mặc định ngay: setup --app wowy --run-tests.
- Chuẩn bị browser để chạy sau: setup --app wowy --with-robot; tùy chọn này không chạy test.
- App đã có, chỉ chạy UI: robot --app wowy; tự build browser có cache và bảo đảm web chạy. Không bắt buộc robot-init trước.
- Chỉ mở lại app sau down: start --app wowy; không cần setup lại.

Validate kiểm tra nội bộ trong container, dryrun kiểm tra cấu trúc, robot thực thi UI; đây là các lựa chọn theo mục tiêu. Phạm vi cụ thể tại [COMMANDS](../guides/COMMANDS.md); cách viết/chạy test tại [WORKFLOWS](../guides/WORKFLOWS.md). Các khối lệnh bên dưới minh họa từng công việc, không yêu cầu chạy hết mỗi phiên.

## Khởi tạo và truy cập

```bat
cmdc.cmd setup --app wowy
cmdc.cmd urls --app wowy
cmdc.cmd status --app wowy
```

Mở Storefront để duyệt cửa hàng. Đăng nhập bằng email/password của vai trò trong apps/wowy/.env. Administrator có liên kết Administration trên thanh điều hướng; đường quản trị Django chuẩn nằm ở /super-admin/. Customer và staff không được đọc khu vực quản trị tùy biến. Staff là tài khoản nhân viên giới hạn, không phải seller độc lập.

Mẫu [.env.template](../../apps/wowy/.env.template) tạo .env riêng; các secret được sinh riêng cho app. SQLite, ảnh tải lên, static đã thu thập và email cục bộ nằm trong .runtime/data. Khi chuyển app, chạy down --app của ứng dụng đang hoạt động trước.

## Dữ liệu và hành trình

Wowy đọc danh mục, nhận diện, địa chỉ và đối tác giao hàng từ [SHARED_DATA](../guides/SHARED_DATA.md). Cửa hàng có 16 sản phẩm nước hoa, bốn nhóm hương và các tài khoản hư cấu có tên nhất quán. Customer mới có hai địa chỉ trong sổ địa chỉ. Setup lặp giữ giá, tồn kho, mật khẩu, quyền và đơn hàng; thay .env không đổi mật khẩu đã lưu trong database.

Hành trình customer: bộ sưu tập → sản phẩm → thêm giỏ → Checkout → chọn địa chỉ, dịch vụ giao hàng và COD → xác nhận → My orders. Các thao tác đi qua link, nút và form. Wishlist và sổ địa chỉ dùng các trang native. Đường Forgot Password cung cấp chỉ dẫn khôi phục tài khoản local qua administrator; không mô tả đây là một luồng gửi email phục hồi đã tích hợp.

Hành trình admin: đăng nhập → Administration → Products/Categories/Orders/Customers/Reports. Middleware kiểm tra quyền cho toàn bộ namespace quản trị tùy biến, kể cả những view upstream chỉ có login_required. Có thể đổi trạng thái đơn qua form quản trị. Đơn đã hủy được giữ lịch sử; tạo đơn mới khi cần mua lại.

## Tổng tiền, tồn kho và lịch sử

Tổng sản phẩm lưu ở total_amount; phí giao hàng lấy từ đối tác đã chọn và cộng một lần trong grand_total. Server đọc giá và phí từ dữ liệu sở hữu, không dùng số tiền client gửi lên. COD được ghi nhận ở trạng thái chưa thanh toán.

Checkout dùng transaction, cập nhật tồn kho có điều kiện và receipt có token duy nhất. Số lượng tổng trong giỏ phải nằm trong tồn kho; variant phải thuộc sản phẩm đã chọn và dùng giá/tồn kho của chính variant. Snapshot giữ SKU, tên, số lượng, giá và variant của dòng đơn. Địa chỉ giao hàng được sao chép cho đơn, tách khỏi địa chỉ có thể chỉnh trong sổ địa chỉ.

Hủy đơn pending chưa thanh toán hoàn lại phần tồn kho đã giữ đúng một lần. Sản phẩm/variant đã được snapshot bảo vệ lịch sử; dùng trạng thái không hoạt động khi cần ngừng bán. Phương thức COD và danh sách giao hàng là phạm vi của adapter; bộ dữ liệu ví/ngân hàng chung chỉ được nạp ở app có profile nghiệp vụ tương ứng. Wowy không cung cấp fuzcake Wallet.

## Runtime và nguồn

Runtime mặc định có một web container, một thread và SQLite; web/tools mặc định trần 512 MiB, browser có trần riêng 1024 MiB và được build khi chọn Robot. Đây là cấu hình giới hạn, không phải yêu cầu RAM tối thiểu đã đo. App không cần PostgreSQL, Redis hoặc worker thường trực.

Image dùng Python 3.12 và Django 5.2 theo requirements khóa. Build lấy commit và kiểm tra tree Git trước khi sao chép phần runtime. Database, media, fixtures và settings mặc định đi kèm repository upstream được loại khỏi phần tích hợp; database riêng được tạo bằng migration. Stripe/dj-stripe được thay bằng checkout COD cục bộ. Nguồn native nằm tại /opt/wowy trong image; lớp điều chỉnh nằm trong storefront, overrides và scripts/prepare_upstream.py của adapter.

BuildKit/Compose cần hỗ trợ named build contexts để nhận fuzcake-data ngoài app. Build đầu tiên cần truy cập GitHub và kho package; các lần sau có thể dùng cache của nguồn khóa.

## Kiểm thử và phục hồi

| Mục tiêu | Cách gọi độc lập sau setup |
| --- | --- |
| Regression nội bộ/backend | `cmdc.cmd validate --app wowy` |
| Kiểm tra cấu trúc suite | `cmdc.cmd robot --app wowy --dryrun` |
| Chạy hành trình trên browser | `cmdc.cmd robot --app wowy` |
| Dừng và giữ dữ liệu | `cmdc.cmd down --app wowy` |

Chọn dòng phù hợp; không yêu cầu chạy validate và dryrun trước mỗi lượt UI. Khi cần kiểm tra cả backend lẫn UI, chạy validate rồi robot và dừng nếu bước đầu lỗi.

Validate kiểm tra Django, migration drift, CLI, nguồn chung và regression checkout/quyền truy cập trong database test riêng. Robot mở cửa hàng, đăng nhập, chọn sản phẩm, đặt COD và truy cập quản trị qua UI. Dryrun kiểm tra cú pháp/keyword, không thay thế browser thực tế. Đối chiếu phạm vi bằng chứng theo [TESTING](../guides/TESTING.md).

Lỗi khởi tạo có đường dẫn apps/wowy/.runtime/django-<step>.log; lỗi server nằm trong log container hoặc .runtime/server-errors.log. Giữ .env và .runtime khi sửa source rồi chạy lại setup. Backup/restore dùng SQLite và media theo [OPERATIONS](../guides/OPERATIONS.md); lưu bản source/dữ liệu chung cùng bộ backup để tái dựng đúng môi trường.

Giấy phép và phạm vi sửa nguồn tại [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md) và [WOWY_LICENSE](../licenses/WOWY_LICENSE).

[NAVIGATION](../NAVIGATION.md)
