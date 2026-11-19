[NAVIGATION](../NAVIGATION.md)

# nopCommerce

nopCommerce là mục tiêu cửa hàng native trong [danh mục ứng dụng](../APPS.md). Adapter dùng .NET 10 và PostgreSQL, với phiên bản 5.00.1. Nguồn khóa tại [source-lock.json](../../apps/nopcommerce/config/source-lock.json).

## Chọn cách chạy

Một lệnh setup --app nopcommerce --run-tests --accept-resource-risk cài đặt, mở cửa hàng và chạy smoke mặc định. Nếu chỉ thao tác thủ công, bỏ --run-tests. Robot tự build browser nên robot-init là tùy chọn chuẩn bị trước; robot cần web đang chạy và không nhận --dryrun/--test. Sau down, dùng start trước khi robot, hoặc setup --run-tests khi cần khởi tạo lại toàn luồng. Validate chỉ kiểm tra cấu hình/dữ liệu nguồn, không xác nhận UI hay checkout. Xem [COMMANDS](../guides/COMMANDS.md) và [WORKFLOWS](../guides/WORKFLOWS.md).

## Bắt đầu

```bat
cmdc.cmd setup --app nopcommerce --accept-resource-risk
cmdc.cmd urls --app nopcommerce
cmdc.cmd robot --app nopcommerce --accept-resource-risk
cmdc.cmd down --app nopcommerce
```

Hướng dẫn cài đặt, phạm vi lệnh, bảo vệ dữ liệu, cổng và xử lý lỗi nằm trong [NATIVE_COMMERCE](../guides/NATIVE_COMMERCE.md). Cổng khởi tạo là 8084, storefront http://127.0.0.1:8084/ và quản trị http://127.0.0.1:8084/Admin/. Credential được sinh riêng trong apps/nopcommerce/.env; dùng ADMIN_EMAIL để đăng nhập. Giữ cấu hình đó cùng volume sau cài đặt.

## Dữ liệu và giao diện

Trình cài đặt native tạo quản trị với ADMIN_EMAIL/ADMIN_PASSWORD và tắt dữ liệu minh họa. Danh mục 16 sản phẩm, nhóm hương, giá, tồn kho và ảnh được nhập qua XLSX/API quản trị native; SKU đã có được bỏ qua. Customer, staff, wallet và lịch sử giao dịch chưa được ánh xạ trong adapter này. Giao diện giữ theme và ghi nhận tác giả của nopCommerce.

Nguồn chung theo [SHARED_DATA](../guides/SHARED_DATA.md). Chỉnh giá, tên và tồn kho đã lưu qua quản trị của nopCommerce; setup không áp lại dữ liệu nguồn lên sản phẩm đã tồn tại.

## Cấu hình và bảo trì

Đọc chú thích trước mỗi khóa trong [.env.template](../../apps/nopcommerce/.env.template). Cấu trúc dịch vụ ở [compose.yaml](../../apps/nopcommerce/compose.yaml). Web chỉ mở trên loopback; database không publish cổng. Chạy resources/logs/status với --app nopcommerce để kiểm tra mà không cần xác nhận tải.

Gói release được kiểm SHA-256 và chỉ hỗ trợ Linux amd64. Giới hạn GC heap giúp giảm áp lực RAM nhưng không bao gồm toàn bộ native memory, JIT và cache. Giữ dòng powered by nopCommerce theo giấy phép đi kèm.

Chỉ start khi setup đã hoàn tất. Khi lỗi, dùng diagnostics --app nopcommerce và giữ .env/volume. Với dữ liệu có thể xóa, dùng destroy --app nopcommerce --yes theo phạm vi trong hướng dẫn chung; down không xóa dữ liệu. Kết quả kiểm chứng theo phiên bản tại nhật ký cập nhật (lưu riêng trong bản bàn giao đầy đủ).

[NAVIGATION](../NAVIGATION.md)
