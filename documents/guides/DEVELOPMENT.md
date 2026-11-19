[NAVIGATION](../NAVIGATION.md)

# 🧰 Đọc và phát triển mã nguồn

## Bắt đầu từ đâu

1. Đọc [APPS](../APPS.md) để xác định app và adapter.
2. Xem [ARCHITECTURE](ARCHITECTURE.md) để phân biệt thành phần chung với mã ứng dụng.
3. Theo lệnh từ cmdc → dispatcher → `apps/<id>/scripts/adapter.*` → Docker → công cụ hoặc server của app.
4. Xem .env.template, source-lock.json và [SHARED_DATA](SHARED_DATA.md) trước khi thay dependency hoặc dữ liệu khởi tạo.

## Đặt thay đổi đúng phạm vi

Sửa nghiệp vụ, Django settings, ánh xạ seed và Robot trong app tương ứng. Dữ liệu tham chiếu, ảnh và nhận diện dùng chung được sửa một lần trong fuzcake-data; bổ sung profile và kiểm tra adapter tiêu thụ thay vì sao chép dữ liệu vào app. Sửa lựa chọn, khóa, ownership, RAM engine hoặc giao diện terminal trong scripts dùng chung. Tránh để công cụ chung phụ thuộc vào một ứng dụng cụ thể.

Khi thêm app, đồng bộ registry, hồ sơ trong documents/apps, danh mục trung tâm và allowlist dispatcher. Adapter phải dùng namespace Docker riêng, kiểm tra dữ liệu sở hữu và hỗ trợ trình tự setup/start/down của CLI chung.

## Phân biệt cấu hình dự án và mặc định app Shuup

Shuup AppConfig mặc định thu thập tên viết hoa từ settings.py bên trong package app. Với storefront, settings.py là cấu hình toàn dự án nên AppConfig phải chỉ rõ default_settings_module trỏ tới .default_settings. Không nhập cấu hình dự án hoặc settings upstream vào module mặc định này; các giá trị ghi đè vẫn thuộc storefront.settings. Giữ AppConfig của Shuup để cơ chế provides tiếp tục đăng ký theme.

Khi sửa ranh giới này, kiểm tra bootstrap registry bằng tiến trình Django mới trong container và đối chiếu chủ sở hữu của setting upstream. Kiểm tra migrate/seed sau đó theo quy trình của [SHUUP](../apps/SHUUP.md).

## Kiểm tra trước đóng gói

Source checker chỉ đọc cây source duy trì; bỏ qua runtime, virtualenv, dependency, reports, backups và đường dẫn liên kết. Không áp dụng quy ước tên/ngôn ngữ của workspace lên static đã collect hay vendor upstream.

Dùng python scripts/package_source.py để tạo ZIP. Script kiểm tra các thành phần nguồn bắt buộc và hash bản lưu trữ trước/sau đóng gói; check_preservation.py có thể chạy riêng. Snapshot lịch sử được kiểm bằng hash, không sửa để đáp ứng quy ước tên/link của tài liệu hiện hành.

Chạy kiểm tra nội bộ của app trong Docker bằng validate --app <id>, theo phạm vi tại [COMMANDS](COMMANDS.md). Tools Django đọc source từ mount host nhưng dependency vẫn thuộc image; web dùng source COPY nên cần setup khi thay code triển khai. Quy trình viết test, model và chọn chạy gọn/tách bước tại [WORKFLOWS](WORKFLOWS.md). Kiểm tra dispatcher với lựa chọn thiếu/sai, khóa đang có, ứng dụng khác còn chạy, container/volume khác workspace và lỗi giữa chừng. Kiểm tra terminal tương tác cùng chế độ plain.

Rà toàn bộ liên kết và chỉ dẫn thao tác sau khi đổi đường dẫn. File .env, backup credential, runtime và report riêng phải được loại khỏi image/source package. Kết quả theo môi trường thực thi nằm trong evidence; hạn chế xác minh được ghi ở nhật ký phiên bản.

## Phạm vi lưu trên Git

Git lưu source, cấu hình mẫu, fixture kiểm thử và asset cần chạy cửa hàng. Các thư mục lịch sử cập nhật, báo cáo phát hành, runtime, log, cache, dependency cài đặt và cấu hình môi trường riêng được giữ ngoài Git. Template môi trường và cấu hình chính sách dùng chung trong config vẫn được theo dõi.

Bản checkout sạch không cần các thư mục lịch sử hoặc hồ sơ nội bộ để kiểm tra source/tài liệu. Khi các thư mục bảo toàn có mặt trong bản bàn giao đầy đủ, bộ kiểm tra tiếp tục xác minh các tệp và checksum; bỏ qua Git không xóa dữ liệu đang có trên máy.

[NAVIGATION](../NAVIGATION.md)
