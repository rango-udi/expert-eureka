[NAVIGATION](../NAVIGATION.md)

# ⌨️ Tra cứu lệnh CMDC

Chọn quy trình theo mục tiêu tại [WORKFLOWS](WORKFLOWS.md); trang này giải thích hợp đồng của từng lệnh. Đọc tên lệnh cùng phạm vi adapter: một lệnh được hỗ trợ ở nhiều app có thể gọi các công cụ native khác nhau.

Tra theo việc: [cú pháp](#cú-pháp-và-cách-đọc-ví-dụ), [chọn nhanh](#chọn-nhanh), [hỗ trợ và alias](#phạm-vi-hỗ-trợ-và-tên-đồng-nghĩa), [hệ thống](#lệnh-hệ-thống-không-thêm---app), [vòng đời](#chuẩn-bị-và-vòng-đời), [validate](#validate), [generate](#generate), [Robot](#robot), [quan sát/cấu hình](#quan-sát-và-cấu-hình), [dữ liệu](#sao-lưu-phục-hồi-và-xóa).

## Cú pháp và cách đọc ví dụ

Chạy từ root đã giải nén đầy đủ. Mỗi tác vụ ứng dụng cần đúng một `--app`; ID lấy bằng `apps --ids`. Launcher không nhớ app của lệnh trước.

| Shell | Ví dụ có thể chạy |
| --- | --- |
| Windows CMD | `cmdc.cmd setup --app shuup` |
| Windows PowerShell | `.\cmdc.cmd setup --app shuup` |
| Linux/macOS, shell POSIX | `sh cmdc setup --app shuup` |

Các khối `bat` dưới đây dùng CMD. Với PowerShell thay `cmdc.cmd` bằng `.\cmdc.cmd`; với POSIX thay bằng `sh cmdc`. `<id>`, `<name>`, `<scope>` là chỗ cần thay, không gõ nguyên dấu ngoặc. Dấu `[...]` nghĩa là tùy chọn, không phải ký tự cần nhập. Giá trị có khoảng trắng phải đặt trong dấu nháy kép.

```text
cmdc <command> --app <id> [arguments and options]
cmdc <global-command> [options]
```

## Chọn nhanh

| Tôi muốn… | Lệnh | Điều kiện/kết quả |
| --- | --- | --- |
| Mở cửa hàng lần đầu | `setup --app shuup` | Chuẩn bị app và khởi động luôn |
| Chuẩn bị và chạy suite mặc định bằng một lệnh | `setup --app shuup --run-tests --customer` | Chọn suite customer đầy đủ của Shuup thay smoke; --customer cần đi cùng --run-tests |
| `setup --app shuup --run-tests` | Bao gồm browser; suite có thể thay đổi dữ liệu kiểm thử |
| Mở lại cửa hàng đã khởi tạo | `start --app shuup` | Giữ database; cần image và cấu hình hiện có |
| Chạy browser với app Django đã khởi tạo | `robot --app shuup` | Tự build browser, bảo đảm web chạy rồi thực thi suite |
| Xuất Excel customer; tùy chọn ảnh/kết quả | `report --app shuup --media --results reports/output.xml` | Excel luôn có; chỉ đọc lần chạy đã tồn tại |
| Kiểm tra code/config và regression nội bộ | `validate --app shuup` | Xem phạm vi cụ thể bên dưới; không mở browser |
| Sinh và chạy ca theo model Shuup | `robot --app shuup --design` | Sinh lại rồi chạy UI trong cùng một lệnh |
| Chỉ xem ca sinh trước khi chạy | `generate --app shuup` | Ghi artifacts, không thực thi ca |
| Dừng và giữ dữ liệu | `down --app shuup` | Gỡ container/network; lần sau dùng start |
| Xem lỗi khởi tạo khi Docker không chạy | `diagnostics --app shuup` | Đọc log backend cục bộ, giới hạn 120 dòng/file |

Các ví dụ trên dùng Shuup. Nhóm PHP/.NET có điều kiện chạy Robot khác; xem bảng hỗ trợ và mục Robot. Các ví dụ là lựa chọn theo nhu cầu, không phải danh sách phải chạy hết.

## Phạm vi hỗ trợ và tên đồng nghĩa

| Chức năng | Oscar, Shuup, Wowy | Pretix | nopCommerce, PrestaShop, WooCommerce |
| --- | --- | --- | --- |
| setup, start, stop, down, init | Có | Có | Có |
| validate | Django, unit/integration, source/docs | Compose, unit, cú pháp, source/docs | Cấu hình môi trường, dữ liệu chung, hash ảnh |
| robot | Suite UI riêng của app | Suite UI vé/sự kiện | Smoke cửa hàng chỉ đọc |
| robot với `--dryrun` hoặc bộ lọc Robot | Có | Có | Không nhận tùy chọn Robot |
| generate | Có; Shuup có model mới | CSV generator cũ | Không hỗ trợ |
| report | Chỉ Shuup: Excel; tùy chọn media/kết quả | Không hỗ trợ | Không hỗ trợ |
| backup, restore, reset, manage | Có | Có | Không hỗ trợ |
| env show | Có, che secret được khai báo | Có, che secret | Không hỗ trợ; đọc file riêng cục bộ |
| pull | Không hỗ trợ | Có | Không hỗ trợ |
| source | Đọc đường dẫn/khóa nguồn | Tải checkout nguồn khóa | Đọc source-lock |
| versions | Đọc package đã cài | Ghi báo cáo image/runtime | Đọc source-lock |

`bootstrap` là tên tương thích của `setup` trên mọi adapter; dùng `setup` trong hướng dẫn mới. `up` là tên tương thích của `start`. Không chạy lần lượt hai tên đồng nghĩa. `restart` thực sự dừng rồi mở lại nên khác `start`. Trong nhóm PHP/.NET, `source` và `versions` hiện cùng in source-lock; giữ hai điểm vào để tương thích giao diện CLI, không cần gọi cả hai.

## Lệnh hệ thống: không thêm --app

| Lệnh | Hành vi thực tế và cách dùng |
| --- | --- |
| `help` | In tóm tắt cú pháp và nơi tra cứu, dùng offline. `-h` và `--help` là tên tương đương của lệnh này. |
| `apps` | In bảng ID và tên từ registry cục bộ; không gọi Docker. |
| `apps --names` | Chỉ in tên hiển thị, mỗi dòng một app. Dùng `--ids` khi cần giá trị cho --app. |
| `apps --ids` | Chỉ in ID hợp lệ, mỗi dòng một app; phù hợp script chọn app. |
| `apps --raw` | In registry nguyên dạng gồm comment và các cột phân cách bằng `\|`; dành cho đọc cấu hình. |
| `version` | In VERSION của bộ công cụ; khác versions của app. Dùng offline. |
| `doctor` | Kiểm tra Docker Engine Linux, phiên bản Compose và RAM engine theo chính sách chung. Không kiểm tra checkout, sức khỏe nghiệp vụ hay chạy Robot; không tự chỉnh RAM. |
| `wsl-vm-limit-help` | Hiển thị/mở hướng dẫn cấu hình WSL; không tự thay cấu hình VM. Dùng offline. |

`help --app shuup` vẫn là trợ giúp root, không phải trợ giúp chi tiết của Shuup. Đọc [hồ sơ ứng dụng](../APPS.md) và trang này để chọn option. `host-memory` và `lock` trong nguồn adapter Pretix cũ không được dispatcher root công bố; không dùng chúng như lệnh CMDC hiện hành. Cấu hình VM theo [WSL_VM_MEMORY_LIMIT](../helps/WSL_VM_MEMORY_LIMIT.md).

## Chuẩn bị và vòng đời

### setup

Dùng khi cài lần đầu hoặc sau khi cập nhật source cần rebuild/migration/seed. Setup chuẩn bị cấu hình, image, khởi tạo native và khởi động cửa hàng. Thành công nghĩa là bước khởi tạo và readiness đã qua; không có nghĩa bộ kiểm thử chức năng đã chạy.

| Cách gọi | Kết quả thêm vào setup cơ bản |
| --- | --- |
| `setup --app shuup` | Chỉ chuẩn bị app và mở cửa hàng; chưa build browser |
| `setup --app shuup --with-robot` | Chuẩn bị thêm browser image để dùng sau; chưa chạy suite |
| `setup --app shuup --run-tests --customer` | Chọn suite customer đầy đủ của Shuup thay smoke; --customer cần đi cùng --run-tests |
| `setup --app shuup --run-tests` | Chuẩn bị browser và chạy suite mặc định sau khi web sẵn sàng; không tự gọi validate |
| `setup --app pretix --run-tests --accept-pretix-risk` | Luồng gọn tương ứng của Pretix; không nhận --with-robot |
| `setup --app woocommerce --run-tests --accept-resource-risk` | Cài native, mở web và chạy smoke chỉ đọc |

Không cần thêm `--with-robot` khi đã có `--run-tests`. Setup không nhận `--test`, `--dryrun` hay `--design`; muốn chọn suite/test, dùng setup rồi robot với option tương ứng. Pretix mặc định không tải checkout nguồn; `--skip-source` là option tương thích đã trùng hành vi mặc định. Muốn đọc nguồn Pretix, dùng source riêng.

Setup chạy lại giữ cấu hình và bản ghi đã có theo quy tắc seed của app, nhưng vẫn thực hiện migration/bổ sung dữ liệu và có thể dừng web trong lúc bảo trì. Đây không phải cách nhanh nhất để mở lại app hằng ngày; dùng start. Build có thể dùng cache, vẫn cần kho image/package cho phần chưa có. Khi lỗi, giữ .env/database/volume và đọc diagnostics trước khi thử lại.

### init

Chạy khởi tạo với image đã có, khi chỉ cần migration/seed hoặc chuẩn bị lại tài nguyên dữ liệu. Django: dừng web, migrate, seed, collectstatic; Oscar/Shuup còn dựng chỉ mục tìm kiếm; kết thúc để web dừng, gọi start khi muốn mở lại. Pretix: chạy migrate/seed qua các dịch vụ hỗ trợ. PHP/.NET: xác thực dữ liệu, chạy installer/seed cần thiết rồi đưa web tới readiness. Init không thay cho setup khi thiếu image hoặc source đã thay mà image chưa rebuild.

```bat
cmdc.cmd init --app shuup
cmdc.cmd start --app shuup
```

Hai dòng được tách để người vận hành xem kết quả khởi tạo trước khi mở web. Khi cần toàn bộ quá trình tự động, dùng một lệnh setup.

### start

Khởi động app đã chuẩn bị và chờ readiness. Django không tự build, migrate hay seed; PHP/.NET yêu cầu marker khởi tạo thành công và khởi động database trước web. Pretix khởi động các dịch vụ theo cấu hình và cấp lại endpoint khi cần. Lấy URL hiện tại bằng urls; không giả định cổng cũ của Django/Pretix còn hiệu lực sau down.

### up

Tên tương thích có cùng hành vi với start. Chọn một tên; không có bước bổ sung cần chạy sau start.

### restart

Dừng rồi gọi luồng start. Dùng để khởi động lại process với cấu hình runtime phù hợp; không rebuild image hoặc migrate. Với source/dependency thay đổi cần rebuild, dùng setup.

### stop

Dừng container của app, giữ container/network, database, media và cấu hình. Hợp với tạm dừng trong cùng phiên. Pretix còn có chọn dịch vụ theo bảng bên dưới. Dùng down trước khi chuyển app để gỡ network/container cũ.

### down

Dừng và gỡ container/network của đúng app; giữ image, .env và dữ liệu. Gọi start để mở lại. Down không phải reset database. Nếu công việc bị ngắt và còn one-off/khóa, xử lý theo [APP_LIFECYCLE](APP_LIFECYCLE.md), không xóa khóa khi tác vụ còn chạy.

## Kiểm tra, sinh ca và chạy browser

### validate

Tên validate ở đây nghĩa là **chạy bộ kiểm tra nội bộ được adapter đăng ký**, không phải một phép thử UI chung cho mọi app. Lệnh dừng khi một bước trả lỗi; các bước trước PASS không làm cả lệnh thành công. Mã thoát 0 chỉ xác nhận các kiểm tra trong phạm vi sau:

| App | Các bước theo thứ tự triển khai |
| --- | --- |
| oscar | Django check → unit CLI → Django integration (database test) → kiểm tra tài liệu → kiểm tra source |
| shuup | Django check → kiểm tra thiếu migration của storefront (check/dry-run, không tạo migration) → unit CLI → unit test-design → Django integration (database test) → tài liệu → source |
| wowy | Django check → kiểm tra thiếu migration của storefront → unit CLI → Django integration (database test) → tài liệu → source |
| pretix | Compose config → unit CLI → biên dịch kiểm tra cú pháp Python → tài liệu → source; Windows còn gọi py_compile cho configuration.py |
| Nhóm PHP/.NET | Tạo/kiểm tra .env nếu cần → build tools → kiểm tra giá trị cấu hình, profile, bản ghi/tham chiếu và checksum ảnh chung |

Django validate cần app image đã có, nhưng không cần storefront đang chạy; không tự build image hoặc seed cửa hàng. Tools mount thư mục app từ host nên đọc source/test hiện tại; dependency và test-design trong image vẫn theo lần build trước. Web dùng source COPY trong image nên kết quả validate không chứng minh web đã nhận source mới. Test integration tạo/xóa database test, có thể mất thời gian ở dòng Creating/Destroying test database. Công cụ cũng có thể hoàn thiện cấu hình thiếu và ghi log/runtime. PHP/.NET validate có thể chuẩn bị helper/tools image và .env nên không phải kiểm tra tĩnh thuần túy hay lệnh offline.

Validate không chạy Robot, không xác nhận browser/checkout trên website đang mở, không tự sửa code hoặc dữ liệu và không sinh suite để chạy UI. Checker source/tài liệu có phạm vi toàn repository; vì vậy validate một app vẫn có thể báo lỗi tài liệu dùng chung hoặc source app khác. Xem [TESTING](TESTING.md) để phân biệt bằng chứng và lỗi runtime.

```bat
cmdc.cmd validate --app shuup
```

Chọn validate khi sửa code/config/seed hoặc chuẩn bị bàn giao; có thể bỏ bước này trong một phiên chỉ cần mở cửa hàng hoặc chạy lại UI đã chọn.

### generate

Chỉ sinh dữ liệu/kế hoạch ca; không mở browser và không áp các giá trị sinh vào app. Cần image công cụ hiện có đối với Django/Pretix. Các artifact được ghi lại khi chạy cùng đầu ra.

| Adapter/cách gọi | Đầu vào trên host | Đầu ra trong thư mục app |
| --- | --- | --- |
| Shuup: `generate --app shuup --customer` | tests/data/CUSTOMER_DESIGN.yaml và records dùng chung | reports/customer: test_cases.csv, test_cases.md, execution_cases.csv, robot_transport.csv, model.json, coverage.json, run.robot |
| Shuup: `generate --app shuup` | tests/data/WALLET_DESIGN.yaml | reports/design/model.json, cases.csv, coverage.json, run.robot |
| Shuup: `generate --app shuup --design-model tests/data/MY_MODEL.json` | Model tùy chọn trong apps/shuup/tests/data | reports/design với cùng các artifact |
| Shuup: `generate --app shuup --legacy` | tests/data/INPUT_MODEL.json | reports/generated_cases.csv và case_generation_summary.json |
| Oscar, Wowy, Pretix: `generate --app <id>` | tests/data/INPUT_MODEL.json của app | reports/generated_cases.csv và case_generation_summary.json |

Đường dẫn `--design-model` được hiểu trong container, tương đối với /app của Shuup. Đặt model trong apps/shuup/tests/data rồi truyền tests/data/tên-file.json. Không truyền đường C:\… vào container. CSV legacy là dữ liệu để nối vào keyword/assertion; chạy robot mặc định không tự tiêu thụ CSV này. Shuup `robot --design` tự sinh lại trước khi chạy nên generate riêng là tùy chọn khi muốn xem xét kế hoạch. Kỹ thuật và giới hạn độ phủ tại [AUTOMATED_TEST_DESIGN](AUTOMATED_TEST_DESIGN.md).

### report

Chỉ Shuup hỗ trợ. `report --app shuup` build runtime báo cáo riêng rồi xuất Excel vào apps/shuup/reports/customer/customer_test_cases.xlsx. Không cần setup cửa hàng trước để chỉ xuất thiết kế; cần Docker/Compose và source đầy đủ. `--media` thêm PNG/SVG và hình phân tích nhúng. Mặc định đọc reports/output.xml nếu có; `--results reports/output.xml` chọn nguồn cụ thể tính từ app, không chạy lại Robot. Bằng chứng đã xác minh được điền theo từng TC; kết quả nhập giữ vai trò tham chiếu và không tự gán kết quả nghiệp vụ mới. Report ghi hoàn chỉnh trước khi thay đích. Nếu Excel khóa tệp mặc định, lệnh lưu tên riêng cùng thư mục và in WARNING/đường dẫn thực tế; nếu vẫn không lưu được thì báo ERROR và trả mã lỗi. Chạy report sau Robot kể cả khi suite FAIL. Xem [SHUUP_CUSTOMER_REPORT](SHUUP_CUSTOMER_REPORT.md) để tra cột, liên kết ảnh và cách xử lý tệp đang mở.

### robot-init

Django và PHP/.NET: build image browser/Chromium. Pretix: root chuyển lệnh thành pull robot. Không chạy suite, không chứng minh browser kết nối ứng dụng thành công. Dùng khi muốn chuẩn bị dependency trước giờ kiểm thử hoặc kiểm tra lỗi build riêng. Không bắt buộc chạy trước robot vì robot đã build/pull browser cần thiết.

### robot

Chạy Robot Framework và ghi report/log/output vào apps/<id>/reports. Mặc định dùng suite tests/robot của app; thành công chỉ bao phủ các test được chọn. Lệnh không tự chạy validate.

| Adapter | Việc chuẩn bị trước khi thực thi |
| --- | --- |
| Oscar, Shuup, Wowy | Build browser image (có cache); chạy start trừ khi có đúng option --dryrun; yêu cầu app đã được setup |
| Pretix | Pull browser nếu thiếu; bảo đảm stack chạy khi không dryrun |
| PHP/.NET | Yêu cầu marker và cửa hàng đang chạy; build browser rồi chạy smoke; không tự start web và không nhận thêm option |

Với PHP/.NET đã down, chạy start trước robot; hoặc dùng setup --run-tests nếu cần khởi tạo và chạy trọn luồng một lần. Với Django, robot sau down có thể tự mở lại app đã có database/image.

```bat
cmdc.cmd robot --app shuup
cmdc.cmd robot --app shuup --dryrun
cmdc.cmd robot --app shuup --test "*Customer Opens*"
cmdc.cmd robot --app shuup --include smoke
cmdc.cmd robot --app shuup --design
cmdc.cmd robot --app shuup --design --design-model tests/data/WALLET_DESIGN.yaml
```

Mỗi dòng là một lựa chọn. `--test` khớp tên test, `--include` khớp tag thực sự có trong suite; xem danh sách tại [TESTING](TESTING.md). `--dryrun` kiểm tra cấu trúc/keyword, không thực hiện hành trình, nhưng vẫn nạp library/listener và cần runtime phù hợp. PASS của dryrun không xác nhận chức năng UI. `--customer` của Shuup chọn bộ đăng ký→mua ba sản phẩm→lịch sử đơn, tự sinh reports/customer. Dùng --customer-case "SH-CUST-Q*" hoặc --customer-stage e2e để lọc trước khi DataDriver sinh test; không dùng --test/--include/--exclude của Robot trong mode này. Không ghép --customer với --design. Thiết kế và bảng ca tại [SHUUP_CUSTOMER_TEST_DESIGN](SHUUP_CUSTOMER_TEST_DESIGN.md). `--design` và `--design-model` chỉ được Shuup xử lý; --design-model phải đi cùng --design. Suite chạy thật có thể tạo đơn, thay tồn kho hoặc cộng ví; database không tự reset giữa các lần chạy.

## Quan sát và cấu hình

| Lệnh | Hành vi, giới hạn và kết quả |
| --- | --- |
| `status --app shuup` | Xem trạng thái container Compose; không chứng minh checkout hoạt động. Pretix dùng ps -a và gồm service profile tools. |
| `urls --app shuup` | In endpoint hiện tại; không mở browser. Django lấy cổng đang publish; PHP/.NET dùng HTTP_PORT đã lưu; Pretix đồng bộ endpoint. Oscar in host:port, Shuup/Wowy in link có nhãn. |
| `resources --app shuup` | Snapshot RAM/CPU container; không phải RAM toàn VM/Windows. Pretix hỗ trợ --watch để theo dõi liên tục. |
| `logs --app shuup` | In đuôi log container: Django 100 dòng web; PHP/.NET 100 dòng app/db; Pretix 150 dòng và có thể chọn service. Không theo dõi liên tục bằng -f qua CLI này. |
| `diagnostics --app shuup` | Đọc log backend đã lưu trên host, không cần Docker; che giá trị secret đã cấu hình và lấy 120 dòng cuối/file. Có thể chứa log cũ hoặc không có log cho bước hiện tại; kiểm tra nội dung trước khi chia sẻ. |
| `env --app shuup init` | Django build app image rồi hoàn thiện .env; không migrate/start. Pretix/PHP/.NET dùng helper tạo cấu hình. Bare env tương đương env init; giữ giá trị hiện có. |
| `env --app shuup show` | Django/Pretix in cấu hình với secret đã khai báo được che; Django vẫn đi qua build app image và công cụ cấu hình. Không phải đọc file offline. PHP/.NET từ chối show. |
| `config --app shuup` | Django in Compose đã nội suy nên có thể chứa secret, cần giữ riêng. PHP/.NET dùng --no-interpolate. Pretix in cấu hình vận hành qua helper. Không sửa cấu hình hay tự xác minh UI. |
| `manage --app shuup check` | Truyền đối số sang Django trong container. Django adapter dừng web trước khi chạy và không tự mở lại; dùng start khi xong. Pretix khởi động postgres/redis rồi gọi worker với đối số quản trị. PHP/.NET không hỗ trợ. |
| `source --app shuup` | Django in đường dẫn upstream trong image và source-lock; không tải checkout. Pretix tải checkout commit khóa để đọc mã, có thể cần image git/mạng. PHP/.NET in source-lock cục bộ. |
| `versions --app shuup` | Django in phiên bản package đã cài, cần app image. Pretix ghi evidence image/runtime và có thể chạy worker để truy vấn phiên bản. PHP/.NET in nguồn khóa, không truy vấn bản thực tế đang chạy. |
| `pull --app pretix server` | Chỉ Pretix: chuẩn bị image server còn thiếu; mặc định server. Chọn robot cho browser, all cho cả server/browser/git. Không migrate/seed/start; khác setup. |

### Tùy chọn dịch vụ riêng của Pretix

`start`, `up`, `restart`, `stop` nhận tối đa một tên dịch vụ hoặc `all` (mặc định). Các tên được nhận: postgres, redis, mailpit, gateway, pretix, worker, periodic. Chọn pretix khi stop áp dụng toàn stack; chọn pretix/worker/periodic khi start có thể mở thêm các dịch vụ hỗ trợ, không phải chỉ một container. `logs` nhận danh sách các tên này và robot. `down` không nhận tên dịch vụ. Trình khởi động có thứ tự/phụ thuộc riêng; dùng lựa chọn thành phần khi chẩn đoán hoặc giảm tải, không cần tách dịch vụ để dùng thông thường. Profile periodic=manual có thể giữ scheduler dừng dù chọn all.

## Sao lưu, phục hồi và xóa

### backup

```bat
cmdc.cmd backup --app shuup before-change
```

Django dừng web rồi ghi SQLite/media vào apps/<id>/backups/before-change.zip; không ghi đè tên đã có. Pretix dừng writers (pretix/worker/periodic), chạy database cần cho pg_dump và lưu backups/before-change/database.dump cùng data.tar.gz. Writers vẫn dừng sau backup; gọi start khi cần tiếp tục. .env không nằm trong bản backup này: lưu cấu hình riêng an toàn. PHP/.NET dùng công cụ sao lưu native theo [NATIVE_COMMERCE](NATIVE_COMMERCE.md).

### restore

```bat
cmdc.cmd restore --app shuup before-change --yes
cmdc.cmd start --app shuup
```

Thay database/media bằng backup tin cậy cùng app; dữ liệu mới hơn có thể bị ghi đè/mất. Django kiểm tra đường dẫn archive, phục hồi và migrate; Oscar/Shuup dựng lại index. Pretix phục hồi PostgreSQL/data và xóa Redis. Không tự mở lại writers. Tách start để có điểm kiểm tra kết quả phục hồi; không chạy setup trước restore chỉ để mở cửa hàng. Cần source/image tương thích và .env phù hợp; tên backup chỉ dùng chữ Anh, số, dấu gạch nối hoặc gạch dưới.

### reset

Chỉ Django/Pretix. Luôn cần scope và --yes; lệnh này xóa dữ liệu, không tự seed lại.

| App | Scope | Phạm vi xóa |
| --- | --- | --- |
| Django | db | SQLite và các file db.sqlite3*; giữ media và reports |
| Oscar | cache | Chỉ index tìm kiếm .runtime/data/search; web đã dừng |
| Shuup/Wowy | cache | Không hỗ trợ |
| Django | data | .runtime/data và reports; giữ .env, backups, image |
| Django | all | Cùng hành vi với data trong adapter hiện tại; giữ tên tương thích |
| Pretix | db | Down stack, xóa volume postgres_data; giữ volume khác |
| Pretix | cache | Down stack, xóa volume redis_data |
| Pretix | data | Down stack và tất cả data volume; giữ image |
| Pretix | all | Down stack, data volume và image thuộc Compose project |

Sau reset db/data/all, dùng setup để khởi tạo và mở lại, hoặc init rồi start nếu image còn và muốn kiểm tra từng giai đoạn. Oscar reset cache chỉ cần init để dựng lại index rồi start. Không dùng reset để sửa lỗi kết nối/khóa/thiếu dependency khi dữ liệu cần giữ.

### destroy

```bat
cmdc.cmd destroy --app shuup --yes
```

| Adapter | Mặc định --yes | Thêm --include-files |
| --- | --- | --- |
| Django | Gỡ container/network, xóa .runtime/data và reports, gỡ image Compose; giữ .env, backups, log ngoài data | Xóa thêm .env và backups |
| Pretix | Tương đương reset all; giữ file cục bộ như .env/reports/backups | Xóa thêm file sinh cục bộ, checkout upstream, evidence của app, .env, reports, backups và runtime |
| PHP/.NET | Gỡ container/network/volume, xóa marker; giữ image cache, .env, log, reports, backups | Xóa thêm .env, reports, backups |

Các phạm vi khác nhau: không suy từ destroy một app sang app khác. Django destroy cần app image hiện có để chạy công cụ cleanup; PHP/.NET destroy không tải image và hỗ trợ cleanup sau setup lỗi/mất .env. Dữ liệu xóa không phục hồi bằng start; dùng backup nếu cần giữ trước khi xác nhận. Root source và nguồn dữ liệu dùng chung được giữ. Khi cleanup lỗi, đọc thông báo bước thất bại trước khi chạy lại.

## Xác nhận, lỗi và hiển thị

Pretix dùng prompt gõ pretix hoặc --accept-pretix-risk cho mỗi tác vụ tạo tải. PHP/.NET dùng prompt gõ đúng ID hoặc --accept-resource-risk. Chấp thuận tải độc lập với --yes của thao tác xóa. Chọn cờ theo app, không ghép hai cờ. Chi tiết tại [PRETIX_RESOURCE_PRESSURE](../helps/PRETIX_RESOURCE_PRESSURE.md) và [NATIVE_COMMERCE](NATIVE_COMMERCE.md).

Các tác vụ ứng dụng thường cần Docker kể cả khi chỉ đọc config/source; ngoại lệ offline rõ ràng là diagnostics. Chỉ một tác vụ thay đổi tài nguyên được phép giữ khóa; không ghép validate/robot đồng thời trong cùng workspace. Engine policy và ownership vẫn được kiểm tra trước adapter.

Terminal tương tác dùng màu, spinner và thời gian ở mép phải. Django validate/generate/robot giữ log trực tiếp cùng progress; build/pull dùng tiến độ Docker. Pipe/CI hoặc CMDC_UI=plain dùng văn bản. Mã thoát khác 0 là thất bại; đọc tên bước và diagnostic trước, không kết luận thành công từ một đoạn OK giữa luồng. Quy trình giữ dữ liệu tại [OPERATIONS](OPERATIONS.md) và [APP_LIFECYCLE](APP_LIFECYCLE.md).

[NAVIGATION](../NAVIGATION.md)
