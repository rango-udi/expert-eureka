[NAVIGATION](../NAVIGATION.md)

# Vận hành cửa hàng PHP và .NET

Chọn nopCommerce, PrestaShop hoặc WooCommerce từ [APPS](../APPS.md). Mỗi lựa chọn có database, volume, cấu hình và tài khoản riêng. Cả ba dùng danh mục nước hoa trong [SHARED_DATA](SHARED_DATA.md), với phạm vi nhập được mô tả tại hồ sơ ứng dụng.

## Chuẩn bị và cài đặt

Docker phải chạy Linux containers và Compose từ 2.24.0 để hỗ trợ env_file tùy chọn. nopCommerce dùng gói Linux x64 nên yêu cầu engine amd64; không tự bật giả lập trên ARM. Dùng source đầy đủ có apps, scripts, config và fuzcake-data.

```bat
cmdc.cmd apps
cmdc.cmd doctor
cmdc.cmd setup --app woocommerce --accept-resource-risk
cmdc.cmd urls --app woocommerce
cmdc.cmd status --app woocommerce
cmdc.cmd down --app woocommerce
```

Thay ID trong lệnh để chọn app khác. Trên terminal tương tác, có thể bỏ --accept-resource-risk và gõ đúng ID ứng dụng tại lời nhắc. Cần xác nhận lại cho mỗi tác vụ tạo tải. Xác nhận không bỏ qua ownership, khóa engine, ngưỡng dự phòng RAM hay chính sách VM.

Setup kiểm tra RAM, sinh .env từ .env.template bằng container bootstrap không có mạng, chuẩn bị image được chọn, kiểm tra nguồn chung, khởi động database rồi web, chạy trình cài đặt native và nhập sản phẩm. Marker .runtime/initialized.json chỉ được ghi sau khi trình khởi tạo và kiểm tra readiness hoàn tất. Lỗi ở một bước dừng luồng; database và .env được giữ để chẩn đoán.

## Phạm vi lệnh

| Lệnh | Công dụng và tác động |
| --- | --- |
| setup | Chuẩn bị image, installer/seed và khởi động web; --with-robot thêm browser, --run-tests thêm browser và chạy smoke |
| bootstrap | Tên tương thích của setup; dùng một trong hai |
| init | Chạy lại kiểm tra dữ liệu, installer/seed với image sẵn có rồi đưa web tới readiness |
| start | Mở app đã có marker; database trước web; không build hoặc seed |
| up | Tên tương thích của start |
| restart | Dừng riêng web rồi mở lại database/web; không rebuild |
| stop | Dừng service; giữ container, network và volume |
| down | Dừng/gỡ container và network; giữ volume/image/.env |
| status | Snapshot trạng thái container Compose |
| resources | Snapshot RAM/CPU container |
| logs | Đuôi 100 dòng log web/database |
| diagnostics | Đọc log backend cục bộ khi Docker đã dừng, che secret cấu hình |
| destroy --yes | Xóa container/network/data volume/marker của đúng app; --include-files mở rộng phạm vi file như phần dưới |
| urls | In storefront và quản trị từ HTTP_PORT đã cấu hình; không mở browser |
| env init | Dùng helper để tạo .env khi thiếu; giữ cấu hình đã có; env không đối số có cùng hành vi |
| config | In Compose --no-interpolate; không thay cấu hình |
| validate | Tạo/kiểm tra .env, build tools rồi kiểm tra giá trị cấu hình, profile, tham chiếu và hash ảnh; không kiểm thử installer/checkout/UI |
| source | In source-lock; không tải checkout |
| versions | Cùng in source-lock theo giao diện hiện tại; không truy vấn package đang chạy |
| robot-init | Chuẩn bị browser image; không chạy smoke; tùy chọn vì robot đã build |
| robot | Build browser và chạy smoke chỉ đọc; cần web đang chạy, không nhận thêm option |

**Cách gọn:** setup --app woocommerce --run-tests --accept-resource-risk đã bao gồm mở web và kiểm tra UI mặc định. Không cần chạy robot-init rồi robot để lặp lại cùng test. **Cách chủ động:** setup để thao tác thủ công; robot khi web còn chạy; nếu đã down thì start trước robot. Chỉ tách robot-init khi muốn chuẩn bị dependency từ trước. Xem [WORKFLOWS](WORKFLOWS.md) và [COMMANDS](COMMANDS.md).

Các lệnh backup, restore, reset, generate và manage cần adapter nghiệp vụ riêng và bị từ chối trước Docker. Không dùng lệnh của app khác để bảo trì database này. Với backup, dừng app, sao lưu database bằng công cụ native phù hợp, lưu volume web/media cùng .env và marker. Chỉ phục hồi vào stack cùng phiên bản; không xóa volume để chữa lỗi setup.

Destroy xóa database/media trong volume của đúng app và bỏ marker khởi tạo. Mặc định giữ .env, log, reports và backups. Thêm --include-files để xóa .env, reports và backups; log chẩn đoán, source, fuzcake-data và image cache vẫn được giữ. Lệnh yêu cầu --yes, không tải image và có thể dùng khi setup thất bại hoặc mất .env. Chỉ dùng khi dữ liệu có thể xóa; sau đó cần setup lại. Nếu cleanup Docker lỗi, file cục bộ được giữ để phục hồi.

