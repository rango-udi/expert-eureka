[NAVIGATION](../NAVIGATION.md)

# 🔄 Chuyển cấu trúc và dữ liệu

## Trước khi thay source

Dùng launcher của deployment cũ để down ứng dụng. Sao lưu .env, chính sách RAM, database/media và backups trong lúc các tiến trình ghi đã dừng. Triển khai source mới vào thư mục riêng để đối chiếu và phục hồi khi cần.

Các deployment hoặc khóa điều phối dùng định danh cũ bị từ chối tiếp quản. Hoàn tất việc dừng/phục hồi bằng đúng bộ source đã tạo chúng trước khi chuyển.

## Di chuyển dữ liệu Oscar

| Vị trí trong cấu trúc trước | Vị trí hiện hành |
| --- | --- |
| .env ở root | apps/oscar/.env |
| .runtime/data ở root | apps/oscar/.runtime/data |
| backups và reports ở root | apps/oscar/backups và apps/oscar/reports |

Launcher từ chối tiếp tục nếu phát hiện .env hoặc database Oscar còn ở root. Di chuyển các mục trong bảng sang vị trí tương ứng sau khi đã lưu bản sao. Chỉ mang theo dữ liệu, không chép khóa hoặc trạng thái tiến trình cũ. Sau khi đặt dữ liệu đúng nơi, chạy setup --app oscar, urls --app oscar rồi kiểm tra tài khoản và đơn hàng. Giữ secret cũ cùng database; việc đổi package Django không tự thay dữ liệu nghiệp vụ.

## Chuyển môi trường pretix

Cấu hình và output vẫn thuộc apps/pretix. Compose project và tên tài nguyên đã được chuẩn hóa, vì vậy volume của namespace trước không được tự gắn vào môi trường mới. Dùng backup database.dump/data.tar.gz từ phiên cũ, đặt vào thư mục backups của adapter mới.

Giữ lại .env trước khi setup. Các credential cũ có hậu tố ADMIN_EMAIL, ADMIN_PASSWORD, STAFF_EMAIL và STAFF_PASSWORD được ánh xạ sang khóa hiện hành nếu xác định được một giá trị duy nhất. Xung đột sẽ dừng; không tự tạo mật khẩu thay thế cho dữ liệu đã có. Một bản .env.credentials-backup riêng được tạo trước khi ghi cấu hình đổi tên.

Chuẩn bị môi trường/image tương thích trước khi restore backup đã kiểm tra. Restore thay database/media và giữ writers dừng; gọi start nếu chỉ muốn mở lại bản phục hồi. Chọn init --app pretix trước start khi cần áp migration và bổ sung fixture hiện hành vào dữ liệu vừa phục hồi; đây là thao tác cập nhật dữ liệu có chủ đích, không phải bước bắt buộc của mọi lần restore. Các tác vụ tạo tải cần --accept-pretix-risk hoặc xác nhận prompt từng lần. Các nhãn nghiệp vụ trong dữ liệu người dùng được giữ nguyên; thư mục source dùng tên chuẩn của dự án.

## Áp dụng profile tài nguyên Pretix

Giữ .env và named volume hiện có. Khi dùng source có profile swap/restart/scheduler, down app rồi chạy env init với --accept-pretix-risk để sinh lại cấu hình hiệu lực. Các giá trị đã có được giữ; khóa mới dùng mặc định trong template. Start lại sẽ tạo lại dịch vụ theo profile; dữ liệu database/media vẫn ở volume cũ.

Manual scheduler dừng cả scheduler còn lại của profile trước khi start toàn app. Nếu hành trình cần maintenance tự động, chọn PERIODIC_TASKS=scheduled rõ ràng. Tham khảo [PRETIX_RESOURCE_PRESSURE](../helps/PRETIX_RESOURCE_PRESSURE.md) trước khi chấp thuận tạo tải.

## Xác nhận sau chuyển đổi

Chạy doctor để xem chính sách engine, status/urls theo app và kiểm tra luồng người dùng trong [APPS](../APPS.md). Đối chiếu secret, dữ liệu và quyền truy cập trước khi xóa các bản sao chuyển đổi. Không sửa nhãn volume cũ để bỏ qua bước xác minh ownership.

Các snapshot và kết quả thô trước đó được tham chiếu qua hồ sơ nguồn (lưu riêng trong bản bàn giao đầy đủ), tách khỏi source hiện hành.

[NAVIGATION](../NAVIGATION.md)
