[NAVIGATION](../NAVIGATION.md)

# Dữ liệu customer từ YAML đến browser và Excel

Tài liệu này giải thích nguồn của từng giá trị, nơi lưu kết quả và cách giữ dữ liệu nhất quán khi chạy toàn bộ hoặc chọn một ca. Đường đi của lệnh nằm ở [hướng dẫn thực hiện](SHUUP_CUSTOMER_EXECUTION.md); phần keyword và hàm Python nằm ở [đọc mã Robot](SHUUP_CUSTOMER_ROBOT_WALKTHROUGH.md).

## 1. Mỗi nguồn dữ liệu dùng để làm gì?

Các đường dẫn sau tính từ thư mục gốc dự án.

| Nguồn | Nội dung và nơi sử dụng |
| --- | --- |
| `apps/shuup/tests/data/CUSTOMER_DESIGN.yaml` | Miền giá trị, quy tắc, tài khoản, mật khẩu cụ thể, dữ liệu từng ca và các nhóm customer mở rộng; customer_design.py đọc để xây kế hoạch |
| `fuzcake-data/records/` | Catalogue, cửa hàng và đối tác dùng chung; bộ đọc fuzcake-data cấp giá, SKU, địa chỉ, vận chuyển cho seed và bộ sinh ca |
| `apps/shuup/tests/data/CUSTOMER_CASE_TEXT.json` | Tên, mô tả và nội dung ca gốc bằng tiếng Anh cho dữ liệu ngoài Excel |
| `apps/shuup/tests/data/CUSTOMER_EXCEL_TEXT.json` | Nội dung ca gốc bằng tiếng Việt cho Excel và bảng Markdown |
| `apps/shuup/tests/data/CUSTOMER_EXTENSION_TEXT.json` | Nội dung tiếng Anh và tiếng Việt của các ca giỏ, sổ địa chỉ, đổi mật khẩu |
| `apps/shuup/.env` | Cấu hình riêng của cửa hàng và tài khoản vận hành; configuration.ensure()/load() chuẩn bị môi trường |
| `apps/shuup/.runtime/data/db.sqlite3` | Dữ liệu thực của cửa hàng đang chạy: tài khoản, giỏ, tồn kho, địa chỉ, đơn hàng |
| `apps/shuup/.runtime/data/mail/` | Email local, gồm thư kích hoạt mà E01 đọc theo người nhận và thời gian gửi |

YAML và các tệp nội dung ca là đầu vào của bộ sinh. Excel là tài liệu để đọc, ghi nhận và đối chiếu; chương trình không đọc workbook để điều khiển Robot. Sửa Excel không đổi dữ liệu browser ở lượt chạy sau.

Tên người, địa chỉ và giá trị nhập bằng tiếng Anh. Tên và mô tả ca trong Excel, cùng tài liệu Markdown, dùng tiếng Việt. Dữ liệu đầu vào trong Excel là giá trị cụ thể, kể cả mật khẩu kiểm thử hư cấu; không chứa biểu thức Python, keyword Robot hoặc chuỗi payload nội bộ.

## 2. Có hai đường sử dụng dữ liệu cần phân biệt

**Chuẩn bị cửa hàng:** `commands.initialize()` gọi seed_demo rồi seed_customer_tests để tạo các bản ghi còn thiếu. Database đã có vẫn giữ giao dịch, tồn kho và các thay đổi của người vận hành theo quy tắc seed. Việc đọc cùng nguồn tham chiếu không bảo đảm database hiện tại còn đúng mọi điều kiện của ca; cần kiểm tra điều kiện trước khi chạy.

**Thực hiện kiểm thử:** customer_design.py đọc YAML và nguồn tham chiếu để tạo dữ liệu ca. CustomerJourney nhập các giá trị ấy qua browser. Mã Robot không gọi seed để biến kết quả thực tế thành kết quả mong đợi. Cửa hàng nhận form và tự xử lý bằng Django/native Shuup.

Tài khoản kiểm thử ghi trong YAML và tài khoản vai trò tạo qua cấu hình có mục đích khác nhau. Chẳng hạn `_login()` lấy username/password từ `case['inputs']`; `_secret()` truyền mật khẩu qua keyword Fill Secret của Browser. Không thay những giá trị cụ thể trong bảng ca bằng tên biến môi trường.

## 3. Trình tự sinh dữ liệu

Trong [customer_design.py](../../apps/shuup/scripts/customer_design.py), `main()` nhận đường dẫn YAML, thư mục xuất và bộ lọc. `export()` thực hiện theo thứ tự:

1. `load_specification()` đọc YAML qua [specification.py](../../test-design/test_design/specification.py).
2. `build_plan()` kiểm tra model qua `validate_customer_model()` và `customer_inputs.validate_test_data()`.
3. Bộ thiết kế trong [engine.py](../../test-design/test_design/engine.py) phân tích miền và quy tắc; các hàm trong [customer_extensions.py](../../apps/shuup/scripts/customer_extensions.py) thêm nhóm customer mở rộng. [customer_inputs.py](../../apps/shuup/scripts/customer_inputs.py) gắn giá trị cụ thể vào ca.
4. Kế hoạch hoàn chỉnh gồm 52 execution và các dấu vân tay SHA-256 của model, nguồn tham chiếu và từng ca.
5. `export()` lọc `scheduled` theo `--case` và `--stage`, rồi ghi các tệp dưới đây.

