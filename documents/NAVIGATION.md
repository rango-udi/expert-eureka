[NAVIGATION](NAVIGATION.md)

# 🧭 Điều hướng Robot Web Tests

| Nhu cầu | Điểm đến và nội dung |
| --- | --- |
| [YAML test data](guides/YAML_TEST_DATA.md) | Mô hình YAML, giá trị đầu vào và truy vết đồng nhất |
| 🏠 Giới thiệu | [README](../README.md): mục tiêu, nền tảng và lệnh chính |
| 🧩 Ứng dụng | [APPS](APPS.md): danh mục trung tâm và hồ sơ từng ứng dụng |
| 🏬 PHP và .NET | [NATIVE_COMMERCE](guides/NATIVE_COMMERCE.md): installer, phạm vi lệnh, cổng và phục hồi |
| 🔒 Vòng đời | [APP_LIFECYCLE](guides/APP_LIFECYCLE.md): lựa chọn, khóa, ownership và phục hồi |
| 🚀 Bắt đầu | [QUICKSTART](../QUICKSTART.md): chuẩn bị Docker, tạo cửa hàng, chạy Robot và dừng |
| 🧭 Chọn quy trình | [WORKFLOWS](guides/WORKFLOWS.md): một lệnh hoặc từng bước, viết test, model và chọn ca |
| ⌨️ Lệnh và option | [COMMANDS](guides/COMMANDS.md): cú pháp, mặc định, dữ liệu bị tác động |
| 🛒 Hành trình | [JOURNEYS](guides/JOURNEYS.md): customer, seller, admin và cash on delivery |
| 🗺️ Cấu trúc | [ARCHITECTURE](guides/ARCHITECTURE.md): từng thư mục, thành phần và dữ liệu |
| 🏷️ Đặt tên | [NAMING](guides/NAMING.md): tên dự án, tài nguyên, file và code |
| 📋 Biến môi trường | [ENVIRONMENT_VARIABLES](guides/ENVIRONMENT_VARIABLES.md): biến công khai và nội bộ |
| 🧰 Phát triển | [DEVELOPMENT](guides/DEVELOPMENT.md): đọc luồng code, sửa đúng phạm vi và kiểm tra |
| 🛠️ Script | [SCRIPTS](guides/SCRIPTS.md): hàm, đầu vào, đầu ra và điều phối Docker |
| ⚙️ Cấu hình | [ENVIRONMENT](guides/ENVIRONMENT.md): biến, secret và port |
| 🆘 Trợ giúp WSL | [WSL_VM_MEMORY_LIMIT](helps/WSL_VM_MEMORY_LIMIT.md): trần RAM, thu hồi cache, áp dụng và hoàn tác |
| ⚠️ Tài nguyên Pretix | [PRETIX_RESOURCE_PRESSURE](helps/PRETIX_RESOURCE_PRESSURE.md): xác nhận, khởi động từng bước và phục hồi EOF/OOM |
| 🧠 RAM | [MEMORY](guides/MEMORY.md): ngân sách, tải image, cache WSL và số đo |
| Sinh test hộp đen | [AUTOMATED_TEST_DESIGN](guides/AUTOMATED_TEST_DESIGN.md): BVA, EP, rule, giảm ca và Robot DataDriver |
| 🛒 Customer Shuup | [SHUUP_CUSTOMER_TEST_DESIGN](guides/SHUUP_CUSTOMER_TEST_DESIGN.md): phân tích, giá trị, bảng ca và độ phủ; [SHUUP_CUSTOMER_TEST_CODE](guides/SHUUP_CUSTOMER_TEST_CODE.md): Robot/selector/Python |
| 🔎 Theo dõi lệnh customer | [SHUUP_CUSTOMER_EXECUTION](guides/SHUUP_CUSTOMER_EXECUTION.md): lệnh đầy đủ/một ca và thứ tự gọi; [SHUUP_CUSTOMER_ROBOT_WALKTHROUGH](guides/SHUUP_CUSTOMER_ROBOT_WALKTHROUGH.md): keyword, Python và B09; [SHUUP_CUSTOMER_DATA_FLOW](guides/SHUUP_CUSTOMER_DATA_FLOW.md): YAML, browser, ảnh và Excel |
| 🧩 Customer mở rộng | [CUSTOMER_EXTENSIONS](guides/CUSTOMER_EXTENSIONS.md): giỏ, sổ địa chỉ, mật khẩu và phục hồi qua UI |
| 📊 Excel customer | [SHUUP_CUSTOMER_REPORT](guides/SHUUP_CUSTOMER_REPORT.md): 15 cột, BVA/EP/decision, nhập kết quả và xuất ảnh |
| 🧪 Kiểm thử | [TESTING](guides/TESTING.md): CLI, HTTP, browser và sinh ca |
| 🔧 Vận hành | [OPERATIONS](guides/OPERATIONS.md): log, reset, sao lưu/phục hồi và xử lý lỗi |
| 🔄 Chuyển mục tiêu | [MIGRATION](guides/MIGRATION.md): cấu hình/dữ liệu Oscar riêng, tài nguyên hệ thống |
| 🗂️ Nguồn dữ liệu chung | [SHARED_DATA](guides/SHARED_DATA.md): fuzcake-data, profile adapter, build/mount và nâng cấp |
| 📝 Cập nhật | Điều hướng cập nhật (lưu riêng trong bản bàn giao đầy đủ): phiên bản và kết quả thực thi |
| 👤 Sở hữu | [CODEOWNER](../CODEOWNER.md) và [CODEOWNERS](../.github/CODEOWNERS) |
| 📄 Giấy phép | [LICENSE](../LICENSE), [THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES.md) |

Mã ứng dụng và kiểm thử riêng nằm trong `apps/<id>/`; `scripts/` và `config/` chứa bộ điều phối dùng chung. Tra cấu hình, dữ liệu và tài liệu của từng ứng dụng tại [APPS](APPS.md). Kết quả đóng gói được ghi tại `evidence/`; báo cáo và bản sao lưu vận hành nằm trong thư mục của ứng dụng.

[NAVIGATION](NAVIGATION.md)
