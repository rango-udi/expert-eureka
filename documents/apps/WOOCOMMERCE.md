[NAVIGATION](../NAVIGATION.md)

# WooCommerce

WooCommerce là mục tiêu cửa hàng native trong [danh mục ứng dụng](../APPS.md). Adapter dùng WordPress 7.1.4, PHP 8.3, Apache và MariaDB, với phiên bản 11.3.0. Nguồn khóa tại [source-lock.json](../../apps/woocommerce/config/source-lock.json).

## Chọn cách chạy

Một lệnh setup --app woocommerce --run-tests --accept-resource-risk cài đặt, mở cửa hàng và chạy smoke mặc định. Nếu chỉ thao tác thủ công, bỏ --run-tests. Robot tự build browser nên robot-init là tùy chọn chuẩn bị trước; robot cần web đang chạy và không nhận --dryrun/--test. Sau down, dùng start trước khi robot, hoặc setup --run-tests khi cần khởi tạo lại toàn luồng. Validate chỉ kiểm tra cấu hình/dữ liệu nguồn, không xác nhận UI hay checkout. Xem [COMMANDS](../guides/COMMANDS.md) và [WORKFLOWS](../guides/WORKFLOWS.md).

## Bắt đầu

```bat
cmdc.cmd setup --app woocommerce --accept-resource-risk
cmdc.cmd urls --app woocommerce
cmdc.cmd robot --app woocommerce --accept-resource-risk
cmdc.cmd down --app woocommerce
```

Hướng dẫn cài đặt, phạm vi lệnh, bảo vệ dữ liệu, cổng và xử lý lỗi nằm trong [NATIVE_COMMERCE](../guides/NATIVE_COMMERCE.md). Cổng khởi tạo là 8086, storefront http://127.0.0.1:8086/ và quản trị http://127.0.0.1:8086/wp-admin/. Credential được sinh riêng trong apps/woocommerce/.env; dùng ADMIN_EMAIL để đăng nhập hoặc username avery. Giữ cấu hình đó cùng volume sau cài đặt.

## Dữ liệu và giao diện

Khởi tạo WordPress và plugin WooCommerce đã khóa. Seed dùng WC_Product_Simple, product_cat và media native, tạo 16 sản phẩm và Mira Solen khi chưa tồn tại. Theme fuzcake Fragrance House hiển thị catalogue và giữ cart/checkout/account native. COD và phí fuzcake Delivery đọc từ nguồn chung; ví, staff và lịch sử giao dịch chưa được ánh xạ.

Nguồn chung theo [SHARED_DATA](../guides/SHARED_DATA.md). Chỉnh giá, tên và tồn kho đã lưu qua quản trị của WooCommerce; setup không áp lại dữ liệu nguồn lên sản phẩm đã tồn tại.

## Cấu hình và bảo trì

Đọc chú thích trước mỗi khóa trong [.env.template](../../apps/woocommerce/.env.template). Cấu trúc dịch vụ ở [compose.yaml](../../apps/woocommerce/compose.yaml). Web chỉ mở trên loopback; database không publish cổng. Chạy resources/logs/status với --app woocommerce để kiểm tra mà không cần xác nhận tải.

PHP memory_limit và số worker Apache được giới hạn trong Dockerfile. Cần ngân sách cho database, trình cài đặt và xử lý ảnh bên cạnh web.

Chỉ start khi setup đã hoàn tất. Khi lỗi, dùng diagnostics --app woocommerce và giữ .env/volume. Với dữ liệu có thể xóa, dùng destroy --app woocommerce --yes theo phạm vi trong hướng dẫn chung; down không xóa dữ liệu. Kết quả kiểm chứng theo phiên bản tại nhật ký cập nhật (lưu riêng trong bản bàn giao đầy đủ).

[NAVIGATION](../NAVIGATION.md)
