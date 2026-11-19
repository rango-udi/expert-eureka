[NAVIGATION](documents/NAVIGATION.md)

# 🚀 Bắt đầu theo mục tiêu

Cài Docker chạy Linux containers, Compose từ 2.24.0 và BuildKit có named contexts. Giải nén đầy đủ apps, scripts, config và fuzcake-data cùng root. Chạy lệnh tại root: Windows CMD dùng cmdc.cmd; PowerShell dùng .\cmdc.cmd; Linux/macOS dùng sh cmdc.

## Chọn ứng dụng

```bat
cmdc.cmd apps
```

Lấy ID từ bảng và xem [APPS](documents/APPS.md) để biết nghiệp vụ, ngân sách và giới hạn. Có thể chạy doctor để kiểm tra engine/Compose/RAM trước; setup cũng kiểm tra điều kiện cần thiết. Khi cần chỉnh VM, xem [MEMORY](documents/guides/MEMORY.md).

## Chọn một cách bắt đầu

### Chỉ mở cửa hàng để dùng thủ công

```bat
cmdc.cmd setup --app shuup
cmdc.cmd urls --app shuup
```

Setup đã build/khởi tạo và mở web; không cần thêm start. Mở URL trả về và đăng nhập từ UI bằng tài khoản trong apps/shuup/.env. Thay shuup bằng oscar hoặc wowy để dùng app Django khác.

### Chuẩn bị và chạy suite mặc định ngay

```bat
cmdc.cmd setup --app shuup --run-tests
```

Một lệnh gồm chuẩn bị app, browser và chạy test mặc định. Không cần chạy robot-init hay robot thêm để lặp lại cùng lượt test. Luồng này không gọi validate. Suite có thể tạo đơn hoặc thay dữ liệu kiểm thử.

Riêng Shuup, muốn bộ customer từ đăng ký tới lịch sử đơn thay smoke, dùng `cmdc.cmd setup --app shuup --run-tests --customer`. App đã có thì `cmdc.cmd robot --app shuup --customer`. Xem [bảng ca và điều kiện dữ liệu](documents/guides/SHUUP_CUSTOMER_TEST_DESIGN.md) trước khi chạy vì suite tạo tài khoản và đơn local.

### Chạy một ca customer cụ thể

Khi Shuup đã được chuẩn bị:

```bat
cmdc.cmd robot --app shuup --customer --customer-case SH-CUST-B09
```

Lệnh chỉ chọn ca cập nhật giỏ với số lượng 1.5. Cả lượt đầy đủ và lượt một ca đều chạy `apps/shuup/reports/customer/run.robot`, được sinh lại từ YAML trước khi Robot chạy. Xem [thứ tự launcher, Python, Robot và đường dẫn mã](documents/guides/SHUUP_CUSTOMER_EXECUTION.md). Với customer, chọn bằng `--customer-case` hoặc `--customer-stage`.

### Chuẩn bị trước, chọn test sau

```bat
cmdc.cmd setup --app shuup --with-robot
```

Lệnh mở web và chuẩn bị browser nhưng chưa chạy suite. Khi sẵn sàng, chọn robot mặc định, --test, --include hoặc --design theo [WORKFLOWS](documents/guides/WORKFLOWS.md). Có thể bỏ --with-robot để hoãn build browser tới lần gọi robot.

Các nhóm customer bổ sung chạy riêng bằng `--customer-stage basket_update`, `address_book` hoặc `password_change` cùng `robot --app shuup --customer`. Setup tạo thêm hai tài khoản fixture riêng; xem [thiết kế và điều kiện chạy lại](documents/guides/SHUUP_CUSTOMER_TEST_DESIGN.md).

### Xuất báo cáo customer Shuup

```bat
cmdc.cmd report --app shuup
```

Chạy sau lượt Robot customer, kể cả khi lượt đó có ca FAIL, để tự lấy kết quả nguồn và ảnh theo từng TC. Excel được lưu tại apps/shuup/reports/customer/customer_test_cases.xlsx. Dùng `--media` khi cần hình phân tích BVA/EP/bảng quyết định. Khi tệp mặc định đang mở và bị Excel khóa, báo cáo mới dùng tên riêng cùng thư mục; đọc WARNING và đường dẫn in ra. Mở Excel không cản Robot chạy. Xem [báo cáo và bằng chứng](documents/guides/SHUUP_CUSTOMER_REPORT.md).

### Dùng PHP/.NET hoặc Pretix

Chọn một app, không chạy cả hai dòng liên tiếp:

```bat
cmdc.cmd setup --app woocommerce --run-tests --accept-resource-risk
```

```bat
cmdc.cmd setup --app pretix --run-tests --accept-pretix-risk
```

Thay woocommerce bằng prestashop hoặc nopcommerce nếu phù hợp. Xem [NATIVE_COMMERCE](documents/guides/NATIVE_COMMERCE.md) và [Pretix](documents/apps/PRETIX.md) trước khi chọn. Cờ chấp thuận tải áp dụng cho từng lần gọi; trên terminal tương tác có thể xác nhận bằng cách gõ ID tại prompt. Pretix không nhận --with-robot; robot-init là lựa chọn chuẩn bị browser riêng.

## Những lần chạy tiếp theo

| Nhu cầu | Lệnh với app đã khởi tạo |
| --- | --- |
| Mở lại cửa hàng | `cmdc.cmd start --app shuup` |
| Chạy UI Django (tự chuẩn bị browser và mở web) | `cmdc.cmd robot --app shuup` |
| Xuất Excel và bằng chứng customer Shuup | `cmdc.cmd report --app shuup` |
| Sinh và chạy ca theo model Shuup | `cmdc.cmd robot --app shuup --design` |
| Kiểm tra code/config/regression nội bộ, không mở browser | `cmdc.cmd validate --app shuup` |
| Chỉ kiểm tra cấu trúc suite | `cmdc.cmd robot --app shuup --dryrun` |
| Dừng, giữ dữ liệu | `cmdc.cmd down --app shuup` |

Đây là các lựa chọn độc lập. Validate, dryrun và chạy UI có phạm vi khác nhau; không bắt buộc chạy đủ ba ở mỗi phiên. PHP/.NET robot cần web đang chạy và không nhận --dryrun; start trước nếu đã down. Khi đổi app, down app cũ trước.

## Khi lỗi hoặc cập nhật source

Dùng diagnostics --app shuup để đọc log backend cục bộ, kể cả khi Docker không chạy. Dùng logs khi cần log container và status để biết trạng thái. Giữ .env, .runtime và volume khi chẩn đoán; không xóa database để sửa lỗi runtime.

Giữ cấu hình/dữ liệu khi thay source rồi setup để rebuild/migrate. Sửa riêng model/suite đã mount thường chỉ cần gọi robot. Quy trình và lý do chọn từng bước tại [WORKFLOWS](documents/guides/WORKFLOWS.md); hợp đồng từng lệnh, tên đồng nghĩa, phạm vi validate và thao tác xóa tại [COMMANDS](documents/guides/COMMANDS.md).

[NAVIGATION](documents/NAVIGATION.md)
