[NAVIGATION](../NAVIGATION.md)

# 🧭 Chọn quy trình chạy và viết kiểm thử

Mỗi mục là một lựa chọn độc lập. Không cần chạy hết các quy trình. Dùng [COMMANDS](COMMANDS.md) để tra điều kiện, tác động dữ liệu và option; dùng [APPS](../APPS.md) để chọn adapter. Ví dụ dưới đây dùng Windows CMD; PowerShell thêm .\ trước cmdc.cmd, POSIX dùng sh cmdc.

Hồ sơ Excel, nhập kết quả và ảnh BVA/EP/decision: [SHUUP_CUSTOMER_REPORT](SHUUP_CUSTOMER_REPORT.md). Lệnh `cmdc.cmd report --app shuup` luôn xuất Excel; thêm `--media` để tạo PNG/SVG hoặc `--results reports/output.xml` để đưa một lần chạy tự động vào sheet Truy vết. Kết quả ca nghiệp vụ không được suy ra từ ID Robot.

## Chọn mức chuẩn bị

| Tình trạng/mục tiêu | Cách ngắn nhất phù hợp | Vì sao |
| --- | --- | --- |
| Cài mới để thao tác thủ công | setup | Đã bao gồm khởi tạo và start; không cần browser image |
| Cài mới và chạy suite mặc định ngay | setup --run-tests | Một lệnh gộp chuẩn bị app/browser và chạy suite |
| Cài mới, muốn chuẩn bị browser nhưng chạy sau | setup --with-robot (Django/PHP/.NET) | Tách thời gian tải dependency khỏi giờ kiểm thử |
| App đã có, mở lại sau down | start | Không cần migrate/seed lại |
| Django đã có, chỉ muốn chạy suite UI | robot | Đã tự chuẩn bị browser và mở lại web |
| Sửa code/seed/config | setup nếu cần rebuild; validate để kiểm tra nội bộ | Validate đọc app source qua tools mount, không rebuild dependency hoặc web image |
| Sửa model Shuup và chạy ca sinh | robot --design | Tự sinh lại; generate riêng chỉ cần khi muốn xem kế hoạch trước |
| Lỗi chưa biết ở giai đoạn nào | Tách đúng giai đoạn đang cần chẩn đoán | Không chạy lại toàn bộ hoặc xóa dữ liệu chỉ để thu log |

## A. Một lệnh chuẩn bị và chạy suite mặc định

Chọn **một** dòng phù hợp với app:

```bat
cmdc.cmd setup --app shuup --run-tests
```

```bat
cmdc.cmd setup --app pretix --run-tests --accept-pretix-risk
```

```bat
cmdc.cmd setup --app woocommerce --run-tests --accept-resource-risk
```

Thay shuup bằng oscar/wowy, hoặc woocommerce bằng prestashop/nopcommerce khi cần. Setup dừng tại bước lỗi, nên không cần tự thêm kiểm tra exit giữa các bước nội bộ. Suite mặc định có phạm vi riêng theo app và có thể tạo đơn/dữ liệu; xem [TESTING](TESTING.md). Luồng này không tự gọi validate, không nhận --design/--test và không chạy tất cả loại kiểm thử của dự án.

## B. Mở cửa hàng và kiểm thử thủ công

Lần đầu:

```bat
cmdc.cmd setup --app shuup
cmdc.cmd urls --app shuup
```

Setup đã mở web; urls chỉ lấy điểm vào để bạn mở browser. Sau đó đăng nhập từ UI bằng tài khoản trong file cấu hình riêng của app. Khi xong:

```bat
cmdc.cmd down --app shuup
```

Phiên sau, dùng start rồi urls; không cần setup lại. Khi đổi app, down app cũ trước rồi setup/start app mới. Dữ liệu giao dịch không chuyển sang app mới.

## C. Chạy UI có sẵn trên app đã khởi tạo

Django (Oscar/Shuup/Wowy), chọn một:

```bat
cmdc.cmd robot --app shuup
```

```bat
cmdc.cmd robot --app shuup --test "*Customer Opens*"
```

```bat
cmdc.cmd robot --app shuup --include smoke
```

Robot tự build browser có cache và bảo đảm web chạy. Không cần gọi robot-init/start trước từng lượt. Nếu muốn chuẩn bị browser trước, có thể chạy robot-init từ trước; đây là lựa chọn bố trí công việc, không phải điều kiện bổ sung.

