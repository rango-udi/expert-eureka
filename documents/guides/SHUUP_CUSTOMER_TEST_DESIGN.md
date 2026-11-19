[NAVIGATION](../NAVIGATION.md)

# Thiết kế kiểm thử customer

Bộ ca gồm 71 tình huống nghiệp vụ tiếng Việt trong Excel và Markdown. Tên, mô tả Robot, console, CSV và JSON xuất báo cáo dùng tiếng Anh. Tên người, tài khoản, mật khẩu và địa chỉ là giá trị tiếng Anh cụ thể trong mọi bản trình bày. ID ổn định nối các bản trình bày với cùng dữ liệu đầu vào.

| Nhóm thực thi | ID | Số lượng |
| --- | --- | --- |
| Kiểm tra đăng ký | SH-CUST-R01-R08 | 8 |
| Kiểm tra đăng nhập | SH-CUST-L01-L04 | 4 |
| Kiểm tra số lượng | SH-CUST-Q01-Q09 | 9 |
| Cập nhật/xóa giỏ và thêm lặp | SH-CUST-B01-B12 | 12 |
| Sổ địa chỉ và quyền sở hữu | SH-CUST-A01-A11 | 11 |
| Đổi mật khẩu và phiên đăng nhập | SH-CUST-P01-P07 | 7 |
| Hành trình customer đầy đủ | SH-CUST-E01 | 1 |

Tên ca mô tả tình huống đầu vào, ví dụ “Đăng ký với tên đăng nhập để trống” hoặc “Thêm 26 chai Rose Nocturne khi tồn kho là 25 chai”. Kết quả từ chối nằm ở cột Kết quả mong đợi. Tên và mô tả không phải lời khuyên hoặc câu mệnh lệnh phủ định.

## Tài khoản cụ thể

| Mục đích | Username | Email | Mật khẩu kiểm thử |
| --- | --- | --- | --- |
| Fixture đã kích hoạt | oliver.bennett | oliver.bennett@fuzcake.test | Oliver!4826Maple |
| Dữ liệu đăng ký cơ sở | lucas.parker | lucas.parker@fuzcake.test | Lucas!7362Maple |
| Customer mới của hành trình | emily.carter | emily.carter@fuzcake.test | Emily!4826Cedar |

Các giá trị mặc định lấy từ CUSTOMER_DESIGN.yaml. Mật khẩu, ô trống, thông tin đăng nhập sai, từ khóa không có kết quả và mã giảm giá lạ đều được cụ thể hóa trước khi xem trước. Robot nhập đúng giá trị đã duyệt, không tạo danh tính hoặc mật khẩu khác trong lúc chạy.

Hành trình thành công yêu cầu username và email chưa tồn tại. Sau lần thành công, chọn giá trị cụ thể mới trong YAML rồi sinh lại trước khi chạy E01. Chuẩn bị fixture giữ tài khoản hiện hữu và từ chối xung đột thông tin truy cập.

## Oracle số lượng và điều kiện tồn kho

Rose Nocturne mặc định có tồn kho khởi tạo 25 chai, tối thiểu 1 và bước nguyên 1. BVA dùng 0, 1, 2, 24, 25, 26 và giá trị danh định 3; EP bổ sung ô trống và 1.5. Sản phẩm biên tách khỏi các sản phẩm bị tiêu thụ bởi đơn hàng E01.

Nhà cung cấp phải bật stock_managed, StockCount của sản phẩm phải được quản lý và ShopProduct.backorder_maximum phải bằng 0. Seed áp dụng chính sách tồn kho hữu hạn cho danh mục fuzcake một lần, kể cả dữ liệu khởi tạo từ phiên bản cũ; giữ nguyên số lượng tồn, điều chỉnh tồn và đơn hàng. Các lần setup sau giữ tùy chỉnh chính sách của người vận hành. Nếu tự sửa chính sách hoặc tồn kho, cần đối chiếu điều kiện trước khi chạy BVA. Xem [khởi tạo và phục hồi](OPERATIONS.md).

Ca vượt tồn vẫn mong đợi bị từ chối. Giỏ trống chưa đủ chứng minh từ chối: browser phải quan sát nút thêm bị vô hiệu hóa hoặc lỗi số lượng/tồn kho native đang hiển thị. Nếu giỏ nhận sản phẩm, test báo lỗi kèm số lượng thực tế. Lỗi server hoặc mạng chung không thỏa oracle nghiệp vụ; hết thời gian chờ vẫn là FAIL.

