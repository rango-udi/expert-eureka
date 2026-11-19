[NAVIGATION](../NAVIGATION.md)

# 🧪 Kiểm thử

Hồ sơ Excel, nhập kết quả và ảnh BVA/EP/decision: [SHUUP_CUSTOMER_REPORT](SHUUP_CUSTOMER_REPORT.md). Lệnh `cmdc.cmd report --app shuup` luôn xuất Excel; thêm `--media` để tạo PNG/SVG hoặc `--results reports/output.xml` để đưa một lần chạy tự động vào sheet Truy vết. Kết quả ca nghiệp vụ không được suy ra từ ID Robot.

## Chọn kiểm tra theo câu hỏi

Không phải mọi phiên đều cần validate, dryrun, generate rồi robot. Chọn kiểm tra giải đáp câu hỏi hiện tại; quy trình gọn/tách bước và viết test tại [WORKFLOWS](WORKFLOWS.md).

| Câu hỏi | Lệnh | Kết quả chứng minh |
| --- | --- | --- |
| Code/config và regression nội bộ có đạt? | validate --app shuup | Các bước nội bộ đăng ký cho adapter; không mở browser |
| Suite có lỗi keyword/import/cấu trúc? | robot --app shuup --dryrun | Cấu trúc và khả năng nạp library; keyword hành trình không được thực thi |
| Website có đạt hành trình được chọn? | robot --app shuup | Assertion UI của suite đã thực thi; có thể thay dữ liệu |
| Model tạo ca gì, độ phủ bao nhiêu? | generate --app shuup | Kế hoạch/CSV/suite; chưa thực thi |
| Ca model có đạt trên UI? | robot --app shuup --design | Sinh lại rồi chạy assertion UI |

Phạm vi validate theo từng app và điều kiện image/mount tại [COMMANDS](COMMANDS.md). Nhóm PHP/.NET robot chỉ có smoke mặc định, không nhận --dryrun hoặc bộ lọc. Setup --run-tests gộp chuẩn bị và chạy suite mặc định; không bao gồm validate.

### Chọn test và đọc báo cáo

Các suite mặc định của Oscar, Shuup, Wowy và Pretix đều dùng tag smoke. --include smoke vì vậy chọn suite smoke hiện có, không phải một bộ kiểm tra toàn website lớn hơn. --test khớp tên test trong file .robot; dùng tên thật hoặc wildcard có khớp. Ví dụ Shuup:

```bat
cmdc.cmd robot --app shuup --test "*Customer Opens*"
```

Ví dụ này chọn catalogue smoke nhanh. Bộ customer xuyên suốt dùng robot --customer; chọn một ca bằng --customer-case SH-CUST-E01 hoặc nhóm bằng --customer-stage. Không dùng --test/--include cho mode DataDriver customer vì test động được sinh sau bước lọc Robot. Đọc apps/shuup/tests/robot/smoke.robot để lấy tên đầy đủ; các app khác có file trong tests/robot riêng. Với Shuup --design, danh sách test lấy từ model/CSV DataDriver thay vì suite smoke. Không có test khớp là lỗi lựa chọn, không phải toàn bộ chức năng đã đạt.

Báo cáo nằm tại apps/<id>/reports: report.html để xem tổng hợp, log.html để mở từng keyword/ảnh lỗi, output.xml cho xử lý máy. Các tên báo cáo mặc định có thể bị ghi đè lần sau; lưu bản cần đối chiếu trước khi chạy tiếp. Kiểm tra mã thoát, Test Execution Errors và keyword status cùng nhau. PASS trong dryrun không tương đương PASS trên browser thật.

## Thiết kế test từ dữ liệu

