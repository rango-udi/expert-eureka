[NAVIGATION](../NAVIGATION.md)

# 🎟️ pretix

Tra ID và cách lựa chọn tại [danh mục ứng dụng](../APPS.md). Adapter phục vụ kiểm thử bán vé, giỏ hàng và giao diện quản trị sự kiện. Nguồn và tag được ghi trong [PRETIX_SOURCE_LOCK](../../apps/pretix/config/source-lock.json); image khóa bằng digest tại [compose.lock.yaml](../../apps/pretix/compose.lock.yaml).

## Chọn cách chạy

Setup đã mở stack. Thêm --run-tests để chuẩn bị browser và chạy suite mặc định trong cùng một lệnh; Pretix không nhận --with-robot. Với app đã khởi tạo, robot tự chuẩn bị browser còn thiếu và mở lại dịch vụ khi chạy thật. Robot-init chỉ là lựa chọn pull browser trước; start dùng để mở lại cửa hàng mà không chạy test. Các tác vụ tạo tải cần --accept-pretix-risk hoặc xác nhận prompt mỗi lần. Validate là kiểm tra Compose/unit/cú pháp/source/docs; không chạy hành trình browser. Xem [COMMANDS](../guides/COMMANDS.md) và [WORKFLOWS](../guides/WORKFLOWS.md).

## Cảnh báo và xác nhận

Stack có thể tạo tải RAM/đĩa cao khi chuẩn bị và khởi động. Xác nhận riêng cho mỗi tác vụ bằng prompt pretix hoặc --accept-pretix-risk; cờ không bỏ qua các kiểm tra tài nguyên/ownership. [PRETIX_RESOURCE_PRESSURE](../helps/PRETIX_RESOURCE_PRESSURE.md) liệt kê phạm vi lệnh, profile giảm tải và quy trình xử lý EOF/OOM. Status/logs/resources và down giữ sẵn để phục hồi.

## Khởi tạo

```bat
cmdc.cmd setup --app pretix --accept-pretix-risk
cmdc.cmd urls --app pretix
cmdc.cmd robot --app pretix --accept-pretix-risk
```

Setup chuẩn bị tuần tự image server còn thiếu, migrate/seed, cấp cổng loopback rồi khởi động từng dịch vụ với kiểm tra giữa bước. Mặc định restart policy no giữ dịch vụ lỗi dừng để xem log; swap của container có trần bằng 0 để giảm nguy cơ nghẽn đĩa. Browser được chuẩn bị bằng robot-init hoặc robot; `setup --run-tests` chuẩn bị và chạy suite. Source checkout là tác vụ source riêng; setup dùng image đã khóa.

## Cấu hình và tài nguyên

Dữ liệu cấu hình riêng nằm trong `apps/pretix/.env`, sinh từ [.env.template](../../apps/pretix/.env.template). Reports/backups/evidence cũng thuộc thư mục adapter. Database, Redis, media/config và mail dùng named volume của Compose project robot-web-pretix.

Stack gồm gateway Nginx riêng, pretix web, PostgreSQL, Redis, Mailpit và worker. Periodic scheduler là lựa chọn riêng, mặc định manual; scheduled bật lại khi cần tác vụ định kỳ. EXECUTION_MODE=single giữ một web worker và một tác vụ nền tuần tự. MEMORY_BUDGET_MIB mặc định của adapter là 1920 MiB, phân bổ thành trần các container; chỉnh theo máy và workload. Xem cấu hình hiệu lực bằng `config --app pretix`.

Khi chạy lại setup/pull, image đã có được giữ để tránh tải lại. Ngân sách server khác với bộ nhớ guest và đỉnh khi chuẩn bị image. Chọn mốc/dung sai tại [MEMORY](../guides/MEMORY.md) theo stack này; không lấy mức dùng của ứng dụng khác làm bằng chứng pretix đủ RAM.

## Hành trình và truy cập

Urls trả đường dẫn ticket shop, control và Mailpit. Customer mở danh sách sự kiện của organizer, chọn Future Makers Summit và thêm vé vào giỏ. Quản trị đăng nhập từ control; staff được cấp phạm vi organizer qua dữ liệu seed. Email kiểm thử được nhận trong Mailpit.

Suite smoke bao gồm danh sách sự kiện, giỏ vé miễn phí, liên kết phục hồi mật khẩu và đăng nhập quản trị. Fixture mặc định có organizer demo-organizer và sự kiện Future Makers Summit. Profile sự kiện nằm trong [SHARED_DATA](../guides/SHARED_DATA.md). Sự kiện mới nhận tiền tệ hiệu lực từ cấu hình instance; mức giá vé khởi tạo được diễn giải theo tiền tệ đó và không quy đổi lịch sử đã có. Dữ liệu từ các phiên trước được giữ nguyên khi seed bổ sung bản ghi thiếu.

Bằng chứng HTTP/browser phải ghi rõ kết quả thực thi; không suy rộng smoke thành toàn bộ checkout hoặc thanh toán.

Hostname pretix.localhost và cổng công bố được giữ nhất quán giữa host, gateway và browser thông qua adapter. Các thao tác tiếp theo trong hành trình dùng link/nút/form.

## Sao lưu và xóa

Backup dừng writers, tạo database.dump và data.tar.gz trong thư mục tên mới. Restore cần backup tin cậy và `--yes`; archive media được kiểm tra đường dẫn/thành viên trước khi thay database. Backup/restore giữ ứng dụng dừng để người vận hành chủ động start lại.

Reset db/cache chỉ xóa volume tương ứng sau kiểm tra nhãn ownership. Data/all và destroy có phạm vi rộng hơn; `destroy --yes --include-files` xóa thêm cấu hình và output riêng của adapter. Image dùng chung ngoài project không được prune toàn hệ thống.

## Kiểm tra cấu hình và source

`cmdc.cmd validate --app pretix --accept-pretix-risk` kiểm tra Compose, các unit test cấu hình/tài nguyên/archive, cú pháp Python và quy ước source/tài liệu chung. Lệnh này không thay thế suite browser.

## Tham khảo

[pretix Docker](https://docs.pretix.eu/self-hosting/installation/docker_smallscale/), [cấu hình pretix](https://docs.pretix.eu/self-hosting/config/).

[NAVIGATION](../NAVIGATION.md)
