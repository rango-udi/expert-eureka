[NAVIGATION](../NAVIGATION.md)

# Từ lệnh CMD đến lượt kiểm thử customer

Tài liệu này đi theo đúng thứ tự gọi của mã Windows hiện tại. Mọi đường dẫn bắt đầu từ thư mục gốc dự án. Python của ứng dụng, Python của Robot và Chromium đều chạy trong Docker; Windows chỉ cần launcher, Docker và Compose.

## 1. Chọn lệnh theo nhu cầu

| Nhu cầu | Lệnh chạy tại thư mục chứa cmdc.cmd |
| --- | --- |
| Chuẩn bị cửa hàng rồi chạy toàn bộ customer | `cmdc.cmd setup --app shuup --run-tests --customer` |
| Cửa hàng đã chuẩn bị, chạy lại toàn bộ customer | `cmdc.cmd robot --app shuup --customer` |
| Chạy riêng ca cập nhật giỏ bằng số lẻ | `cmdc.cmd robot --app shuup --customer --customer-case SH-CUST-B09` |
| Chạy riêng ca thêm quá tồn kho | `cmdc.cmd robot --app shuup --customer --customer-case SH-CUST-Q06` |
| Chạy riêng hành trình mua hàng | `cmdc.cmd robot --app shuup --customer --customer-case SH-CUST-E01` |
| Chỉ chạy nhóm sổ địa chỉ | `cmdc.cmd robot --app shuup --customer --customer-stage address_book` |
| Xuất Excel cùng hình phân tích sau lượt Robot | `cmdc.cmd report --app shuup --media` |

Lệnh có `--customer` chạy bộ customer hiện có 52 lượt Robot, tương ứng 71 ca nghiệp vụ trong Excel. Nó không chạy kèm smoke, bộ ví `--design`, kiểm tra CLI hoặc kiểm tra tích hợp Django. Các kiểm tra nội bộ được gọi riêng bằng `cmdc.cmd validate --app shuup`.

Nếu chưa chuẩn bị cửa hàng mà muốn chạy riêng B09, dùng hai bước:

```bat
cmdc.cmd setup --app shuup --with-robot
cmdc.cmd robot --app shuup --customer --customer-case SH-CUST-B09
```

## 2. Lệnh chạy toàn bộ customer đi qua đâu?

Lệnh cần theo dõi:

```bat
cmdc.cmd setup --app shuup --run-tests --customer
```

### Bước 1: CMD chuyển đối số sang PowerShell

[cmdc.cmd](../../cmdc.cmd) chạy `powershell.exe` với tệp [scripts/cmdc.ps1](../../scripts/cmdc.ps1). `%*` chuyển các đối số đã nhập sang script. Vì vậy PowerShell nhận `setup`, `--app shuup`, `--run-tests` và `--customer`.

Script PowerShell này xử lý ở phần thân chương trình, không có hàm Python hay hàm tên `main` ở bước này. Nó tách `--app shuup`, giữ các tùy chọn còn lại, kiểm tra Docker, quyền sở hữu tài nguyên, trạng thái ứng dụng và khóa vận hành. Nó gọi `scripts/system.ps1` với `doctor` để kiểm tra môi trường, rồi dùng hàm `Invoke-Adapter` mở adapter Shuup.

### Bước 2: Adapter Shuup chuẩn bị ứng dụng

Tệp chạy tiếp là [apps/shuup/scripts/adapter.ps1](../../apps/shuup/scripts/adapter.ps1), nhận `setup --run-tests --customer`. Trong nhánh `setup`, thứ tự là:

| Thứ tự | Hàm hoặc câu lệnh trong adapter | Việc thực hiện |
| --- | --- | --- |
| 1 | `Build-App` | Gọi `Test-Preflight`, sau đó `Invoke-Compose build tools` để build runtime ứng dụng/công cụ |
| 2 | `Invoke-Compose stop shuup` | Dừng tiến trình web trước migration và seed |
| 3 | `Invoke-Tool init` | Kiểm tra image rồi chạy service `tools` với đối số `init` |
| 4 | `Build-Robot` | Build service `robot` vì có `--run-tests` |
| 5 | `Start-Shuup` | Kiểm tra dữ liệu, khởi động web và đợi healthcheck qua Compose `--wait` |
| 6 | `Invoke-Compose run --rm --no-deps --pull never robot --customer` | Tạo container tác vụ Robot và bắt đầu bộ customer |

`Invoke-Compose` ghép lệnh Docker với [apps/shuup/compose.yaml](../../apps/shuup/compose.yaml). `Test-Preflight` nằm trong [scripts/memory_policy.ps1](../../scripts/memory_policy.ps1). Các bước lỗi sẽ dừng chuỗi tại bước đó; Robot chưa được gọi nếu build, khởi tạo hoặc readiness thất bại.