PHP/.NET: nếu web đã chạy sau setup, chỉ dùng robot với cờ xác nhận tải. Nếu đã down, cần start trước vì adapter robot không tự mở web:

```bat
cmdc.cmd start --app woocommerce --accept-resource-risk
cmdc.cmd robot --app woocommerce --accept-resource-risk
```

Nhóm này chỉ hỗ trợ smoke mặc định, không nhận --dryrun/--test/--include. Pretix nhận bộ lọc Robot và cần --accept-pretix-risk cho mỗi lượt có tải.

## Chạy customer Shuup từ đăng ký tới lịch sử đơn

Cài mới và chạy đủ bộ customer trong một lệnh:

```bat
cmdc.cmd setup --app shuup --run-tests --customer
```

App đã khởi tạo: dùng robot --app shuup --customer; generate --customer là lựa chọn duyệt kế hoạch trước. Chạy riêng hành trình bằng --customer-stage e2e; chọn ca theo ID bằng --customer-case "SH-CUST-Q*". Bộ lọc này áp vào CSV trước DataDriver, thay cho --test/--include của Robot trong mode customer. Không dùng --customer của setup nếu thiếu --run-tests.

Bảng 22 ca, giá trị, BVA/EP/decision và độ phủ thiết kế tại [SHUUP_CUSTOMER_TEST_DESIGN](SHUUP_CUSTOMER_TEST_DESIGN.md); giải thích từng selector/keyword/Python tại [SHUUP_CUSTOMER_TEST_CODE](SHUUP_CUSTOMER_TEST_CODE.md). Luồng này tạo tài khoản/đơn local, giữ activation và COD native. Suite --design bên dưới là nghiệp vụ ví riêng.

## D. Sinh ca theo model Shuup: chạy ngay hoặc duyệt trước

Chuẩn bị app bằng setup nếu chưa có. Sửa apps/shuup/tests/data/WALLET_DESIGN.yaml hoặc thêm model trong cùng thư mục. Chọn một trong hai cách:

**Chạy ngay:**

```bat
cmdc.cmd robot --app shuup --design
```

Lệnh tự sinh model/CSV/suite rồi chạy UI. Không cần generate trước.

**Duyệt kế hoạch trước:**

```bat
cmdc.cmd generate --app shuup
```

Mở apps/shuup/reports/design/coverage.json, cases.csv và model.json. Kiểm tra expected, số ca, nghĩa vụ bị loại và độ phủ. Sau khi chốt model, chạy robot --design. Lệnh này sinh lại cùng model, nên model là nguồn cần quản lý; chỉnh trực tiếp CSV sinh không phải cách duy trì dữ liệu của luồng này.

Dùng model khác:

```bat
cmdc.cmd robot --app shuup --design --design-model tests/data/MY_MODEL.json
```

Có thể thêm --dryrun để kiểm tra cấu trúc trước, nhưng không bắt buộc thêm một lượt dryrun cho mỗi lần chạy thật. Dryrun vẫn nạp DataDriver/Browser và có thể lỗi runtime; đọc cả mã thoát và Test Execution Errors. Ý nghĩa BVA, EP, bảng quyết định, single fault và giảm ca tại [AUTOMATED_TEST_DESIGN](AUTOMATED_TEST_DESIGN.md).

## E. Viết hoặc sửa kiểm thử

### Chọn dữ liệu hay hành trình

