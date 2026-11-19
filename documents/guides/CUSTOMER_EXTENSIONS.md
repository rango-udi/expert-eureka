[NAVIGATION](../NAVIGATION.md)

# Giỏ hàng, sổ địa chỉ và mật khẩu customer

Bộ customer gồm 71 ca nghiệp vụ liên kết với 52 execution Robot. Phần bổ sung có 30 ca độc lập; mỗi ca ánh xạ một execution và dùng đúng dữ liệu cụ thể trong CUSTOMER_DESIGN.yaml. Tên/mô tả ca tiếng Việt lấy từ CUSTOMER_EXTENSION_TEXT.json; tên thực thi tiếng Anh lấy từ cùng ID. CSV/JSON dùng tiếng Anh, Markdown/Excel dùng tiếng Việt. Cột đầu vào hiển thị đầy đủ giá trị, kể cả mật khẩu và các tiêu đề dài, không chứa mã nguồn.

| Chức năng | Ca nghiệp vụ | Execution | Phân tích |
| --- | --- | --- | --- |
| Cập nhật/xóa giỏ, thêm lặp | TC-GB-001 đến TC-GB-012 | SH-CUST-B01 đến B12 | BVA 0/1/2/24/25/26/3, EP trống và phân số, 3 quy tắc thao tác giỏ |
| Sổ địa chỉ | TC-SD-001 đến TC-SD-011 | SH-CUST-A01 đến A11 | BVA độ dài 0/1/2/254/255/256/13, EP đường trống và quyền sở hữu, 3 quy tắc sửa/xóa |
| Đổi mật khẩu | TC-MK-001 đến TC-MK-007 | SH-CUST-P01 đến P07 | 7 phân vùng và 7 quy tắc đăng nhập/mật khẩu hiện tại/cặp mật khẩu mới |

## Chuẩn bị và chạy riêng phần mới

Sau khi cập nhật source, setup tạo fixture còn thiếu và giữ tài khoản/giao dịch đã có:

```bat
cmdc.cmd setup --app shuup --with-robot
cmdc.cmd robot --app shuup --customer --customer-case "SH-CUST-B*" --customer-case "SH-CUST-A*" --customer-case "SH-CUST-P*"
cmdc.cmd report --app shuup --media
```

Chạy lệnh report riêng kể cả khi Robot trả mã lỗi. Cũng có thể chọn từng nhóm bằng --customer-stage basket_update, address_book hoặc password_change. Bộ lọc áp dụng trước DataDriver; không dùng --test/--include để chọn ca customer. Lượt chỉ chọn ba nhóm này tránh đăng ký và tạo lại đơn của E01.

## Dữ liệu và phục hồi

| Tài khoản | Email | Mật khẩu gốc | Vai trò |
| --- | --- | --- | --- |
| grace.mitchell | grace.mitchell@fuzcake.test | Grace!5824Willow | Sổ địa chỉ và đổi mật khẩu |
| henry.foster | henry.foster@fuzcake.test | Henry!7362Cedar | Kiểm tra phân tách địa chỉ |

Mật khẩu mới trong P06 là Grace!9637Cedar. Ca này kiểm tra mật khẩu cũ bị từ chối, đăng nhập bằng mật khẩu mới, đổi lại mật khẩu gốc qua UI rồi đăng nhập lại để xác nhận. Nếu lỗi sau thao tác đổi, executor chụp trước phục hồi và cố gắng phục hồi qua phiên UI mới; lỗi ban đầu vẫn được giữ. Nếu phục hồi thất bại hoặc tiến trình bị ngắt, xem log/ảnh để xác định mật khẩu còn hiệu lực rồi đổi lại qua UI. Seed không tự reset mật khẩu.

Ca địa chỉ lưu loại 1 (shipping) và trạng thái 1 (enabled) qua các lựa chọn native. Mỗi ca chỉ xóa địa chỉ vừa tạo bằng liên kết Delete có ID lấy từ UI; không xóa địa chỉ mặc định hoặc bản ghi khác. Nếu ca bị ngắt và tiêu đề còn tồn tại, lượt sau báo điều kiện dữ liệu thay vì tự xóa. Đăng nhập đúng chủ để kiểm tra/dọn bản ghi đó trước khi chạy lại.

