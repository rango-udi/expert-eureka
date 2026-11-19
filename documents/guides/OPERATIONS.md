[NAVIGATION](../NAVIGATION.md)

# 🔧 Vận hành và xử lý lỗi

## Kiểm tra môi trường

| Nhu cầu | Lệnh hoặc tài liệu |
| --- | --- |
| Kiểm tra engine và Compose | `cmdc doctor` |
| Xem container | `cmdc status --app <id>` |
| Xem địa chỉ cửa hàng | `cmdc urls --app <id>` |
| Xem log ứng dụng | `cmdc logs --app <id>` |
| Xem RAM/CPU container | `cmdc resources --app <id>` |
| Cấu hình RAM WSL | `cmdc wsl-vm-limit-help` và [hướng dẫn WSL](../helps/WSL_VM_MEMORY_LIMIT.md) |

Khi engine chưa sẵn sàng, mở Docker và kiểm tra chế độ Linux containers. Khi vượt ngưỡng RAM, đối chiếu RAM VM với mốc cộng dung sai đang có hiệu lực, áp dụng thay đổi rồi kiểm tra lại.

## Tiến độ build in thành nhiều khung

BuildKit cập nhật cùng một bảng bằng lệnh điều khiển con trỏ. Console không xử lý VT, đầu ra bị ghi qua pipe hoặc môi trường ép tty có thể biến các khung đó thành nhiều dòng. Số giây tăng cùng bước build và dòng FINISHED biểu thị một lượt build, không tự chứng minh launcher đang build lại.

Launcher kiểm tra terminal, bật VT trên Windows khi được hỗ trợ và chọn plain khi không thể vẽ lại. Có thể đặt CMDC_UI=plain cho phiên thu log; CI, pipe và NO_COLOR dùng văn bản. Dùng terminal có hỗ trợ VT để giữ màu, spinner và bảng tiến độ cố định. [ENVIRONMENT](ENVIRONMENT.md) mô tả cấu hình hiển thị.

## RAM tăng trong hoặc sau khi tải image

Đối chiếu phạm vi số đo tại [MEMORY](MEMORY.md). Đặt trần VM và giảm tải layer đồng thời để hạn chế đỉnh khi pull; dùng autoMemoryReclaim để trả page cache sau tác vụ. [Hướng dẫn WSL](../helps/WSL_VM_MEMORY_LIMIT.md) có mẫu đầy đủ và quy trình xác nhận. RAM vẫn cao khi WSL còn bận không chứng minh reclaim đã lỗi; kiểm tra tác vụ cùng VM và so sánh sau khi down app.

## Pretix mất kết nối khi start

EOF qua dockerDesktopLinuxEngine cần kiểm tra cả engine, RAM và đĩa; không tự kết luận OOM. Dừng lặp setup, phục hồi Docker rồi đối chiếu State.OOMKilled/ExitCode/logs. Quy trình giữ dữ liệu và xử lý khóa tại [PRETIX_RESOURCE_PRESSURE](../helps/PRETIX_RESOURCE_PRESSURE.md).

## Chẩn đoán theo log

Chạy diagnostics --app <id> để đọc log khởi tạo/migration trên máy mà không cần khởi động Docker. Lệnh che secret đã cấu hình trong .env và giới hạn 120 dòng cuối mỗi file; kiểm tra nội dung trước khi chia sẻ. Log task của launcher có thể chỉ chứa thông báo lớp ngoài, nên cần log backend của chính bước thất bại.

| Phạm vi lỗi | File chi tiết |
| --- | --- |
| Thao tác Docker | Đầu ra terminal; lịch sử build trong Docker Desktop → Builds hoặc `docker buildx history logs` |
| Launcher Oscar trên Windows | `apps/oscar/.runtime/launcher-errors.log` |
| Quản trị Oscar trong container | `apps/oscar/.runtime/maintenance-errors.log` |
| Khởi tạo PHP | apps/prestashop/.runtime/prestashop-install.log và .runtime/seed-diagnostic.log của app; giữ riêng theo [NATIVE_COMMERCE](NATIVE_COMMERCE.md) |
| Khởi động Oscar | `apps/oscar/.runtime/server-errors.log` |

Thông báo terminal nêu bước xử lý tiếp theo và vị trí log khi ghi được. Kiểm tra nội dung nhạy cảm trước khi chia sẻ log.

Nếu database chưa được khởi tạo, chọn setup khi cần image/cấu hình và mở web luôn; init dành cho image đã có và hành vi riêng của adapter theo [COMMANDS](COMMANDS.md). Nếu container bị OOM, kiểm tra giới hạn của thành phần liên quan theo [MEMORY](MEMORY.md). Lấy lại URL sau mỗi lần tạo lại container bằng urls --app <id>.

## Shuup lỗi khởi tạo sau khi image đã build

