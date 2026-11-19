[NAVIGATION](../NAVIGATION.md)

# Đọc mã Robot customer theo thứ tự thực hiện

Đọc [đường đi của lệnh CMD](SHUUP_CUSTOMER_EXECUTION.md) trước nếu cần biết ai tạo container hoặc ai gọi Robot Framework. Tài liệu này bắt đầu từ tệp Robot đã được sinh và đi đến các hàm thực hiện từng ca.

## 1. Tệp Robot nào được chạy?

Với cả hai lệnh dưới đây, suite là `apps/shuup/reports/customer/run.robot`:

```bat
cmdc.cmd setup --app shuup --run-tests --customer
cmdc.cmd robot --app shuup --customer --customer-case SH-CUST-B09
```

Khác biệt nằm ở số dòng test trong CSV mà DataDriver đọc: lệnh đầu chọn toàn bộ 52 execution, lệnh sau chỉ chọn B09. Nội dung suite được ghi bởi `export()` trong [customer_design.py](../../apps/shuup/scripts/customer_design.py), không cần viết một tệp .robot riêng cho từng ID.

Phần chính của suite được sinh như sau. Dòng Metadata còn được thêm để ghi dấu vân tay model của lượt sinh:

```robot
*** Settings ***
Documentation    Reduced customer specification. Generation is not browser execution.
Library    Browser
Library    ${CURDIR}/../../tests/robot/CustomerJourney.py    ${CURDIR}/model.json
Library    DataDriver    file=${CURDIR}/robot_transport.csv    dialect=userdefined    delimiter=;    encoding=utf-8
Test Template    Run Customer Case
Test Teardown    Close Browser
Test Tags    customer

*** Test Cases ***
Customer case placeholder
    unused

*** Keywords ***
Run Customer Case
    [Arguments]    ${payload}
    Execute Customer Case    ${payload}
```

| Dòng Robot | Cách đọc và tác dụng |
| --- | --- |
| `Library Browser` | Nạp thư viện điều khiển Chromium qua Playwright |
| `Library .../CustomerJourney.py .../model.json` | Nạp lớp CustomerJourney và truyền đường dẫn model đã đóng băng vào hàm khởi tạo |
| `Library DataDriver ...` | Đọc CSV UTF-8, tách cột bằng dấu chấm phẩy và tạo test từ các dòng đã chọn |
| `Test Template Run Customer Case` | Mỗi test dùng chung keyword này, với payload riêng của dòng CSV |
| `Test Teardown Close Browser` | Sau test, đóng browser kể cả khi assertion thất bại |
| `Test Tags customer` | Gắn nhãn customer cho các test của suite |
| `Customer case placeholder / unused` | Chỗ đặt ban đầu để DataDriver xây các test thật; không phải một ca nghiệp vụ cần nhập dữ liệu `unused` |
| `[Arguments] ${payload}` | Nhận một đối số chứa dữ liệu ca đã được mã hóa trong CSV |
| `Execute Customer Case ${payload}` | Chuyển dữ liệu sang keyword Python đã được đăng ký |

`${CURDIR}` là thư mục chứa suite. Khi chạy trong container, nó là `/app/reports/customer`; vì vậy đường dẫn `../../tests/robot/CustomerJourney.py` dẫn tới `/app/tests/robot/CustomerJourney.py`.

## 2. DataDriver đưa dữ liệu vào keyword thế nào?

CSV có các cột `*** Test Cases ***`, `${payload}`, `[Tags]`, `[Documentation]`. Với B09, tên test là `SH-CUST-B09 Updating a basket line with quantity 1.5`. Payload là JSON được mã hóa Base64 để truyền ổn định trong một cột; đây không phải mã chương trình.

Khi đến dòng B09, DataDriver dùng tên, tag và mô tả của dòng đó, rồi gọi:

```text
Run Customer Case(payload của B09)
  → Execute Customer Case(payload của B09)
  → CustomerJourney.execute_customer_case(payload của B09)
```

Tên keyword Python được khai báo bằng `@keyword('Execute Customer Case')` trong [CustomerJourney.py](../../apps/shuup/tests/robot/CustomerJourney.py). `ROBOT_AUTO_KEYWORDS=False` giúp các hàm hỗ trợ có dấu gạch dưới không tự trở thành keyword công khai.

Nội dung CSV được sinh tự động từ YAML. Khi cần đổi dữ liệu, sửa YAML rồi sinh/chạy lại; không chỉnh chuỗi Base64 hoặc sao chép nó vào Excel.

## 3. Python chuẩn bị và chọn nhánh chạy

`CustomerJourney` kế thừa `CustomerExtensionKeywords` trong [CustomerExtensions.py](../../apps/shuup/tests/robot/CustomerExtensions.py). Nhờ đó `self._basket_update()` được gọi trên cùng đối tượng CustomerJourney, dù phần định nghĩa nằm ở tệp khác.

