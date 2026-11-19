[NAVIGATION](../NAVIGATION.md)

# 🛒 Hành trình kiểm thử

Tra các vai trò, dữ liệu mẫu, đường vào ứng dụng và phạm vi suite tại [danh mục ứng dụng](../APPS.md). Mỗi adapter mô tả hành trình theo đúng nghiệp vụ và giao diện của repository mục tiêu.

Bắt đầu bằng địa chỉ do `urls --app <id>` trả về. Sau điểm vào, sử dụng link, nút và form để chuyển trang. Mỗi ca có phiên browser riêng và xác nhận kết quả quan sát được trên giao diện.

Hành trình customer Shuup từ đăng ký tới đơn hàng có [bảng thiết kế](SHUUP_CUSTOMER_TEST_DESIGN.md) và [mã được giải thích](SHUUP_CUSTOMER_TEST_CODE.md), chạy bằng robot --customer. Đây là suite riêng với các probe EP/BVA và E2E; smoke chỉ phục vụ kiểm tra nhanh.

Để viết ca mới hoặc chọn suite/test theo hành trình, xem [WORKFLOWS](WORKFLOWS.md) và [TESTING](TESTING.md). Không cần gọi generate cho suite .robot đã có; dữ liệu sinh chỉ được thực thi khi đã nối vào keyword/oracle thích hợp.

Phân biệt kết quả sinh dữ liệu, HTTP integration, Robot dryrun và browser thực tế. Kết quả theo phiên bản nằm tại nhật ký (lưu riêng trong bản bàn giao đầy đủ).

[NAVIGATION](../NAVIGATION.md)
