[NAVIGATION](../NAVIGATION.md)

# 🛒 Django Oscar

Tra ID và cách lựa chọn tại [danh mục ứng dụng](../APPS.md). Adapter tích hợp storefront, dashboard, tài khoản customer/seller/admin và cash on delivery của Django Oscar. Nguồn khóa tại [SOURCE_LOCK](../../apps/oscar/config/source-lock.json).

## Chọn cách chạy

- Lần đầu chỉ mở cửa hàng: setup --app oscar; lệnh đã start web.
- Chuẩn bị và chạy suite mặc định ngay: setup --app oscar --run-tests.
- Chuẩn bị browser để chạy sau: setup --app oscar --with-robot; tùy chọn này không chạy test.
- App đã có, chỉ chạy UI: robot --app oscar; tự build browser có cache và bảo đảm web chạy. Không bắt buộc robot-init trước.
- Chỉ mở lại app sau down: start --app oscar; không cần setup lại.

Validate kiểm tra nội bộ trong container, dryrun kiểm tra cấu trúc, robot thực thi UI; đây là các lựa chọn theo mục tiêu. Phạm vi cụ thể tại [COMMANDS](../guides/COMMANDS.md); cách viết/chạy test tại [WORKFLOWS](../guides/WORKFLOWS.md). Các khối lệnh bên dưới minh họa từng công việc, không yêu cầu chạy hết mỗi phiên.

## Khởi tạo và dữ liệu

```bat
cmdc.cmd setup --app oscar
cmdc.cmd urls --app oscar
cmdc.cmd robot --app oscar
```

Cấu hình tại `apps/oscar/.env`, hoàn thiện từ [.env.template](../../apps/oscar/.env.template). Dữ liệu nằm trong `apps/oscar/.runtime/data`, báo cáo tại `apps/oscar/reports`, backup tại `apps/oscar/backups`. Compose project là robot-web-oscar. Package Django tại apps/oscar/storefront; SQLite, Whoosh và email file phục vụ kiểm thử tuần tự.

Trần mặc định web/tools 384 MiB, Robot 1024 MiB; một web thread. Điều chỉnh APP_MEMORY_LIMIT, ROBOT_MEMORY_LIMIT và WEB_THREADS theo nhu cầu. Setup hỗ trợ `--with-robot` và `--run-tests`.

## Hành trình

Customer chọn sản phẩm, thêm giỏ, đổi số lượng, áp voucher OSCAR10, checkout COD và xem lịch sử đơn trong Account. Seller mở Dashboard → Catalogue → Products, với phạm vi partner riêng. Admin mở Fulfilment → Orders và cập nhật trạng thái đơn.

Dữ liệu fuzcake được đọc từ [SHARED_DATA](../guides/SHARED_DATA.md): 16 sản phẩm nước hoa, bốn nhóm hương và ảnh dùng chung. Seed ánh xạ SKU thành UPC/StockRecord, bổ sung bản ghi thiếu và giữ mật khẩu, quyền, giá, tồn kho đã có. Sản phẩm cũ giữ ID và quan hệ đơn; bộ nội dung mới có SKU riêng. Mật khẩu tài khoản riêng được lưu trong .env; đổi mật khẩu người dùng đã tồn tại qua giao diện hoặc manage changepassword.

## Lệnh dữ liệu

Backup lưu SQLite/media vào ZIP. Reset db giữ media; reset cache xóa index; data/all xóa dữ liệu vận hành và reports. Restore cần `--yes`; chạy start sau khi hoàn tất. Destroy cần `--yes`, chỉ tác động dữ liệu và image của adapter; `--include-files` mở rộng sang secret và backups.

## Kiểm thử

Validate chạy kiểm tra Django, unit, HTTP integration, source và tài liệu. Robot kiểm tra storefront, voucher, COD, lịch sử đơn và dashboard. Kết quả thực thi theo phiên bản nằm trong nhật ký (lưu riêng trong bản bàn giao đầy đủ).

[NAVIGATION](../NAVIGATION.md)
