[NAVIGATION](../NAVIGATION.md)

# PrestaShop

PrestaShop là mục tiêu cửa hàng native trong [danh mục ứng dụng](../APPS.md). Adapter dùng PHP 8.3, Apache và MariaDB, với phiên bản 9.2.1, gói classic 6.1. Nguồn khóa tại [source-lock.json](../../apps/prestashop/config/source-lock.json).

## Chọn cách chạy

Một lệnh setup --app prestashop --run-tests --accept-resource-risk cài đặt, mở cửa hàng và chạy smoke mặc định. Nếu chỉ thao tác thủ công, bỏ --run-tests. Robot tự build browser nên robot-init là tùy chọn chuẩn bị trước; robot cần web đang chạy và không nhận --dryrun/--test. Sau down, dùng start trước khi robot, hoặc setup --run-tests khi cần khởi tạo lại toàn luồng. Validate chỉ kiểm tra cấu hình/dữ liệu nguồn, không xác nhận UI hay checkout. Xem [COMMANDS](../guides/COMMANDS.md) và [WORKFLOWS](../guides/WORKFLOWS.md).

## Bắt đầu

```bat
cmdc.cmd setup --app prestashop --accept-resource-risk
cmdc.cmd urls --app prestashop
cmdc.cmd robot --app prestashop --accept-resource-risk
cmdc.cmd down --app prestashop
```

Hướng dẫn cài đặt, phạm vi lệnh, bảo vệ dữ liệu, cổng và xử lý lỗi nằm trong [NATIVE_COMMERCE](../guides/NATIVE_COMMERCE.md). Cổng khởi tạo là 8085, storefront http://127.0.0.1:8085/ và quản trị http://127.0.0.1:8085/control/. Credential được sinh riêng trong apps/prestashop/.env; dùng ADMIN_EMAIL để đăng nhập. Giữ cấu hình đó cùng volume sau cài đặt.

## Dữ liệu và giao diện

Installer CLI dùng --fixtures=0 và nhận diện fuzcake, Avery Vale. Seed dùng Product/Category/Image/StockAvailable/Customer native, nhập 16 sản phẩm và nhóm hương; tạo Mira Solen nếu email chưa có. Giao diện dùng theme Classic native. Staff, địa chỉ khách, ví và phí giao hàng chung chưa được ánh xạ.

Nguồn chung theo [SHARED_DATA](../guides/SHARED_DATA.md). Chỉnh giá, tên và tồn kho đã lưu qua quản trị của PrestaShop; setup không áp lại dữ liệu nguồn lên sản phẩm đã tồn tại.

## Cấu hình và bảo trì

Đọc chú thích trước mỗi khóa trong [.env.template](../../apps/prestashop/.env.template). Cấu trúc dịch vụ ở [compose.yaml](../../apps/prestashop/compose.yaml). Web chỉ mở trên loopback; database không publish cổng. Chạy resources/logs/status với --app prestashop để kiểm tra mà không cần xác nhận tải.

PHP memory_limit và số worker Apache được giới hạn trong Dockerfile. Cần ngân sách cho database, trình cài đặt và xử lý ảnh bên cạnh web.

Chỉ start khi setup đã hoàn tất. Khi lỗi, dùng diagnostics --app prestashop và giữ .env/volume. Với dữ liệu có thể xóa, dùng destroy --app prestashop --yes theo phạm vi trong hướng dẫn chung; down không xóa dữ liệu. Kết quả kiểm chứng theo phiên bản tại nhật ký cập nhật (lưu riêng trong bản bàn giao đầy đủ).

[NAVIGATION](../NAVIGATION.md)