Shuup dùng cmdc generate --app shuup để sinh kế hoạch single-fault, CSV DataDriver và suite Robot; cmdc robot --app shuup --design sinh lại rồi chạy UI. Biên, phân vùng và rule nằm trong model JSON; hành trình và oracle khai báo một lần cho từng form. Các bước, thư viện, thuật toán, API, giới hạn giảm ca và cách đọc độ phủ tại [AUTOMATED_TEST_DESIGN](AUTOMATED_TEST_DESIGN.md). Generate --legacy giữ bộ CSV cũ có multi-fail riêng. Các adapter khác chưa đổi generator mặc định.

Validate Shuup còn chạy unit của thư viện test-design và regression session địa chỉ native. Checkout customer đầy đủ nằm trong suite --customer: Continue địa chỉ, methods, coupon, COD và đúng đơn trong lịch sử đều đi qua UI native; không thay POST bằng lời gọi nội bộ. Thiết kế/22 ca tại [SHUUP_CUSTOMER_TEST_DESIGN](SHUUP_CUSTOMER_TEST_DESIGN.md); selector/keyword/Python tại [SHUUP_CUSTOMER_TEST_CODE](SHUUP_CUSTOMER_TEST_CODE.md). DataDriver dryrun, kiểm thử serializer và browser chạy thật là ba loại bằng chứng riêng.

## Runtime trình duyệt và cách đọc kết quả

Browser Batteries chứa Node riêng. Browser image cài libatomic1 trước khi cài Chromium; bước build chạy Node --version để phát hiện lỗi dynamic linker. Khi log báo thiếu libatomic.so.1 hoặc không kết nối được Playwright process, kiểm tra playwright-log và build lại browser image qua setup --with-robot hoặc robot-init sau khi cập nhật source. Không sửa bằng cách bỏ listener hoặc bỏ qua lỗi để làm xanh báo cáo.

Dryrun có thể ghi test PASS trong khi các keyword đều NOT RUN; đây là kiểm tra cấu trúc, không phải hành trình UI đã chạy. Xem cả Test Execution Errors và mã thoát. Shuup bật --exitonerror theo [Robot Framework User Guide](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html) để lỗi import/listener được coi là lỗi thực thi nghiêm trọng; điều này không biến dryrun thành kiểm thử chức năng.

## Kiểm thử PHP và .NET

Theo [NATIVE_COMMERCE](NATIVE_COMMERCE.md), robot-init chuẩn bị Chromium; robot kiểm tra trang cửa hàng có Rose Nocturne và ảnh. Test chỉ đọc, dùng network namespace của web để giữ đúng URL loopback. Khi kiểm chứng tích hợp, cần chạy setup lần đầu và lặp lại, thay giá/tồn kho/mật khẩu qua quản trị rồi đối chiếu; kiểm tra lỗi import giữa chừng và missing .env trước khi đưa bộ dữ liệu vào hành trình checkout. Không suy ra kết quả installer hay checkout từ kiểm tra nguồn/fake Docker.

## Kiểm tra dispatcher và giao diện host

Inventory tên/ID và diagnostics được kiểm tra offline, gồm giới hạn dòng, che secret và từ chối log liên kết. Destroy PHP/.NET cần regression cho confirmation, ownership, mất .env, lỗi cleanup, giữ/xóa đúng phạm vi file và thao tác lặp. Các tình huống quan trọng gồm thiếu/sai ID, lựa chọn trùng, không tạo app khác khi app hiện tại đang chạy, tranh khóa, ownership khác workspace, thất bại giữa chừng và cleanup đúng app. Kiểm tra terminal bằng PTY để xác nhận màu, spinner, khôi phục cursor và tiến độ native; kiểm tra pipe/CI để xác nhận văn bản.