| Tệp tại apps/shuup/reports/customer/ | Chạy toàn bộ | Chỉ chọn SH-CUST-B09 |
| --- | --- | --- |
| `model.json` | Model đóng băng và dấu vân tay đủ 52 execution | Vẫn đủ model và dấu vân tay 52 execution |
| `coverage.json` | Kế hoạch đầy đủ; scheduled_count=52 | Kế hoạch đầy đủ; scheduled_count=1, scheduled_ids chỉ có B09 |
| `robot_transport.csv` | 52 dòng ca, ngoài dòng tiêu đề | 1 dòng B09, ngoài dòng tiêu đề |
| `execution_cases.csv` | Nội dung 52 execution bằng tiếng Anh | Nội dung một execution B09 bằng tiếng Anh |
| `test_cases.csv` | 71 ca nghiệp vụ bằng tiếng Anh | Vẫn 71 ca nghiệp vụ |
| `test_cases.md` | 71 ca nghiệp vụ bằng tiếng Việt | Vẫn 71 ca nghiệp vụ |
| `report_data.json` | Dữ liệu báo cáo bằng tiếng Anh | Vẫn đầy đủ bảng ca; chưa phải kết quả browser |
| `run.robot` | Suite dùng template Run Customer Case | Cùng template, đọc CSV chỉ có B09 |

Chuỗi JSON/Base64 trong robot_transport.csv chỉ phục vụ truyền dữ liệu giữa bộ sinh và DataDriver. Khi đọc ca, dùng execution_cases.csv hoặc bảng Excel thay vì giải mã thủ công. Thông báo `generated, not executed` chỉ xác nhận đã sinh thành công; kết quả chạy thuộc output.xml.

## 4. Đi theo giá trị 1.5 của B09

1. YAML ghi số lượng ban đầu `2`, số lượng cần thử `1.5`, kỳ vọng `rejected` và dữ liệu tài khoản riêng.
2. Bộ sinh tạo ca `SH-CUST-B09`, liên kết với ca nghiệp vụ `TC-GB-009`, rồi ghi vào CSV và dấu vân tay trong model.json.
3. DataDriver đọc dòng B09 và gọi `Run Customer Case` → `Execute Customer Case`.
4. `CustomerJourney.execute_customer_case()` giải mã ca, xác minh dữ liệu và gọi `_basket_update()` trong CustomerExtensions.py.
5. Hàm đăng nhập, thêm 2 chai Rose Nocturne qua UI, nhập `1.5` ở giỏ rồi rời ô để form native cập nhật.
6. Django xử lý form bằng phương thức giỏ đã cấu hình trong storefront/settings.py. [storefront/basket.py](../../apps/shuup/storefront/basket.py) kiểm tra lượng chính xác trước khi native quy đổi/làm tròn đơn vị.
7. Robot yêu cầu quan sát được thông báo từ chối, sau đó tải lại và đối chiếu lượng đã lưu vẫn là 2, cùng tổng tiền kỳ vọng từ giá tham chiếu. Việc giỏ giữ nguyên tự nó chưa đủ để đạt ca.
8. Mã chụp UI, ghi manifest bằng chứng; Robot ghi PASS/FAIL và thông báo lỗi vào output.xml.
9. Lệnh report đọc lượt chạy nguồn, kiểm tra ảnh rồi điền đường dẫn liên quan vào cột Bằng chứng của TC-GB-009.

Kỳ vọng của ca đến từ dữ liệu đã duyệt. Chương trình không lấy giá trị giỏ thực tế để tự sửa kỳ vọng của ca.

## 5. Đường dẫn trên máy và trong container

| Trên máy | Trong container Shuup/Robot | Ý nghĩa |
| --- | --- | --- |
| `apps/shuup/` | `/app/` | Gốc ứng dụng, không phải gốc toàn bộ repository |
| `apps/shuup/tests/data/` | `/app/tests/data/` | Đầu vào được mount chỉ đọc cho Robot |
| `apps/shuup/reports/` | `/app/reports/` | Báo cáo được ghi ra máy qua bind mount |
| `apps/shuup/.runtime/` | `/app/.runtime/` | Trạng thái riêng của cửa hàng |
| Dữ liệu chung đã đóng gói từ fuzcake-data | `/fuzcake-data/records/` | Nguồn tham chiếu chỉ đọc |