## Phạm vi customer mở rộng

- Giỏ hàng: BVA số lượng 0, 1, 2, 24, 25, 26 và danh định 3; EP bổ sung trống và 1.5. Thử trên dòng đã có 2 chai, kiểm tra số đã lưu sau khi mở lại và tổng tiền. Ô trống giữ số đã lưu; xóa dòng là thao tác riêng. Bảng quyết định phân biệt xóa một dòng khi còn hàng khác, xóa dòng cuối và thêm lặp cùng SKU.
- Sổ địa chỉ: tiêu đề bắt buộc, tối đa 255 ký tự theo SavedAddressForm native. BVA độ dài 0, 1, 2, 254, 255, 256 và danh định 13. Dữ liệu dài được lưu nguyên văn trong YAML và Excel. Ca 256 dùng thao tác gõ để quan sát giới hạn UI còn 255 ký tự đầu; không sửa DOM hoặc bỏ maxlength. Bổ sung EP đường trống, lưu/sửa/xóa và bảng quyết định quyền sở hữu. Địa chỉ mặc định checkout được giữ nguyên.
- Mật khẩu: EP mật khẩu hiện tại sai/trống, mật khẩu mới trống, xác nhận trống/khác; bảng quyết định xét đăng nhập, mật khẩu hiện tại và cặp mật khẩu mới. Không áp đặt BVA độ dài khi chưa có validator tương ứng. Ca thành công chứng minh mật khẩu cũ bị từ chối, mật khẩu mới đăng nhập được, rồi phục hồi mật khẩu gốc qua UI.

Grace Mitchell (grace.mitchell / Grace!5824Willow) và Henry Foster (henry.foster / Henry!7362Cedar) là hai fixture riêng, được seed_customer_tests tạo khi thiếu. Seed từ chối xung đột, không reset mật khẩu hoặc quyền đang có. Ca địa chỉ xóa đúng bản ghi vừa tạo qua liên kết UI. Nếu bị ngắt giữa chừng, đối chiếu ảnh/log rồi dọn địa chỉ còn lại hoặc phục hồi mật khẩu bằng tài khoản sở hữu trước khi chạy lại.

Ca A11 cố ý mở liên kết Edit/Delete đã lấy từ UI của chủ sở hữu bằng phiên khách khác để thử phân quyền. Native có thể trả form tạo mới trống khi mở Edit của địa chỉ người khác; oracle yêu cầu không lộ dữ liệu và không xóa được bản ghi của chủ. Đây là truy cập URL qua browser, không gọi API hoặc ORM trong test Robot.

## Sinh và chạy

```bat
cmdc.cmd generate --app shuup --customer
cmdc.cmd report --app shuup --media
cmdc.cmd robot --app shuup --customer
cmdc.cmd report --app shuup
```

Chạy riêng các phần mới, độc lập với E01:

```bat
cmdc.cmd robot --app shuup --customer --customer-stage basket_update
cmdc.cmd robot --app shuup --customer --customer-stage address_book
cmdc.cmd robot --app shuup --customer --customer-stage password_change
cmdc.cmd report --app shuup --media
```

Mỗi lần Robot ghi đè output.xml theo quy ước hiện hành. Nếu chạy từng nhóm, xuất report sau từng lượt để lưu tham chiếu tương ứng; thư mục ảnh từng run vẫn được giữ. Lượt đầy đủ gồm 52 execution và workbook 71 ca.

Để kiểm tra riêng tồn kho, dùng `cmdc.cmd robot --app shuup --customer --customer-case SH-CUST-Q06`. Lựa chọn này tránh lặp lại đăng ký và tạo đơn đã thành công. Chạy report sau Robot kể cả khi Robot trả mã lỗi để lấy ảnh và kết quả nguồn. Sinh ca và xuất báo cáo không thay thế thực thi browser.

Xem [dữ liệu YAML](YAML_TEST_DATA.md), [báo cáo Excel](SHUUP_CUSTOMER_REPORT.md) và [hiện thực kiểm thử](SHUUP_CUSTOMER_TEST_CODE.md).

[NAVIGATION](../NAVIGATION.md)