### Bước 3: Container tools chạy Python để khởi tạo

Service `tools` có entrypoint `python scripts/commands.py`, thư mục làm việc `/app`. Khi adapter thêm `init`, lệnh trong container tương đương:

```text
python scripts/commands.py init
```

Trong [apps/shuup/scripts/commands.py](../../apps/shuup/scripts/commands.py), `main()` đọc lệnh, giữ `command_lock()`, gọi `ensure()` và `load()` từ [configuration.py](../../apps/shuup/scripts/configuration.py). `ensure()` giữ hoặc tạo cấu hình cần thiết; `load()` đưa cấu hình vào môi trường của tiến trình.

Với lệnh `init`, `main()` gọi `initialize()`. Hàm này gọi `django()` lần lượt cho:

1. `migrate`: áp dụng migration vào database của app.
2. `seed_demo`: tạo dữ liệu còn thiếu và áp dụng các phần sửa cấu hình có marker riêng.
3. `collectstatic`: gom asset phục vụ cửa hàng.
4. `reindex_product_catalog`: xây lại chỉ mục tìm kiếm.

`seed_demo` đi vào `Command.handle()` trong [seed_demo.py](../../apps/shuup/storefront/management/commands/seed_demo.py). Cuối lệnh này, `seed_customer_tests` gọi `Command.handle()` trong [seed_customer_tests.py](../../apps/shuup/storefront/management/commands/seed_customer_tests.py) để chuẩn bị các tài khoản kiểm thử đã khai báo. Đây là chuẩn bị dữ liệu trước kiểm thử, không phải các thao tác Robot thực hiện qua UI.

Setup giữ số lượng tồn và giao dịch đang có. Nó không tạo lại danh tính E01 đã dùng thành công. Trước khi chạy lại toàn bộ, cần chọn username/email E01 chưa tồn tại trong YAML và xem lại dữ liệu sinh ra.

### Bước 4: Web và Robot chạy trong hai tiến trình khác nhau

Sau khởi tạo, `Start-Shuup` chạy service `shuup`; service này mở [scripts/web_server.py](../../apps/shuup/scripts/web_server.py). Container Robot được tạo sau khi web sẵn sàng. Browser truy cập cửa hàng qua `http://shuup:8000`, là địa chỉ trong mạng Compose, không phải cổng localhost mà người dùng mở trên Windows.

Service `robot` có entrypoint:

```text
python scripts/commands.py robot
```

Adapter thêm `--customer`, nên Python nhận `robot --customer`. `commands.main()` đi vào nhánh `robot` và gọi `robot(extra)` trong chính tệp đó.

### Bước 5: Python sinh bộ ca trước khi gọi Robot Framework

Trong `commands.robot(arguments)`:

1. Đọc cấu hình và đặt `BASE_URL=http://shuup:8000` cho tiến trình con.
2. Nhận ra `--customer` và bỏ cờ này khỏi đối số sẽ chuyển cho Robot Framework.
3. Gọi `run()` để chạy `python scripts/customer_design.py`.
4. Sau khi sinh thành công, đặt suite thành `/app/reports/customer/run.robot`.
5. Gọi `run()` lần nữa để chạy Robot Framework với suite đó.

Trong [customer_design.py](../../apps/shuup/scripts/customer_design.py), `main()` gọi `export()`. `export()` đọc YAML, gọi `build_plan()`, chọn các ca được xếp chạy và ghi CSV, model đã đóng băng, bảng ca và tệp `run.robot`. Chi tiết từng tệp ở [luồng dữ liệu](SHUUP_CUSTOMER_DATA_FLOW.md).

Lệnh Robot Framework tương đương trong container:

```text
python -m robot --exitonerror --outputdir /app/reports /app/reports/customer/run.robot
```

### Bước 6: Robot đọc suite được sinh và gọi thư viện Python

Tệp thực sự được chạy là **apps/shuup/reports/customer/run.robot**, không phải `apps/shuup/tests/robot/smoke.robot`. Tệp này được sinh lại mỗi lần gọi lệnh customer.

Robot nạp Browser, thư viện `CustomerJourney.py` và DataDriver. DataDriver đọc các dòng đã chọn trong `robot_transport.csv`, tạo các test tương ứng rồi dùng keyword `Run Customer Case` làm phần thân cho từng test. Keyword này gọi `Execute Customer Case`, được nối trực tiếp đến `CustomerJourney.execute_customer_case()`.