Khi nạp thư viện, `CustomerJourney.__init__(model_path)` đọc model.json và các tham chiếu catalogue/store/partners, kiểm tra dấu vân tay và đọc BASE_URL. Lớp có phạm vi `SUITE`, nên đối tượng được dùng chung trong suite; browser/context/page vẫn được tạo mới ở mỗi ca.

Trong mỗi lần `execute_customer_case(payload)`:

1. Giải mã Base64, đọc JSON và lấy ID của execution.
2. So dấu vân tay của ca với model.json; dữ liệu bị đổi sau khi sinh sẽ bị từ chối.
3. Lấy instance Browser đã được Robot nạp.
4. Nếu đây là ca đầu, tạo EvidenceRun và ghi run ID/đường dẫn manifest vào metadata suite.
5. Tìm TC nghiệp vụ tương ứng trong hai tệp nội dung ca, đặt TC đang thực hiện bằng `_at()`.
6. Gọi Browser `New Browser`, `New Context`, `New Page`.
7. Đọc `case['stage']` và chọn hàm theo bảng dưới.

| Stage | ID execution | Hàm nhận ca | Nơi định nghĩa |
| --- | --- | --- | --- |
| address_book | A01–A11 | `_address_book(case)` | CustomerExtensions.py |
| basket_update | B01–B12 | `_basket_update(case)` | CustomerExtensions.py |
| login | L01–L04 | `_login_rejection(case)` | CustomerJourney.py |
| password_change | P01–P07 | `_password_change(case)` | CustomerExtensions.py |
| quantity | Q01–Q09 | `_quantity(case)` | CustomerJourney.py |
| registration | R01–R08 | `_registration_rejection(case)` | CustomerJourney.py |
| e2e | E01 | `_journey(case)` | CustomerJourney.py |

Với model hiện tại, lượt đầy đủ được sắp theo A, B, L, P, Q, R; E01 chạy cuối. Thứ tự hàng trong Excel là thứ tự ca nghiệp vụ, không nhất thiết giống thứ tự execution trong console.

## 4. Đi hết một ca cụ thể: B09

Lệnh:

```bat
cmdc.cmd robot --app shuup --customer --customer-case SH-CUST-B09
```

Dữ liệu B09 lấy từ `extensions.cases` trong [CUSTOMER_DESIGN.yaml](../../apps/shuup/tests/data/CUSTOMER_DESIGN.yaml): tài khoản Oliver Bennett, SKU `fuzcake-rose-nocturne`, số lượng ban đầu `2`, giá trị cập nhật `1.5`, kỳ vọng `rejected`, TC nghiệp vụ `TC-GB-009`. Số tiền kỳ vọng được đối chiếu bằng giá tham chiếu của sản phẩm nhân số lượng đã lưu.

### Phần Python điều khiển browser

| Bước | Hàm được gọi | Thao tác hoặc điều kiện được kiểm tra |
| --- | --- | --- |
| 1 | `execute_customer_case()` → `_basket_update(case)` | Chọn đúng nhóm cập nhật giỏ |
| 2 | `_extra_login()` → `_login()` → `_secret()` | Đăng nhập bằng dữ liệu tài khoản đã ghi; nhập mật khẩu qua cơ chế secret của Browser |
| 3 | `_cart_count()` | Yêu cầu giỏ của phiên mới đang trống |
| 4 | `_extra_add()` → `_open_product()` → `_search()` | Tìm sản phẩm qua UI, mở chi tiết, nhập 2 chai và thêm vào giỏ |
| 5 | `_open_cart()` | Mở giỏ bằng liên kết trong menu |
| 6 | `_extra_basket_line()` | Chờ form, tìm đúng .single-item theo tiêu đề Rose Nocturne, yêu cầu duy nhất một khối |
| 7 | `_kw('Get Attribute', ...)` | Đối chiếu min/step của ô số lượng với miền đã duyệt |
| 8 | `_kw('Promise To', 'Wait For Response', ...)` | Đặt lời chờ phản hồi do thao tác UI sắp tạo ra; chưa gửi một yêu cầu cập nhật riêng |
| 9 | `_kw('Fill Text', ..., '1.5')`, `_kw('Press Keys', ..., 'Tab')` | Nhập số đang thử và rời ô; JavaScript native của trang gửi form cập nhật |
| 10 | `_kw('Wait For', ...)`, `_kw('Wait For Load State', 'networkidle')` | Chờ phản hồi và trang ổn định sau cập nhật |
| 11 | `_extra_update_rejection()` → `_until()` → `_quantity_error()` | Yêu cầu warning/error nghiệp vụ đang hiển thị, không chỉ suy từ việc giỏ giữ nguyên |
| 12 | `_capture(..., 'update-validation')` | Chụp thông báo trước khi tải lại để giữ bằng chứng |
| 13 | `_kw('Reload')`, `Get Property`, `_cart_count()`, `_assert_money()` | Đối chiếu giá trị đã lưu vẫn 2 chai, số trên menu là 2 và tổng tiền bằng hai đơn giá |
| 14 | Trở về `execute_customer_case()` | Chụp kết quả, ghi trạng thái bằng chứng; Robot thực hiện Close Browser |