Xem tên bước Django và file apps/shuup/.runtime/django-<step>.log hoặc host task log được launcher in ra. Tools container khởi tạo là one-off; log web chưa chắc có thông tin của bước đó. Dùng diagnostics --app shuup để lấy lỗi migration. Thông báo có Cause nêu exception backend đã che secret cấu hình; không kết luận lỗi schema/dependency nếu log chỉ có thông báo launcher. Giữ .env/database, sửa source/cấu hình rồi chạy lại setup --app shuup. Xem [SHUUP](../apps/SHUUP.md) để phân biệt lỗi build, khởi tạo và web startup.

## PrestaShop lỗi installer

Chạy diagnostics --app prestashop. Log apps/prestashop/.runtime/prestashop-install.log giữ stdout và stderr installer theo cùng thứ tự; task log in đoạn cuối để thấy lỗi gốc ngay tại terminal. Exit code và đường dẫn log giúp phân biệt lỗi tham số, quyền ghi, kết nối database và thiếu RAM; các khả năng này cần được đối chiếu từ log cụ thể.

Giữ .env và volume khi cần dữ liệu. Nếu dữ liệu khởi tạo có thể xóa, destroy --app prestashop --yes dọn riêng stack đó rồi setup lại; đây là thao tác xóa dữ liệu, không phải cách sửa migration cho database cần giữ. Phạm vi theo [NATIVE_COMMERCE](NATIVE_COMMERCE.md).

## Lựa chọn và tranh khóa

Tra [APPS](../APPS.md) để chọn phạm vi và [APP_LIFECYCLE](APP_LIFECYCLE.md) để xử lý khóa, trạng thái còn lại hoặc ownership khác workspace.

Nếu Windows báo lỗi template khi đọc nhãn hoặc báo không xác minh được operation lock, xem mục phục hồi Windows trong [APP_LIFECYCLE](APP_LIFECYCLE.md). Đọc diagnostic task log trước khi xử lý khóa còn lại.

## Sao lưu và phục hồi

Dùng backup khi các tiến trình ghi đã dừng, bảo quản .env riêng cùng dữ liệu. Oscar/Shuup/Wowy lưu SQLite/media trong ZIP; Pretix lưu database.dump và data.tar.gz. PHP/.NET chưa có lệnh backup/restore; dùng công cụ native theo [NATIVE_COMMERCE](NATIVE_COMMERCE.md). Vị trí, định dạng và trình tự phục hồi được mô tả tại [APPS](../APPS.md). Sau restore, kiểm tra trạng thái rồi start để tiếp tục vận hành.

Không cần reset/destroy khi chỉ muốn dừng rồi mở lại; dùng down/start. Các quy trình gọn, tách kiểm tra và khôi phục tại [WORKFLOWS](WORKFLOWS.md).

Phạm vi reset/destroy được liệt kê tại [COMMANDS](COMMANDS.md). Kiểm tra phạm vi dữ liệu trước khi xác nhận xóa.

## Quyền thư mục

Thư mục project cần có quyền ghi để Docker bind mount tạo dữ liệu. Trên Linux, file được container tạo có thể thuộc root; cấu hình quyền thư mục hoặc xử lý qua container. Trên Windows, kiểm tra quyền NTFS và quyền chia sẻ thư mục của Docker Desktop.

## Tồn kho customer Shuup và báo cáo đang mở

Sau khi cập nhật source, chạy `cmdc.cmd setup --app shuup --with-robot` để rebuild và seed phần sửa cấu hình tồn kho. Danh mục fuzcake dùng quản lý tồn ở nhà cung cấp và sản phẩm, với backorder_maximum bằng 0 và purchase_multiple bằng 1 cho sản phẩm bán nguyên chai. Phần sửa bội số có marker riêng để áp dụng được cả với cửa hàng đã sửa tồn kho trước đó; bội số dương tùy chỉnh được giữ nguyên. Lần áp dụng chính sách đầu tiên sửa các cờ native của danh mục đã khởi tạo; không nạp lại số lượng tồn hoặc xóa đơn. Các lần setup sau giữ chỉnh sửa chính sách của người vận hành. Nếu đã đổi tồn kho Rose Nocturne, đối chiếu lại điều kiện 25 chai trong model trước BVA; không reset database để làm test đạt.

Chạy riêng `cmdc.cmd robot --app shuup --customer --customer-case SH-CUST-Q06` rồi `cmdc.cmd report --app shuup`. Report vẫn hữu ích sau một lượt FAIL. Khi workbook mặc định bị Excel khóa, report lưu bản mới dưới tên riêng và in WARNING; kiểm tra đường dẫn thực tế. Nếu không lưu được cả bản thay thế, kiểm tra quyền ghi/dung lượng rồi chạy lại. Không xóa tệp khóa hoặc đóng Excel cưỡng bức. Chi tiết tại [báo cáo customer](SHUUP_CUSTOMER_REPORT.md).

[NAVIGATION](../NAVIGATION.md)
