[NAVIGATION](../NAVIGATION.md)

# Dữ liệu YAML và ngôn ngữ trình bày

| Nội dung | Ngôn ngữ |
| --- | --- |
| Tài liệu Markdown, kể cả bảng ca sinh ra từ model | Tiếng Việt |
| Tên, mô tả, bước thực hiện, phân tích và hướng dẫn trong Excel | Tiếng Việt |
| Tên và mô tả Robot, console, CSV và JSON xuất báo cáo | Tiếng Anh |
| Tên người, tài khoản, email, địa chỉ và mật khẩu kiểm thử | Giá trị tiếng Anh cụ thể trong mọi bản trình bày |

## Nguồn dữ liệu

| Tệp | Vai trò |
| --- | --- |
| apps/shuup/tests/data/CUSTOMER_DESIGN.yaml | Giá trị đầu vào cụ thể, miền số lượng và quy tắc customer |
| apps/shuup/tests/data/CUSTOMER_CASE_TEXT.json | Tên và mô tả tình huống tiếng Anh cho thực thi |
| apps/shuup/tests/data/CUSTOMER_EXCEL_TEXT.json | Bản tiếng Việt dùng cho Excel và Markdown |
| apps/shuup/tests/data/WALLET_DESIGN.yaml | Model ví riêng cùng liên kết tới giao diện |
| fuzcake-data/records | Sản phẩm, tồn kho khởi tạo, giá, địa chỉ và phí đối tác dùng chung |

Các bản trình bày dùng chung ID và bộ giá trị đầu vào đã được cụ thể hóa. Bản dịch không thay đổi dữ liệu mà Robot nhập. Nội dung tiếng Việt không được sao chép vào tên test hoặc mô tả thực thi Robot.

## Quy trình

1. Sửa giá trị cụ thể trong test_data hoặc negative_cases. Đặt số nhập trên UI và chuỗi rỗng trong dấu nháy.
2. Chuẩn bị tài khoản fixture đã thay đổi bằng `cmdc.cmd manage --app shuup seed_customer_tests`; lệnh giữ nguyên quyền truy cập đã có và báo xung đột.
3. Khi chạy lại đăng ký thành công, chọn username và email cụ thể chưa được sử dụng trước khi sinh bản xem trước.
4. Chạy `cmdc.cmd generate --app shuup --customer`; xem Markdown hoặc Excel tiếng Việt, CSV tiếng Anh.
5. Chạy Robot rồi xuất lại báo cáo để nhận bằng chứng thực thi. Sinh kế hoạch không phải chạy kiểm thử.

Trong reports/customer, test_cases.md mô tả 71 ca bằng tiếng Việt; test_cases.csv và execution_cases.csv lần lượt mô tả 71 ca nghiệp vụ và 52 lượt thực thi bằng tiếng Anh. robot_transport.csv là dữ liệu truyền nội bộ cho DataDriver. model.json, coverage.json và report_data.json giữ nội dung thực thi tiếng Anh. customer_test_cases.xlsx là bản Excel tiếng Việt.

Cột dữ liệu đầu vào phải chứa giá trị dùng trực tiếp, kể cả mật khẩu kiểm thử. Không điền mã nguồn, biểu thức nội suy hoặc payload truyền nội bộ vào ô dành cho người đọc. Đường dẫn ảnh được gắn từ manifest của lần chạy đã chọn sau khi xác minh tệp thật; quá trình này không sửa giá trị YAML.

Model đóng băng dùng dấu vân tay ngữ nghĩa cho model, tham chiếu và payload để phát hiện thay đổi. Giá trị không bị thay ngầm khi thực thi. Oracle giao diện vẫn cần quy tắc nghiệp vụ đã duyệt; không đưa ví dụ tuổi/mật khẩu chung hoặc tổ hợp nhiều lỗi tùy ý vào cửa hàng.

Xem [thiết kế customer](SHUUP_CUSTOMER_TEST_DESIGN.md) và [báo cáo Excel](SHUUP_CUSTOMER_REPORT.md).

[NAVIGATION](../NAVIGATION.md)