```bat
cmdc.cmd destroy --app prestashop --yes
cmdc.cmd setup --app prestashop --accept-resource-risk
```

Robot kiểm tra storefront có Rose Nocturne và ảnh. Nó dùng cùng network namespace với web để URL loopback và redirect native hoạt động nhất quán. Đây không phải bộ kiểm thử checkout/thanh toán hoàn chỉnh. Ghi nhận kiểm chứng từng phiên bản tại nhật ký (lưu riêng trong bản bàn giao đầy đủ).

## Tài nguyên và cổng

Các giới hạn APP_MEMORY_LIMIT, DB_MEMORY_LIMIT và ROBOT_MEMORY_LIMIT nằm trong .env.template từng app. Database dùng buffer nhỏ, giới hạn kết nối; Apache giới hạn hai worker, .NET dùng GC heap ceiling. Đây là cơ chế hạn chế tải, không phải số đo RAM tối thiểu hay bảo đảm không OOM. Tác vụ tải/unpack và cache VM còn cần RAM ngoài heap ứng dụng.

Ngưỡng dự phòng host của nhóm này nằm ở config/commerce-safety.env. Khoảng RAM engine dùng chính sách chung tại config/host-memory.env; xem [MEMORY](MEMORY.md) và [trợ giúp WSL](../helps/WSL_VM_MEMORY_LIMIT.md). Đặc biệt nopCommerce có thể không đủ RAM trong cấu hình VM nhỏ; xem log OOM, tăng ngân sách có chủ đích hoặc chọn app nhẹ hơn.

HTTP_PORT là cổng ổn định từ 1024 đến 65535, chỉ bind 127.0.0.1. Database không publish cổng. Chọn cổng trống trước lần setup đầu. PrestaShop và WordPress lưu URL trong database; sau cài đặt, giữ cổng cũ hoặc thực hiện migration URL bằng công cụ native. Không đổi riêng .env rồi kỳ vọng URL trong database tự thay đổi.

## Giữ dữ liệu khi chạy lại

SKU là khóa ánh xạ sản phẩm. Seed tạo bản ghi thiếu; giá, tồn kho, tài khoản và mật khẩu đã có được giữ. Nội dung runtime không được ghi ngược vào fuzcake-data. Mỗi app có thể nhận phần khác nhau của bộ dữ liệu; không suy ra có ví hay ngân hàng thanh toán vì JSON chung có các nhóm đó.

Không cấp credential cổng thanh toán thật trong stack này. WooCommerce dùng COD cục bộ và phí fuzcake Delivery. PrestaShop và nopCommerce giữ module/thanh toán native để người vận hành cấu hình riêng; adapter không tự kích hoạt dịch vụ thanh toán bên ngoài.

Volume gắn nhãn workspace và app. Khi có dữ liệu mà thiếu .env, khôi phục file riêng cũ trước khi tiếp tục; không sinh tài khoản/database password thay thế. Khóa và quy tắc đổi app theo [APP_LIFECYCLE](APP_LIFECYCLE.md).

## Xử lý lỗi

| Biểu hiện | Kiểm tra và hướng xử lý |
| --- | --- |
| Image/tag không tải được | Kiểm tra mạng, kiến trúc engine và source-lock; giữ phiên bản khóa thay vì đổi sang latest |
| Bind cổng thất bại | Dừng tiến trình chiếm cổng; đổi HTTP_PORT trước cài đặt đầu hoặc giữ cổng đã lưu |
| Database không healthy | Xem logs --app; đối chiếu .env gốc và tình trạng volume |
| EOF, exit 137 hoặc OOM | Dừng app, kiểm tra tài nguyên/WSL, giảm tải khác và điều chỉnh ngân sách có cơ sở |
| Khởi tạo native thất bại | Chạy diagnostics --app của app bị lỗi để đọc nguyên nhân backend; giữ .env và volume. PrestaShop lưu log installer tại apps/prestashop/.runtime/prestashop-install.log; seed PHP lưu .runtime/seed-diagnostic.log. Đây là log riêng ngoài web root, có thể chứa thông tin kỹ thuật nhạy cảm |
| Import nopCommerce không xác nhận đủ SKU | Xem thông báo import trong quản trị và log app; sửa nguyên nhân rồi chạy lại setup |
| Mất .env hoặc ownership khác workspace | Dùng bản cấu hình và workspace gốc, không xóa nhãn/volume/khóa để bỏ qua kiểm tra |

Diagnostics đọc tối đa 120 dòng cuối mỗi log backend, che giá trị secret trong .env. Kiểm tra nội dung còn lại trước khi chia sẻ; lệnh không thay thế việc giữ bản log đầy đủ để đối chiếu. Không công bố .env. Chẩn đoán lỗi native phải loại credential trước khi chia sẻ.

[NAVIGATION](../NAVIGATION.md)
