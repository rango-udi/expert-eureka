[NAVIGATION](../NAVIGATION.md)

# ⚙️ Cấu hình môi trường

## Cấu hình riêng theo ứng dụng

Mỗi adapter tại `apps/<id>` sinh .env từ .env.template của chính nó và tạo secret riêng khi khởi tạo. Cấu hình đã tồn tại được giữ; nhóm PHP/.NET từ chối secret thiếu/yếu thay vì đổi credential của database cũ. Vị trí, biến tài khoản, ngân sách container và tùy chọn được ghi tại [APPS](../APPS.md). Setup đã hoàn thiện cấu hình; env init --app <id> là lựa chọn tạo/kiểm tra cấu hình riêng trước setup hoặc sau khi thay template. Env có thể build app/helper và không phải thao tác đọc file offline. Giá trị đã có được giữ; sửa .env không tự đổi mật khẩu đã lưu trong database. Phạm vi từng lệnh tại [COMMANDS](COMMANDS.md).

Các adapter có database/media/report riêng. Chi tiết biến người dùng và biến điều phối tại [ENVIRONMENT_VARIABLES](ENVIRONMENT_VARIABLES.md). Bảo vệ secret bằng quyền thư mục, giữ .env ngoài repository và kiểm tra log trước khi chia sẻ.

## Dữ liệu dùng chung và build context

Giữ fuzcake-data ở project root theo [SHARED_DATA](SHARED_DATA.md). Adapter Django nhận thư mục này qua named build context; nhóm PHP/.NET đọc nguồn khi khởi tạo trong container; runtime sử dụng mount chỉ đọc /fuzcake-data. Docker BuildKit và Compose v2 phải hỗ trợ additional_contexts. Dữ liệu đã nhập, .env và secret vẫn thuộc app riêng. Wowy dùng PYTHONPATH để nạp native modules từ /opt/wowy và package dữ liệu từ /fuzcake-data.

## Chính sách RAM engine dùng chung

[config/host-memory.env](../../config/host-memory.env) chứa HOST_MEMORY_TARGET_MIB và HOST_MEMORY_TOLERANCE_MIB. Cận trên là tổng hai giá trị. Biến cùng tên trong terminal ưu tiên hơn file; HOST_MEMORY_MAX_MIB cũ là bí danh của mốc khi tên mới chưa đặt.

Mốc nhận 1..1048576 MiB; dung sai nhận 0..1048576 MiB. RAM dưới mốc được cảnh báo và cho tiếp tục; vượt cận trên bị chặn trước chuẩn bị image. Chọn theo workload của adapter trong danh mục và xem [MEMORY](MEMORY.md).

## Giao diện terminal

| Biến host | Ý nghĩa |
| --- | --- |
| CMDC_UI | rich mặc định; auto hoặc plain để điều chỉnh hiển thị |
| NO_COLOR | Chọn văn bản không màu |
| BUILDKIT_TTY_LOG_LINES | Số dòng chi tiết BuildKit; mặc định 6 |

Mặc định rich dùng màu khi terminal tương tác; CI, pipe và file log dùng văn bản. CMDC_UI=rich yêu cầu chế độ màu khi terminal hỗ trợ. Trên Windows, launcher bật xử lý VT cho console trước khi gọi Docker; nếu không có console phù hợp hoặc đầu ra bị chuyển hướng thì dùng plain để tránh in lặp các khung tiến độ. Tác vụ được launcher thu log dùng output plain trong tiến trình con; spinner và thời gian chờ do launcher hiển thị. Build/pull trực tiếp giữ tiến độ native khi console phù hợp. Compose 2.36 trở lên hỗ trợ COMPOSE_PROGRESS. Hợp đồng xử lý con trỏ/màu của Windows tại [SetConsoleMode](https://learn.microsoft.com/en-us/windows/console/setconsolemode).

Trong bước chờ, spinner dùng các ký tự | / - và dấu gạch chéo ngược; thời gian chạy cập nhật ở mép phải cùng dòng. Nhãn được rút gọn theo chiều rộng terminal để giữ bộ đếm dễ đọc. Các bước build/pull dùng tiến độ Docker. Validate, generate và Robot của các adapter Django giữ log trực tiếp cùng hàng spinner/bộ đếm ở mép phải. Tiến trình quản trị cần nhập liệu tiếp tục gắn trực tiếp với console. Output của bước chờ và tác vụ kiểm thử được lưu vào task log dưới .runtime của adapter để xem lại khi lỗi. Dùng diagnostics --app để đọc log backend của installer/migrate ngay cả khi Docker đã dừng; log đầy đủ giữ riêng trên máy.

[NAVIGATION](../NAVIGATION.md)
