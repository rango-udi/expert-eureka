[NAVIGATION](../NAVIGATION.md)

# 🗺️ Cấu trúc mã nguồn

Root chỉ chứa điểm vào, cấu hình điều phối và các thành phần dùng chung. Mã ứng dụng nằm hoàn toàn trong `apps/<id>`. Tra nghiệp vụ và lựa chọn tại [APPS](../APPS.md).

| Thư mục / file | Nội dung |
| --- | --- |
| cmdc / cmdc.cmd | Lệnh công khai cho POSIX / Windows |
| scripts/cmdc.sh / cmdc.ps1 | Dispatcher, khóa thao tác và kiểm tra ownership |
| scripts/diagnostics.sh / diagnostics.ps1 | Đọc log backend cục bộ, che secret cấu hình và giới hạn số dòng |
| scripts/system.sh / system.ps1 | Doctor và trợ giúp hệ thống; độc lập với mọi app |
| scripts/memory_policy.sh / memory_policy.ps1 | Kiểm tra RAM engine theo mốc và dung sai |
| scripts/pretix_safety.sh / pretix_safety.ps1 | Cảnh báo, xác nhận tài nguyên và dự phòng host trước Pretix |
| scripts/commerce | Điều phối PHP/.NET, bootstrap .env, kiểm tra nguồn và import nopCommerce |
| scripts/terminal.sh / terminal.ps1 | Màu, spinner, tiến độ và mã thoát |
| scripts/check_docs.py / check_code.py | Kiểm tra tài liệu và quy ước source chung |
| config | Registry ứng dụng, chính sách RAM và mẫu giới hạn truyền image của engine |
| apps/oscar | Docker, cấu hình, storefront, script, test và output của Oscar |
| apps/shuup | Docker, storefront, cấu hình, script, test và output Shuup |
| apps/wowy | Adapter Wowy, lớp settings/checkout/quyền, overrides và kiểm thử |
| test-design | Thư viện độc lập sinh single-fault, xuất DataDriver và runner UI khai báo; tích hợp adapter Shuup |
| fuzcake-data | Bản ghi, tài nguyên nhận diện và package đọc dùng chung, mount chỉ đọc |
| apps/nopcommerce, apps/prestashop, apps/woocommerce | Docker native, installer/seed, cấu hình riêng và smoke UI; [NATIVE_COMMERCE](NATIVE_COMMERCE.md) |
| apps/pretix | Docker, cấu hình, script, test và output của pretix |
| tests/windows | Kiểm tra launcher host, không chứa kiểm thử nghiệp vụ app |
| documents/updates/archive | Snapshot nguồn và nhật ký lưu trữ, có kiểm tra hash |
| documents | Danh mục app, hướng dẫn, trợ giúp, giấy phép và nhật ký |
| evidence | Bằng chứng kiểm tra bản nguồn theo phiên bản |
| .runtime | Khóa và log điều phối chung; không chứa database ứng dụng |

## Quy ước trong một app

| Thành phần | Trách nhiệm |
| --- | --- |
| compose.yaml / compose.lock.yaml | Dịch vụ Docker và digest khi được cung cấp |
| Dockerfile | Image tùy biến nếu adapter có bước build |
| .env.template | Mẫu cấu hình có chú thích; .env là bản riêng được sinh từ mẫu |
| config/source-lock.json | Repository, tag/commit và nguồn image |
| scripts/adapter.sh / adapter.ps1 | Cầu nối CLI chung với thao tác riêng của ứng dụng |
| scripts/configuration.py | Đọc, kiểm tra và ghi cấu hình riêng trong container |
| tests | Unit, integration, Robot và mô hình đầu vào của app |
| reports / backups / .runtime | Output riêng; không được nhập chung giữa các app |

Oscar dùng package Django `storefront` trong apps/oscar. Công cụ quản trị app có quyền đọc cây repository qua mount riêng để chạy kiểm tra chung; container web/browser chỉ nhận cấu hình và dữ liệu cần thiết của app.

Nhận diện Docker dùng prefix `robot-web-<id>`, nhãn `org.robot-web.*` và workspace sở hữu. Tên file, biến công khai và đường dẫn chuẩn được định nghĩa tại [NAMING](NAMING.md).

## Dữ liệu chung và ánh xạ ứng dụng

fuzcake-data là nguồn theo [SHARED_DATA](SHARED_DATA.md). Package fuzcake_data đọc/kiểm tra dữ liệu; mỗi app có seed ánh xạ vào model native. Runtime của các app dùng một mount chỉ đọc /fuzcake-data, tách khỏi secret và dữ liệu tương tác.

Shuup giữ theme.py, templates/fuzcake, business_data.py và WalletMovement trong storefront của app. storefront.settings chứa cấu hình dự án; storefront.default_settings chỉ chứa mặc định do AppConfig cục bộ khai báo. Oscar ánh xạ SKU sang UPC/StockRecord. Wowy ánh xạ SKU sang Product/ProductImage, giữ receipt và snapshot để bảo vệ checkout và tồn kho; native source lấy theo commit trong build, nằm tại /opt/wowy trong image. Pretix đọc profile sự kiện, giữ ID của organizer/event và quota đã dùng. Tài nguyên ảnh/brand/font/CSS và design-tokens.css nằm ở nguồn chung, tránh bản sao riêng trong app. Theme Shuup ghép macro/hook native vào một header/footer có nhận diện, cùng placeholder và view gốc; context giới thiệu và xử lý static/media tách khỏi response nghiệp vụ.

[NAVIGATION](../NAVIGATION.md)
