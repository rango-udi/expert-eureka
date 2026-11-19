[NAVIGATION](../NAVIGATION.md)

# Báo cáo Excel kiểm thử customer

Workbook giữ 71 tình huống nghiệp vụ tiếng Việt và 15 cột dành cho người kiểm thử. Thông tin tài khoản, mật khẩu và địa chỉ là dữ liệu tiếng Anh cụ thể. Các ID nghiệp vụ liên kết với 52 lượt thực thi Robot, dùng chung giá trị đầu vào và hành vi mong đợi.

```bat
cmdc.cmd report --app shuup
cmdc.cmd report --app shuup --media
cmdc.cmd report --app shuup --media --results reports/output.xml
```

Đích mặc định là apps/shuup/reports/customer/customer_test_cases.xlsx. Cờ --media tạo lại và nhúng hình phân tích thiết kế. Trước khi xuất lại, lưu riêng workbook đã nhập kết quả thủ công nếu muốn giữ các chỉnh sửa đó.

| Sheet | Nội dung |
| --- | --- |
| Ca kiểm thử | Tên, mô tả, các bước tiếng Việt và dữ liệu đầu vào cụ thể |
| BVA | Bảy điểm thêm hàng, bảy điểm cập nhật giỏ và bảy điểm độ dài tiêu đề địa chỉ |
| EP | Phân vùng customer gốc và bổ sung giỏ, sổ địa chỉ, mật khẩu; đại diện cụ thể và TC liên quan |
| Bảng quyết định | Trạng thái có thể đạt của coupon, địa chỉ, vận chuyển và điều khoản |
| Hướng dẫn | Chuẩn bị fixture, yêu cầu đăng ký lại và xử lý bằng chứng |
| Truy vết | Ca nghiệp vụ, nghĩa vụ thiết kế và bằng chứng thực thi liên quan |

## Khi Excel đang mở

Robot đọc YAML và dữ liệu đã đóng băng, không đọc hoặc sửa workbook đang mở. Mở Excel không ngăn việc chạy test. Lệnh report tạo workbook hoàn chỉnh trong tệp tạm cùng thư mục rồi mới thay đích mặc định; bản cũ được giữ nếu xuất lỗi.

Nếu Excel hoặc hệ thống tệp khóa đích mặc định, report lưu kết quả thành customer_test_cases-<UTC>-<mã riêng>.xlsx cùng thư mục, in WARNING và đường dẫn thực tế. Lệnh thành công khi bản thay thế đã được lưu. Đóng bản mặc định rồi chạy lại report nếu muốn cập nhật tên quen thuộc. Tệp chủ sở hữu ~$ chỉ tạo cảnh báo, không được xem là bằng chứng chắc chắn workbook bị khóa.

Nếu thư mục không cho ghi, hết dung lượng hoặc cả tên thay thế cũng không lưu được, lệnh báo ERROR và trả mã lỗi. Thông báo hướng dẫn kiểm tra quyền/dung lượng và chỉ rõ tệp hoàn chỉnh còn giữ lại nếu có. Không tự đóng Excel, xóa khóa hoặc ghi đè tệp đang mở bằng thao tác cưỡng bức.

## Bằng chứng giao diện tự động

Lần chạy customer mới lưu ảnh PNG thật cho ca độc lập đạt/lỗi và từng mốc nghiệp vụ đã tới trong E01. Ảnh nằm tại apps/shuup/reports/customer/evidence/<run-id>/screenshots/. Manifest ánh xạ ảnh với TC, lượt Robot, mốc và checksum. Run ID được ghi trong output.xml; dữ liệu kiểm thử không bị thay đổi.

Lệnh report tự nhập reports/output.xml khi tệp tồn tại. Cờ --results chọn nguồn khác với đường dẫn tính từ app. Báo cáo đối chiếu đúng metadata lần chạy, model, trạng thái test, vị trí tệp, định dạng PNG và checksum rồi điền cột Bằng chứng trong sheet Ca kiểm thử. Đường dẫn hiển thị tính từ app/; nhiều ảnh nằm trên các dòng riêng. Đường dẫn đầu tiên có liên kết tương đối để mở tệp.

Ảnh chỉ gắn với TC được chỉ định tại mốc đó. E01 lỗi sớm không làm các ca chưa tới nhận ảnh trang cuối. Ảnh cung cấp ngữ cảnh, không tự kết luận PASS hoặc lỗi nghiệp vụ. Hộp thoại native có thể được thể hiện bằng trạng thái trang sau khi đóng; log Robot giữ nội dung đã được xác nhận.

Thư mục ảnh nằm ngoài thư mục mặc định có thể bị Browser dọn khi khởi động suite. Chạy mới và sinh lại kế hoạch giữ các thư mục bằng chứng trước. Giữ cấu trúc thư mục ảnh và manifest cùng workbook; di chuyển riêng XLSX không di chuyển được các ảnh mà nó dẫn tới.

XML cũ thiếu metadata chụp ảnh không thể cung cấp PNG đã mất. Nếu có nguồn thật, báo cáo dùng đường dẫn kết quả đã rút gọn làm bằng chứng log và cảnh báo chưa có ảnh. Không chèn ảnh giả hoặc ảnh cũ không liên quan.

Excel và Markdown dùng tiếng Việt. Tên Robot, tên tệp, console, CSV và JSON xuất báo cáo dùng tiếng Anh. Kết quả nhập vẫn là bằng chứng tham chiếu, không tự điền kết quả nghiệp vụ mới.

Xem [quy ước dữ liệu và ngôn ngữ](YAML_TEST_DATA.md) và [thiết kế customer](SHUUP_CUSTOMER_TEST_DESIGN.md).

[NAVIGATION](../NAVIGATION.md)
