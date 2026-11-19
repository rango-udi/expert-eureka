[NAVIGATION](../NAVIGATION.md)

# 🛠️ Tìm script theo công việc

| Công việc | Điểm vào |
| --- | --- |
| Đọc log backend offline | scripts/diagnostics.sh hoặc diagnostics.ps1; che secret trong .env của đúng app |
| Tra lệnh tại terminal | config/COMMAND_HELP.txt dùng chung cho hai root launcher; hợp đồng chi tiết trong COMMANDS |
| Chọn và vận hành app | cmdc ở root; dispatcher tại scripts/cmdc.sh hoặc cmdc.ps1 |
| Kiểm tra Docker và RAM | scripts/system.*, scripts/memory_policy.* |
| Xác nhận và dự phòng host Pretix | scripts/pretix_safety.* |
| Chuẩn bị distribution Shuup | apps/shuup/scripts/prepare_upstream.py xác minh hash và sửa metadata wheel khi build |
| Xuất Excel và hình phân tích customer | apps/shuup/scripts/customer_report.py, customer_report_data.py, customer_report_media.py và customer_report_output.py; hướng dẫn tại [SHUUP_CUSTOMER_REPORT](SHUUP_CUSTOMER_REPORT.md) |
| Hiển thị terminal | scripts/terminal.*: màu, spinner và bộ đếm thời gian canh phải |
| Mở tài liệu WSL | scripts/open_help.ps1 |
| Cửa hàng PHP/.NET | scripts/commerce/adapter.*, commands.py và resource_safety.*; installer PHP nằm trong app |
| Tác vụ riêng của app | `apps/<id>/scripts/adapter.*` |
| Cấu hình app | .env.template từng app; configuration.py cho adapter Django, scripts/commerce/commands.py cho nhóm PHP/.NET |
| Migrate/seed, quản trị và Robot của Oscar | apps/oscar/scripts/commands.py |
| Dữ liệu và theme fuzcake | fuzcake-data/fuzcake_data và các seed của app; storefront/theme.py và views.py giữ nghiệp vụ riêng |
| Tích hợp Wowy | apps/wowy/scripts/prepare_upstream.py, storefront/commerce.py, views.py và middleware.py |
| Web server Oscar | apps/oscar/scripts/web_server.py |
| Seed/health/scheduler pretix | apps/pretix/scripts/seed_demo.py, healthcheck.py, run_periodic_tasks.sh |
| Kiểm tra toàn bộ source/tài liệu | scripts/check_code.py, check_docs.py |

Cách chọn lệnh, tên đồng nghĩa và kết quả từng lệnh tại [COMMANDS](COMMANDS.md); trình tự theo mục tiêu và lý do tách bước tại [WORKFLOWS](WORKFLOWS.md). Trang này chỉ dẫn vị trí mã triển khai, không phải chuỗi lệnh bắt buộc.

App adapter đặt working directory về chính app trước khi gọi Docker. Script hệ thống chỉ dùng config ở root và không đọc secret của app khác. Dùng CLI root cho vận hành; token lựa chọn được dispatcher truyền cho adapter sau khi kiểm tra an toàn.

Mỗi hàm Python có docstring nêu chức năng và ranh giới. Comment giải thích lý do hoặc quy tắc quan trọng; dùng tên có nghĩa thay cho comment diễn giải lại từng dòng lệnh. Tham khảo [DEVELOPMENT](DEVELOPMENT.md) khi sửa hoặc bổ sung adapter.

## Theo dõi một lượt customer cụ thể

Xem [đường đi từ lệnh CMD](SHUUP_CUSTOMER_EXECUTION.md), [từng dòng Robot và hàm Python](SHUUP_CUSTOMER_ROBOT_WALKTHROUGH.md), cùng [luồng dữ liệu và ảnh](SHUUP_CUSTOMER_DATA_FLOW.md). Ví dụ xuyên suốt là chạy toàn bộ customer và chọn riêng SH-CUST-B09.

[NAVIGATION](../NAVIGATION.md)