## Oracle và giới hạn

- Dòng giỏ native dùng khối .single-item, không phải tr. Selector giới hạn đúng tiêu đề trong .product-details .name và kiểm tra duy nhất một khối trước khi sửa/xóa; liên kết ảnh không được dùng để xác định tên.
- Lỗi cập nhật giỏ native được render bằng alert-warning. Bộ quan sát đọc warning cùng danger nhưng vẫn yêu cầu nội dung lỗi số lượng/tồn kho/bội số và số lượng đã lưu giữ nguyên; warning chung không làm test đạt. Nếu không thấy từ chối, ảnh được chụp trước tải lại và lỗi ghi rõ số lượng đã lưu sau tải lại.
- Giỏ khởi đầu với 2 chai Rose Nocturne; cập nhật so sánh số đã lưu sau khi tải lại và tổng tiền theo giá tham chiếu. Ô trống giữ 2 chai. Xóa dòng cuối là thao tác nút xóa riêng, không suy diễn rằng nhập 0 có nghĩa xóa.
- Ca B09 giữ kỳ vọng số lượng chai nguyên. Hook WholeUnitBasketUpdateMethods kiểm tra lượng nội bộ chính xác trước khi native làm tròn; purchase_multiple native bằng 1 tiếp tục kiểm tra bội số ở bước sau. Chỉ đặt bội số 1 chưa đủ vì 1.5 có thể bị làm tròn thành số đang lưu trước validation. Seed sửa một lần các bội số mặc định 0 của sản phẩm không cho phân số, giữ bội số dương đã tùy chỉnh và giữ nguyên tồn kho/giao dịch. Nếu chính sách đã tự sửa, đối chiếu lại điều kiện trước khi chạy.
- SavedAddressForm yêu cầu tiêu đề và giới hạn 255 ký tự. Ca 256 nhập bằng thao tác gõ thật để kiểm tra maxlength, kỳ vọng lưu 255 ký tự đầu. Regression tích hợp riêng kiểm tra form server từ chối chuỗi 256; Robot không bỏ maxlength bằng JavaScript.
- A11 dùng URL Edit/Delete được lấy từ phiên chủ sở hữu để kiểm tra phiên khách khác. Native có thể hiện form mới trống khi mở Edit không thuộc mình; oracle kiểm tra không lộ giá trị và bản ghi chủ vẫn tồn tại sau thử xóa.
- Không đặt biên độ dài mật khẩu tùy ý. Các ca mật khẩu dùng ràng buộc form và trạng thái đăng nhập hiện hữu; thay validator phải phân tích lại.

## Ảnh và bằng chứng

Các hình dưới đây là phân tích thiết kế, không phải ảnh giao diện đã chạy:

- [BVA độ dài tiêu đề địa chỉ](../assets/shuup/customer-extensions/bva_extension_1.png)
- [BVA cập nhật số lượng giỏ](../assets/shuup/customer-extensions/bva_extension_2.png)
- [Bảng quyết định giỏ](../assets/shuup/customer-extensions/decision_5.png)
- [Bảng quyết định sổ địa chỉ](../assets/shuup/customer-extensions/decision_6.png)
- [Bảng quyết định mật khẩu](../assets/shuup/customer-extensions/decision_7.png)

Media có cả PNG và SVG; workbook nhúng 18 hình của toàn bộ bộ customer. Sau browser run, ảnh UI từng TC nằm trong reports/customer/evidence/<run-id>/screenshots/. Chụp trước dọn địa chỉ, trước phục hồi mật khẩu và khi lỗi giúp giữ ngữ cảnh đã kiểm tra. Report đối chiếu run/model/checksum và điền đường dẫn thật vào cột Bằng chứng. Sinh thiết kế hoặc xuất Excel không tạo kết quả thực thi hay ảnh UI.

Xem [thiết kế customer](SHUUP_CUSTOMER_TEST_DESIGN.md), [hiện thực](SHUUP_CUSTOMER_TEST_CODE.md) và [xuất Excel](SHUUP_CUSTOMER_REPORT.md).

[NAVIGATION](../NAVIGATION.md)
