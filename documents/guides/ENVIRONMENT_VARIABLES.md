[NAVIGATION](../NAVIGATION.md)

# 📋 Tham chiếu biến môi trường

## Biến người vận hành sử dụng

| Biến | Nơi cấu hình | Ý nghĩa |
| --- | --- | --- |
| HOST_FREE_MEMORY_MIN_MIB | config/pretix-safety.env hoặc config/commerce-safety.env | Ngưỡng dự phòng host trước tác vụ của nhóm tương ứng, số nguyên MiB; không phải RAM tối thiểu đã đo |
| HOST_MEMORY_TARGET_MIB | config/host-memory.env hoặc terminal | Mốc RAM engine, số nguyên MiB |
| HOST_MEMORY_TOLERANCE_MIB | config/host-memory.env hoặc terminal | Phần tăng thêm được chấp nhận, số nguyên MiB |
| HOST_MEMORY_MAX_MIB | Terminal khi chuyển cấu hình cũ | Bí danh mốc nếu tên TARGET chưa được đặt |
| COUPON_CODE | apps/shuup/.env | Mã coupon native khởi tạo: FUZCAKE10, giảm 10% tiền hàng; 1–12 ký tự ASCII chữ/số/_/-, rỗng bỏ qua tạo mới; không sửa campaign đã có |
| CMDC_UI | Terminal | rich mặc định; auto hoặc plain cho kiểu hiển thị khác |
| NO_COLOR | Terminal | Chọn văn bản không màu |
| BUILDKIT_TTY_LOG_LINES | Terminal | Số dòng log chi tiết của bước build; mặc định 6 |

Biến tài khoản, database và giới hạn container thuộc .env của mỗi app. Đọc chú thích ngay trước từng khóa trong .env.template được liên kết qua [APPS](../APPS.md). Seed dùng mật khẩu khi tạo tài khoản; đổi mật khẩu của tài khoản đã có qua chức năng quản trị phù hợp.

Nhóm PHP/.NET dùng HTTP_PORT ổn định, APP_MEMORY_LIMIT, DB_MEMORY_LIMIT, ROBOT_MEMORY_LIMIT, DB_PASSWORD/DB_ROOT_PASSWORD và ADMIN/CUSTOMER email/password riêng. Nguồn và quy tắc giữ giá trị nằm trong [NATIVE_COMMERCE](NATIVE_COMMERCE.md); không in .env bằng config.

## Biến do dispatcher thiết lập

| Biến | Trách nhiệm |
| --- | --- |
| CMDC_GUARDED_APP | Xác nhận adapter được gọi sau bước chọn app; không phải cơ chế xác thực người dùng |
| CMDC_WORKSPACE | Đường dẫn repository để gắn ownership vào tài nguyên |
| CMDC_SELECTED_RUNNING | Kết quả kiểm tra trạng thái Docker của tác vụ hiện tại |
| CMDC_HOST_PLATFORM | Chọn cách xử lý quyền file trên host Windows/POSIX |
| COMPOSE_PARALLEL_LIMIT | Giới hạn thao tác Compose đồng thời; mặc định 1 |
| PYTHONPATH | Wowy: /app:/opt/wowy:/fuzcake-data; phân tách adapter, nguồn native và package dữ liệu chung trong container |
| COMPOSE_ANSI / COMPOSE_PROGRESS | Chế độ màu và tiến độ Compose do terminal helper chọn |
| BUILDKIT_PROGRESS | Chế độ tiến độ BuildKit tương ứng với terminal |

Các biến này do code điều phối quản lý. Người dùng chạy root cmdc để giữ đúng trình tự kiểm tra thay vì tự thiết lập token gọi adapter.

## Biến runtime của bộ customer Shuup

| Biến nội bộ | Nguồn và vòng đời |
| --- | --- |
| ROBOT_COUPON_CODE | commands.py đọc COUPON_CODE từ .env khi gọi Robot; không phải secret thanh toán |
| ROBOT_CUSTOMER_EMAIL / ROBOT_CUSTOMER_PASSWORD | Credential fixture cho probe login/quantity; password nhập bằng Fill Secret |
| ROBOT_NEW_PASSWORD / ROBOT_NEW_PASSWORD_CONFIRM | Sinh trong process Browser cho mỗi danh tính đăng ký; chỉ giữ trong environment tiến trình, không ghi model/CSV |
| ROBOT_INVALID_PASSWORD | Giá trị rỗng/sai cho ca login âm; không thay mật khẩu fixture |
| BASE_URL | URL nội bộ của Shuup trong Docker; activation mail phải trùng origin này |

Không cần thêm các biến này vào .env.template hoặc tự khai báo để gọi helper. Dùng CMDC để cấp cấu hình. Các email mới dùng miền hư cấu fuzcake.test; thư activation nằm trong backend file local.

## Biến trong container

CMDC_CONTAINER xác định môi trường thực thi công cụ Oscar. DJANGO_SETTINGS_MODULE trỏ tới storefront.settings trong app đó. PLAYWRIGHT_BROWSERS_PATH chỉ nơi browser được cài trong image. TMPDIR/TMP/TEMP được cấu hình về thư mục tạm của app. Credential cho Robot được đọc từ cấu hình app và nhập bằng keyword bảo vệ secret.

PIP_NO_CACHE_DIR, PIP_PROGRESS_BAR và PYTHONDONTWRITEBYTECODE phục vụ image gọn và log dễ theo dõi. Những thiết lập được khai báo tại Dockerfile kèm chú thích; không cần cài runtime của dự án trên host.

[NAVIGATION](../NAVIGATION.md)