Các hàm `_kw()`, `_read()`, `_count()`, `_text()` và `_until()` ở CustomerJourney.py là lớp hỗ trợ dùng chung. `_kw()` gọi `BuiltIn.run_keyword('Browser.' + tên_keyword, ...)`, nên thao tác Python vẫn hiện thành các keyword Browser trong log Robot. `_read()` chỉ đọc DOM qua Evaluate JavaScript; không sửa thuộc tính để bỏ validation.

Nếu bước 11 hết thời gian chờ, `_extra_update_rejection()` chụp trang trước tải lại, đọc số đã lưu sau tải lại và ném AssertionError có chi tiết. B09 vẫn FAIL, kể cả khi số đã lưu còn 2 nhưng chưa quan sát được thông báo yêu cầu.

### Phần xử lý ở phía cửa hàng

Các hàm sau chạy ở tiến trình Django của service `shuup`, không chạy trong thư viện Robot:

| Thứ tự sau khi browser gửi form | Tệp / hàm |
| --- | --- |
| 1 | Native `shuup/front/views/basket.py`: `BasketView.dispatch()` nhận command update |
| 2 | Native `shuup/core/basket/command_dispatcher.py`: `BasketCommandDispatcher.handle()` tìm handler |
| 3 | Native `shuup/core/basket/commands.py`: `handle_update()` nhận trường có tiền tố dq_ và gọi phương thức cập nhật được cấu hình |
| 4 | [storefront/settings.py](../../apps/shuup/storefront/settings.py) chọn `storefront.basket:WholeUnitBasketUpdateMethods` |
| 5 | [storefront/basket.py](../../apps/shuup/storefront/basket.py): `update_display_quantity()` kiểm tra lượng nội bộ chính xác trước làm tròn |
| 6 | Với 1.5 chai, hàm gửi invalid_quantity qua `_handle_orderability_error()` kế thừa native front và trả về không thay đổi dòng |
| 7 | Native front ghi warning; browser nhận lại trang có thông báo; mã Robot tiếp tục quan sát ở bước 11 |

Các đường dẫn bắt đầu bằng `shuup/` ở bảng này thuộc package upstream cài trong image, không phải các tệp source bổ sung tại workspace. Giá trị hợp lệ được `super().update_display_quantity()` chuyển tiếp tới native để giữ cách kiểm tra stock/min/bội số và cập nhật giỏ. Ví dụ này giải thích đường xử lý dự kiến trong mã, không tự chứng minh lượt browser đã PASS.

## 5. E01 đi qua những hàm nào?

E01 dùng `_journey(case)` trong CustomerJourney.py. Chuỗi chính là:

| Thứ tự | Hàm hoặc khối thao tác |
| --- | --- |
| 1 | `_open_registration()`, `_fill_registration()` rồi gửi form đăng ký |
| 2 | `_activation_link()` đọc email local đúng người nhận và mở liên kết kích hoạt thật |
| 3 | `_logout()`, `_login()` để xác nhận đăng nhập lại |
| 4 | `_search()` kiểm tra từ khóa không có kết quả |
| 5 | Vòng lặp ba sản phẩm: `_open_product(..., inspect_gallery=True)`, `_inspect_product_gallery()`, thêm một chai mỗi sản phẩm |
| 6 | `_open_cart()` và đối chiếu số dòng, số lượng, giá |
| 7 | `_coupon()`, `_addresses()`, `_checkout_methods()` kiểm tra coupon, địa chỉ và từng lựa chọn vận chuyển |
| 8 | Gửi xác nhận với điều khoản chưa chọn, sau đó chọn điều khoản và đặt đơn |
| 9 | `_assert_order_lines()` cùng các kiểm tra tổng tiền/trạng thái thanh toán |
| 10 | Mở danh sách đơn, chọn đúng đơn vừa tạo và kiểm tra chi tiết lịch sử |

Các mốc `_at()`/`_capture()` trong hành trình nối ảnh tới từng TC nghiệp vụ. Một execution E01 vì vậy hỗ trợ nhiều hàng Excel, không tạo một execution Robot riêng cho mỗi mốc.

## 6. Khi nào PASS, FAIL và đóng browser?

Nếu hàm xử lý ca trả về bình thường, execute_customer_case ghi trạng thái PASS vào manifest. Nếu assertion hoặc keyword lỗi, nhánh except chụp trang hiện tại, ghi FAIL và ném lại lỗi để Robot đánh dấu ca thất bại. Sau đó Test Teardown đóng browser. Ảnh chụp lỗi không tự chuyển kết quả thành PASS; lỗi chụp ảnh cũng không được thay lỗi chức năng ban đầu.

Kết quả Robot và ảnh nguồn được dùng khi xuất report theo [luồng dữ liệu](SHUUP_CUSTOMER_DATA_FLOW.md).

[NAVIGATION](../NAVIGATION.md)