Ví dụ đường dẫn bằng chứng `reports/customer/evidence/.../image.png` được tính từ **apps/shuup/** trên máy, hay `/app/` trong container. Nó không được tính từ thư mục chứa workbook. Giữ cả thư mục reports khi chuyển báo cáo và ảnh sang máy khác.

Mã Python trong image Robot như scripts/customer_design.py và tests/robot/CustomerExtensions.py không phải bind mount source trực tiếp. Lệnh `robot` có bước build Robot để đưa thay đổi ấy vào image. Mã storefront phía server cần build image ứng dụng bằng setup; chỉ build Robot không cập nhật server. Đầu vào tests/data được mount nên được đọc lại khi sinh ca.

## 6. Ảnh, kết quả nguồn và Excel được nối thế nào?

[customer_evidence.py](../../apps/shuup/scripts/customer_evidence.py) quản lý EvidenceRun. `_at()` ghi TC đang thực hiện; `_capture()` chụp browser tại mốc nghiệp vụ rồi ghi ảnh với execution ID, TC ID và checksum. Khi có lỗi, execute_customer_case chụp trạng thái hiện tại trước khi teardown đóng browser. Suite metadata chứa run ID và vị trí manifest để report tìm đúng lượt chạy.

Sau khi Robot kết thúc, chạy:

```bat
cmdc.cmd report --app shuup --media
```

Đường gọi trong [customer_report.py](../../apps/shuup/scripts/customer_report.py):

1. `main()` chọn output.xml mặc định hoặc tệp app-relative truyền qua `--results`.
2. `import_results()` trong customer_report_data.py đọc kết quả và lưu bản JSON tham chiếu theo checksum nguồn.
3. `prepare_report()` gọi `report_contract()` để xây 71 ca tiếng Việt từ dữ liệu hiện hành.
4. `verified_images()` xác minh metadata lượt chạy, model, ánh xạ TC/execution, đường dẫn và checksum ảnh. Ảnh cũ không khớp dữ liệu hoặc ảnh thiếu bị cảnh báo, không được xem như ảnh mới đã xác minh.
5. `prepare_report()` điền đường dẫn ảnh theo TC. Khi có kết quả nguồn nhưng chưa có ảnh hợp lệ, cột Bằng chứng dùng đường dẫn kết quả tham chiếu nếu TC có execution tương ứng trong nguồn.
6. Nếu có `--media`, `create_media()` trong customer_report_media.py tạo PNG/SVG phân tích BVA, EP và bảng quyết định. Đây là hình phân tích, không phải ảnh UI.
7. `publish_workbook()` trong customer_report_output.py gọi `write_workbook()` để ghi tệp tạm hoàn chỉnh rồi thay workbook đích. Khi đích bị Excel khóa, nó giữ tệp đang mở, xuất tên thay thế và in WARNING cùng đường dẫn mới.

Workbook mặc định là `apps/shuup/reports/customer/customer_test_cases.xlsx`. Kết quả Robot nhập vào được trình bày ở phần truy vết; các cột kết quả nghiệp vụ không tự chuyển thành Đạt chỉ vì có Robot PASS. Báo cáo nói rõ nguồn và phạm vi bằng chứng để người kiểm thử đối chiếu.

Mỗi lượt Robot dùng lại các tên output.xml/log.html/report.html. Thư mục ảnh có run ID riêng; nên xuất report và lưu cả kết quả nguồn sau lượt cần bàn giao trước khi chạy lượt khác. Khi chỉ chạy B09, workbook vẫn có 71 ca, nhưng chỉ B09 có kết quả nguồn mới tương ứng; không được suy ra 51 execution còn lại đã chạy.

## 7. Khi cần thay đổi, sửa ở đâu?

| Việc cần làm | Tệp cần sửa và bước tiếp theo |
| --- | --- |
| Đổi dữ liệu nhập hoặc giá trị biên | CUSTOMER_DESIGN.yaml; sinh lại bằng lệnh customer và xem dữ liệu ca |
| Đổi tên/mô tả tiếng Anh | CUSTOMER_CASE_TEXT.json hoặc phần tiếng Anh CUSTOMER_EXTENSION_TEXT.json |
| Đổi nội dung Excel tiếng Việt | CUSTOMER_EXCEL_TEXT.json hoặc phần tiếng Việt CUSTOMER_EXTENSION_TEXT.json |
| Đổi thao tác/selector Robot | CustomerJourney.py hoặc CustomerExtensions.py; chạy lại lệnh robot để build image và thực hiện ca |
| Đổi xử lý số lượng phía server | storefront/basket.py; setup để build/init/start, sau đó chạy ca liên quan |
| Đổi cách kiểm tra/điền ảnh | customer_evidence.py, customer_report_data.py; chạy ca cần ảnh rồi xuất report |
| Đổi trình bày workbook | customer_report.py hoặc customer_report_layout.py; chạy report với nguồn kết quả đã chọn |

Khi thêm ca, đồng bộ ID nghiệp vụ, ID execution, dữ liệu cụ thể, phân tích và ánh xạ evidence. Xem [thiết kế customer](SHUUP_CUSTOMER_TEST_DESIGN.md) và [YAML](YAML_TEST_DATA.md).

[NAVIGATION](../NAVIGATION.md)
