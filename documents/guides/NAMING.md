[NAVIGATION](../NAVIGATION.md)

# 🏷️ Quy ước đặt tên

## Tên dự án và tài nguyên

| Phạm vi | Quy ước |
| --- | --- |
| Tên hiển thị | Robot Web Tests |
| Thư mục/gói nguồn | robot-web-tests |
| App ID | Chữ thường; khai báo ở config/apps.list |
| Compose project | `robot-web-<id>` |
| Image tự build | `robot-web-<id>-app` hoặc `robot-web-<id>-browser` |
| Nhãn quản lý | org.robot-web.app, org.robot-web.workspace, org.robot-web.owner |
| Volume điều phối | robot-web-operation-lock |
| Volume dữ liệu | Tên Compose project cùng tên volume mô tả chức năng |

Tên cần mô tả vai trò thực tế. Tên ứng dụng và dữ liệu nghiệp vụ dùng đúng thuật ngữ của repository mục tiêu; tên chung chỉ dùng cho cơ chế dùng chung.

## File và mã nguồn

Tài liệu tham chiếu dùng UPPER_SNAKE_CASE.md. Nhật ký có phiên bản/ngày và tên tiếng Anh mô tả thay đổi. Script dùng snake_case; adapter của mỗi app có tên adapter.sh và adapter.ps1 để dễ tìm.

Trong Python, module và biến dùng snake_case, class dùng PascalCase, hằng số dùng UPPER_SNAKE_CASE. Package Django dùng tên nghiệp vụ: storefront mô tả cửa hàng của Oscar.

Biến môi trường dùng UPPER_SNAKE_CASE. Tên trong .env.template phải có chú thích ngay trước giá trị: mục đích, đơn vị/miền giá trị, mặc định và tác động khi để trống nếu áp dụng. Biến điều phối nội bộ được mô tả trong [ENVIRONMENT_VARIABLES](ENVIRONMENT_VARIABLES.md).

Giữ nguyên tên API tiêu chuẩn, image/repository upstream và giấy phép bên thứ ba. Bằng chứng gốc được giữ riêng theo hash khi đổi tên cây source; không sửa log thô để trình bày như một kết quả thực thi mới.

[NAVIGATION](../NAVIGATION.md)