| Thay đổi cần làm | Nơi sửa | Cách chạy sau khi sửa |
| --- | --- | --- |
| Thêm biên/phân vùng/rule cho form Shuup đã có binding | tests/data/model JSON | robot --design; generate tùy chọn để duyệt |
| Kiểm thử một form mới bằng model | Model: field, condition, binding selector, setup và oracle | robot --design --design-model tests/data/MY_MODEL.json |
| Hành trình nhiều trang hoặc thao tác ngoài runner model | tests/robot/*.robot và resource của app | robot với --test/--include tương ứng |
| Thêm regression backend/seed/quyền truy cập | tests/cli hoặc tests/integration của app | validate sau khi image chứa code mới |
| Chỉ tạo bộ dữ liệu legacy Oscar/Wowy/Pretix | tests/data/INPUT_MODEL.json | generate; sau đó tự nối CSV vào test template/keyword/assertion |

Model chỉ tự động hóa dữ liệu sau khi có đặc tả và binding; nó không tự suy ra hành trình/oracle từ website. Với legacy, generate không tự tạo suite UI dùng được. Không đánh đồng file CSV xuất thành công với test đã chạy.

### Quy trình viết test UI

1. Chọn yêu cầu và hành trình từ [JOURNEYS](JOURNEYS.md) hoặc hồ sơ app; xác định đầu vào, expected và dữ liệu sẽ thay đổi.
2. Duyệt luồng native bằng browser từ trang khởi đầu; ghi selector ổn định cho control thật. Bước sau dùng link/nút/form của UI.
3. Khai báo keyword dùng lại, Test Setup/Teardown hoặc binding model; đưa secret qua biến môi trường đã có, không ghi vào model/test.
4. Chọn ca/tag cần chạy. Dryrun là lựa chọn kiểm tra cấu trúc nhanh, hữu ích khi sửa keyword/import; chạy thật mới xác nhận hành vi.
5. Đọc output.xml, log.html và ảnh lỗi trong reports; đối chiếu assertion với đặc tả. Với test ghi dữ liệu, chọn tài khoản/trạng thái ban đầu phù hợp lần chạy tiếp theo.

Thư mục tests/data và tests/robot của adapter Django được mount vào browser container; sửa model/suite có thể chạy robot ngay. Source Python, settings, requirements hoặc file COPY vào image cần rebuild bằng setup trước khi xác nhận. Kiểm tra compose của adapter khi sửa vị trí ngoài các mount này. Validate của Django đọc thư mục app qua tools mount, nên có thể kiểm tra source mới với dependency cũ; source web và test-design COPY vào image cần rebuild để đối chiếu đúng phiên bản.

### Chọn chạy gọn hay chia giai đoạn khi sửa code

- Cần cửa hàng cùng suite mặc định: setup --run-tests.
- Cần kiểm tra backend trước UI: setup → validate → robot. Việc tách tạo điểm dừng khi regression nội bộ lỗi; không phải yêu cầu cho mọi phiên kiểm thử.
- Cần chạy ca model hoặc test chọn lọc: setup → robot với --design/--test; thêm validate nếu thay đổi ảnh hưởng code/config.
- Chỉ sửa test/model đã mount: robot với tùy chọn tương ứng; không cần setup lại.

## F. Ghép nhiều kiểm tra trong một lần gọi shell

CMDC chưa có lệnh tổng hợp gọi validate rồi Robot. Nếu cần cả hai và app đã được setup, CMD/POSIX có thể nối bằng && để chỉ chạy bước sau khi bước trước thành công:

```bat
cmdc.cmd validate --app shuup && cmdc.cmd robot --app shuup
```

Windows PowerShell 5.1 không hỗ trợ &&. Dùng kiểm tra mã thoát:

```powershell
.\cmdc.cmd validate --app shuup
if ($LASTEXITCODE -eq 0) { .\cmdc.cmd robot --app shuup }
```

PowerShell 7 hỗ trợ &&. Không dùng dấu ; để giả định bước sau sẽ dừng khi bước trước lỗi. Không chạy song song các tác vụ app vì khóa vận hành và dữ liệu kiểm thử cần tuần tự.

## G. Sao lưu, thay source và khôi phục

Trước thay đổi có thể ảnh hưởng dữ liệu, backup là lựa chọn bảo vệ trạng thái, không phải bước bắt buộc mỗi lần chạy UI:

```bat
cmdc.cmd backup --app shuup before-update
```

Lưu .env riêng an toàn. Cập nhật source, giữ dữ liệu hiện có, rồi setup để rebuild/migrate/seed và mở lại. Backup dừng writers; nếu chỉ backup mà chưa cập nhật, dùng start để tiếp tục.

Khi thực sự cần quay lại backup:

```bat
cmdc.cmd restore --app shuup before-update --yes
cmdc.cmd start --app shuup
```

Restore thay database/media và để writers dừng, vì cần có điểm kiểm tra trước khi phục vụ lại. Down chỉ dừng/gỡ container; reset/destroy xóa dữ liệu theo [COMMANDS](COMMANDS.md). Không đưa reset/destroy vào quy trình chạy test thông thường.

## Theo dõi một lượt customer cụ thể

Xem [đường đi từ lệnh CMD](SHUUP_CUSTOMER_EXECUTION.md), [từng dòng Robot và hàm Python](SHUUP_CUSTOMER_ROBOT_WALKTHROUGH.md), cùng [luồng dữ liệu và ảnh](SHUUP_CUSTOMER_DATA_FLOW.md). Ví dụ xuyên suốt là chạy toàn bộ customer và chọn riêng SH-CUST-B09.

[NAVIGATION](../NAVIGATION.md)