Script Windows tại tests/windows/test_launcher.ps1 kiểm tra cú pháp và điều kiện trước Docker. Regression native tại tests/windows/test_docker_arguments.ps1 dùng docker.exe giả lập trong thư mục tạm để kiểm tra dấu nháy qua ProcessStartInfo trên Windows PowerShell 5.1: owner, nhãn container, workspace có dấu cách, lỗi metadata, tranh khóa thật và cleanup. Test không kết nối Docker Engine. Chạy bằng `powershell.exe -NoProfile -ExecutionPolicy Bypass -File tests/windows/test_docker_arguments.ps1`. Quyết định dùng cache/tải helper và lựa chọn image được kiểm tra riêng bằng `powershell.exe -NoProfile -ExecutionPolicy Bypass -File tests/windows/test_image_preparation.ps1`, với hàm giả lập không tải image. Xác nhận Pretix và ngưỡng dự phòng Windows có test CIM giả lập tại tests/windows/test_pretix_safety.ps1. Các kiểm tra chức năng ứng dụng chạy trong container. Bằng chứng của từng đợt phát hành được lưu trong evidence và nhật ký (lưu riêng trong bản bàn giao đầy đủ).

Host regression cho source boundary và log/progress dùng dữ liệu tổng hợp, không chạy ứng dụng hoặc Docker: python -m unittest discover -s tests/host -v. Test PTY giữ child chờ tín hiệu hoàn tất để quan sát đủ các frame, thay vì phụ thuộc một khoảng sleep ngắn. Kiểm tra selection xác nhận static/runtime/vendor/private settings không đi vào checker nhưng source tự viết vẫn được xác thực.

## fuzcake và tiến độ terminal

Regression bootstrap của Shuup tạo registry trong tiến trình mới, kiểm tra default_settings_module, quyền sở hữu SHUUP_PRICING_MODULE của core và đăng ký theme. Regression diagnostic kiểm tra bước migrate thành công thay thế log lỗi cũ. Các kiểm tra này chạy bằng validate --app shuup trong container.

Hợp đồng trình bày Shuup kiểm tra view gốc cho category/product/basket, route collection cũ, navigation hooks, context ngoài trang chủ không truy vấn catalogue, media thêm sau khởi động và header cache riêng của response nghiệp vụ. Các kiểm tra này thuộc suite container; kiểm tra Windows VT cần console Windows thật.

Suite integration của Shuup kiểm tra render theme, trang thông tin, sổ ví theo chủ sở hữu, số dư posted, nạp cục bộ và gửi lặp token. Seed lặp phải giữ mật khẩu, giá, tồn kho, theme và dữ liệu chỉnh sửa; upload trong test dùng thư mục tạm riêng. Chạy bằng validate --app shuup trong Docker. Robot smoke đi từ trang chủ qua nhóm hương tới Rose Nocturne rồi đăng nhập quản trị qua form.

Kiểm tra launcher bằng Docker giả lập có thể đối chiếu thời gian thay đổi trên PTY, canh phải ở nhiều độ rộng, cursor sau ngắt, NO_COLOR và log plain. Bằng chứng này chỉ xác minh điều phối và hiển thị host. Bản HTML dựng từ template để xem CSS là bản xem bố cục; không thay thế kiểm thử theme Jinja hoặc checkout trên ứng dụng thật.

## Wowy và nguồn dùng chung

Validate của Wowy kiểm tra CLI, các ranh giới đọc dữ liệu chung, model/migration và HTTP có CSRF. Regression đối chiếu tổng sản phẩm/phí, tồn kho sau đặt/hủy, checkout gửi lặp, địa chỉ của tài khoản khác, snapshot địa chỉ và quyền truy cập toàn bộ khu vực admin. Robot tiếp tục các hành trình qua UI gốc bằng selector từ trang đã mở.

Thêm app phải có kiểm tra dispatch/isolation với các lựa chọn hiện hữu, trạng thái thiếu .env/dữ liệu chung và namespace của workspace khác. Đối chiếu app-profiles.json với registry, mount chỉ đọc và named contexts. Kiểm tra hash ảnh và tổng tiền trong JSON là kiểm tra nguồn dữ liệu; không thay thế chạy seed hoặc checkout trên ứng dụng thật.

[NAVIGATION](../NAVIGATION.md)