Xem giải thích từng dòng Robot và từng nhánh Python tại [đọc mã Robot](SHUUP_CUSTOMER_ROBOT_WALKTHROUGH.md).

### Bước 7: Chạy từng test và lưu kết quả

Với mỗi test, `execute_customer_case()` kiểm tra dữ liệu rồi tạo Browser/context/page mới. Nó chọn hàm Python theo `stage`, thực hiện thao tác UI và xác nhận kết quả. Kết thúc ca, mã lưu ảnh/trạng thái bằng chứng; Robot chạy `Test Teardown    Close Browser` cả khi ca đạt hoặc lỗi.

Robot ghi `output.xml`, `log.html` và `report.html` vào `/app/reports`, được mount ra `apps/shuup/reports` trên máy. `--exitonerror` xử lý lỗi thực thi của Robot; một assertion FAIL thông thường không đồng nghĩa tự dừng toàn bộ các test còn lại. Mã thoát tổng được chuyển ngược qua Python, adapter, launcher và CMD.

## 3. Chạy một test khác chạy toàn bộ ở điểm nào?

Lệnh ví dụ:

```bat
cmdc.cmd robot --app shuup --customer --customer-case SH-CUST-B09
```

| Thứ tự | Điểm khác với lệnh setup toàn bộ |
| --- | --- |
| 1 | `cmdc.cmd` và `scripts/cmdc.ps1` vẫn chọn đúng adapter Shuup |
| 2 | Adapter đi vào nhánh `robot`, gọi `Build-Robot`, `Start-Shuup`, rồi chạy container Robot với các đối số đã nhập |
| 3 | Nhánh này không gọi `Invoke-Tool init`, `initialize()` hoặc `seed_demo`; phải chuẩn bị cửa hàng trước |
| 4 | `commands.robot()` chuyển `--customer-case SH-CUST-B09` thành `--case SH-CUST-B09` cho customer_design.py |
| 5 | `export()` vẫn xây model đủ 52 execution, nhưng `scheduled` chỉ có B09; robot_transport.csv có một dòng test |
| 6 | Robot vẫn chạy cùng đường dẫn reports/customer/run.robot, DataDriver chỉ tạo B09 từ CSV đã lọc |
| 7 | B09 gọi `execute_customer_case()` → `_basket_update()`; không gọi `_journey()` của E01 |

Dòng `Customer plan: 52 cases; 1 scheduled; generated, not executed` nói về kết quả **sinh kế hoạch trước khi chạy**. `52 cases` không có nghĩa cả 52 đã được thực thi. Số test thực sự chạy xem ở tổng kết Robot và output.xml.

Không dùng `--test SH-CUST-B09` hoặc `--include` để chọn ca customer: commands.py từ chối các lựa chọn này để tránh lọc sai thời điểm DataDriver tạo test. Dùng `--customer-case` hoặc `--customer-stage`.

## 4. Xuất Excel là lệnh tiếp theo, không nằm trong setup

```bat
cmdc.cmd report --app shuup --media
```

Adapter đi vào nhánh `report`, build service báo cáo rồi chạy `python scripts/customer_report.py`. `main()` của tệp này đọc output.xml đã có, chuẩn bị dữ liệu, tạo hình phân tích và ghi workbook. Lệnh không chạy browser và không gọi lại 52 ca.

Chạy report bằng một lệnh riêng kể cả khi Robot vừa trả FAIL. Report mặc định dùng `apps/shuup/reports/output.xml` nếu tệp tồn tại. Nếu muốn nguồn khác, dùng `--results` với đường dẫn từ app. Nếu Excel khóa tên mặc định, chương trình lưu tên thay thế và in đường dẫn thực tế.

## 5. Tìm lỗi theo bước đang dừng

| Dừng ở đâu? | Mở tệp hoặc hàm nào trước? |
| --- | --- |
| Chưa tạo container Robot | scripts/cmdc.ps1, adapter.ps1, thông báo build/init/readiness |
| `Invalid customer design` | customer_design.main()/export(), YAML và dữ liệu tham chiếu |
| DataDriver tạo sai số test | scheduled_ids trong coverage.json và các dòng robot_transport.csv |
| Keyword `Execute Customer Case` lỗi | CustomerJourney.execute_customer_case() và hàm được chọn theo stage |
| B09 chưa thấy warning hoặc giá trị sai | CustomerExtensions._basket_update(), _extra_update_rejection() và hook server storefront/basket.py |
| Ảnh chưa được gắn vào Excel | customer_report_data.prepare_report(), customer_evidence.verified_images() và metadata của XML nguồn |

[NAVIGATION](../NAVIGATION.md)
