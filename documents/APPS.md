[NAVIGATION](NAVIGATION.md)

# 🧩 Danh mục ứng dụng

Đây là điểm tham chiếu chung cho lựa chọn ứng dụng, cấu hình riêng và hành trình kiểm thử. Các tài liệu vận hành dùng danh mục này để tra phạm vi của từng adapter.

| ID dùng với --app | Mục tiêu | Môi trường | Tài liệu ứng dụng |
| --- | --- | --- | --- |
| oscar | Cửa hàng thương mại điện tử | Python/Oscar, SQLite, Whoosh trong Docker | [OSCAR](apps/OSCAR.md) |
| shuup | fuzcake: cửa hàng nước hoa, quản trị thương mại và ví mô phỏng cục bộ | Shuup, SQLite, task đồng bộ trong một web container | [SHUUP](apps/SHUUP.md) |
| wowy | fuzcake: cửa hàng nước hoa và quản trị Wowy | Python/Django, SQLite và checkout COD cục bộ trong Docker | [WOWY](apps/WOWY.md) |
| pretix | Bán vé và quản lý sự kiện | pretix, PostgreSQL, Redis, worker, scheduler, gateway và Mailpit trong Docker | [PRETIX](apps/PRETIX.md) |
| nopcommerce | Cửa hàng native và nhập catalogue fuzcake | .NET 10, PostgreSQL; Linux amd64 | [NOPCOMMERCE](apps/NOPCOMMERCE.md) |
| prestashop | Cửa hàng Classic và catalogue fuzcake | PHP, Apache, MariaDB | [PRESTASHOP](apps/PRESTASHOP.md) |
| woocommerce | Cửa hàng fuzcake với WooCommerce và COD cục bộ | WordPress, PHP, Apache, MariaDB | [WOOCOMMERCE](apps/WOOCOMMERCE.md) |

Mọi adapter đều nằm tại `apps/<id>` với Docker, .env.template, script và test riêng.

Cấu hình nhận diện tại [apps.list](../config/apps.list) quy định ID, Compose project và thư mục ứng dụng. Lệnh `cmdc apps` hiển thị ID và tên từ registry. Dùng `cmdc apps --names` để chỉ in tên, `cmdc apps --ids` để lấy ID và `cmdc apps --raw` để xem bản ghi đầy đủ. Dùng một ID duy nhất cho mỗi tác vụ:

```bat
cmdc.cmd setup --app oscar --run-tests
cmdc.cmd down --app oscar
```

Ví dụ này khởi tạo/chạy suite Oscar rồi dừng và giữ dữ liệu. Để chọn app khác, thay ID và thêm cờ xác nhận tải nếu adapter yêu cầu; không chạy setup app mới khi app cũ vẫn hoạt động.

Nhóm PHP/.NET dùng --accept-resource-risk hoặc xác nhận ID tại prompt. Xem [NATIVE_COMMERCE](guides/NATIVE_COMMERCE.md) để tra điều kiện Docker, cổng, dữ liệu và các lệnh được hỗ trợ.

Các cách chạy theo từng app là lựa chọn theo nhu cầu, không phải quy trình phải chạy hết. Setup đã mở web; start dành cho lần mở lại sau khi dừng. Dùng setup --run-tests để gộp chuẩn bị và chạy suite mặc định; xem [WORKFLOWS](guides/WORKFLOWS.md) để chọn cách chạy.

Setup chỉ chuẩn bị ứng dụng được chọn. Mỗi lệnh vận hành cần lựa chọn rõ ràng; lựa chọn trước đó không được dùng làm mặc định cho lệnh sau. Một Docker engine chỉ chạy một ứng dụng workspace tại một thời điểm thông qua launcher.

| Tác vụ | Cách sử dụng |
| --- | --- |
| Khởi tạo | `setup --app <id>` |
| Khởi chạy / dừng | `start --app <id>` / `down --app <id>` |
| Kiểm thử UI | `robot --app <id>` |
| Chuẩn bị browser | `robot-init --app <id>` |
| Log lỗi khởi tạo cục bộ | `diagnostics --app <id>`; dùng được khi Docker đã dừng |
| Tra cứu trạng thái | `status --app <id>`, `resources --app <id>` |
| Lệnh hệ thống chung | `help`, `apps`, `version`, `doctor`, `wsl-vm-limit-help` |

Pretix yêu cầu cảnh báo và xác nhận riêng trước tác vụ có thể tạo tải: gõ pretix trên terminal tương tác hoặc thêm --accept-pretix-risk cho từng lần gọi. Tra [hướng dẫn RAM Pretix](helps/PRETIX_RESOURCE_PRESSURE.md) trước khi chọn stack này.

Dữ liệu khởi tạo dùng chung được quản lý theo [SHARED_DATA](guides/SHARED_DATA.md), với profile phù hợp cho mỗi app. Các adapter có phạm vi lệnh khác nhau; bảng trên là điểm tra cứu, không phải cam kết mọi lệnh có trên mọi app. Tra tùy chọn riêng trong tài liệu ứng dụng. Xem [COMMANDS](guides/COMMANDS.md), [APP_LIFECYCLE](guides/APP_LIFECYCLE.md) và [MEMORY](guides/MEMORY.md) trước khi đổi ứng dụng hoặc dữ liệu.

[NAVIGATION](NAVIGATION.md)
