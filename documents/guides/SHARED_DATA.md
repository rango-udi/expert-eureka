[NAVIGATION](../NAVIGATION.md)

# 🗂️ Dữ liệu fuzcake dùng chung

fuzcake-data ở project root là nguồn khởi tạo và tài nguyên nhận diện dùng chung. Các adapter được liệt kê ở [APPS](../APPS.md). Mỗi adapter ánh xạ dữ liệu vào model riêng và giữ database, secret, tồn kho, đơn hàng của chính app.

## Cấu trúc nguồn

| Thành phần | Trách nhiệm |
| --- | --- |
| [records/store.json](../../fuzcake-data/records/store.json) | Nhận diện, danh tính theo vai trò và các địa chỉ hư cấu |
| [records/catalogue.json](../../fuzcake-data/records/catalogue.json) | SKU, nhóm hương, tên, giá và tồn kho ban đầu, tham chiếu ảnh |
| [records/partners.json](../../fuzcake-data/records/partners.json) | Ngân hàng, ví, phương thức nạp và dịch vụ giao hàng |
| [records/wallet.json](../../fuzcake-data/records/wallet.json) | Lịch sử ví, tổng đối chiếu và đơn/vận chuyển tham chiếu |
| [records/events.json](../../fuzcake-data/records/events.json) | Organizer, sự kiện, vé, quota, voucher và nội dung thanh toán thủ công |
| [records/app-profiles.json](../../fuzcake-data/records/app-profiles.json) | Khai báo nhóm dữ liệu mà từng adapter sử dụng |
| [records/asset-provenance.json](../../fuzcake-data/records/asset-provenance.json) | Tên gốc và SHA-256 của 16 ảnh sản phẩm |
| assets/fuzcake | Ảnh gốc, SVG nhận diện, font và stylesheet dùng chung |
| fuzcake_data | Bộ đọc độc lập với Django/app; kiểm tra tham chiếu, hash và cung cấp dữ liệu cho Robot |

Profile và phạm vi nhập của từng adapter được khai báo trong app-profiles.json và hồ sơ ở [APPS](../APPS.md); Pretix đọc profile sự kiện. Hồ sơ app xác định phần nghiệp vụ hỗ trợ. Bộ dữ liệu chung có ví/ngân hàng không có nghĩa mọi app có tính năng ví; ví cục bộ thuộc adapter Shuup. Đây là nguồn seed, không phải cơ chế đồng bộ giao dịch giữa các app.

## Quyền sở hữu và credit

Dữ liệu hư cấu, mô tả, cách tổ chức dữ liệu và SVG nguyên bản do dự án tạo thuộc rango-udi, theo [CC BY 4.0](../../fuzcake-data/LICENSE.txt). Metadata credit tại [attribution.json](../../fuzcake-data/attribution.json). Khi tái sử dụng, giữ tên/link tác giả, link license và ghi thay đổi. Cho phép sử dụng thương mại và sửa đổi theo điều khoản license.

Ảnh sản phẩm do người dùng cung cấp, nhãn hiệu bên thứ ba, font Noto và artwork điều chỉnh từ Lucide giữ quyền/giấy phép nguồn. Không coi tuyên bố quyền sở hữu dữ liệu là việc tái cấp phép những thành phần đó. Mã nguồn vẫn theo giấy phép phần mềm tương ứng. Chi tiết tại [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md).

## Cách ứng dụng nhận dữ liệu

Các adapter Django truyền fuzcake-data dưới dạng named build context vào image tùy biến. Nhóm PHP/.NET dùng mount chỉ đọc tại thời điểm khởi tạo; helper kiểm tra nguồn chung trước khi gọi installer/seed native. Dockerfile sao chép riêng records, assets và package đọc; build context của app giữ phạm vi trong chính thư mục app. Runtime mount nguồn chung vào /fuzcake-data ở chế độ chỉ đọc. Pretix nhận cùng mount khi chạy seed trong worker.

Bộ đọc reference chỉ nhận tên đã đăng ký và trả bản sao độc lập. Asset phải nằm trong assets, có tệp thực và không đi qua filesystem link. Trước seed, adapter kiểm tra profile, liên kết và hash ảnh; lỗi nguồn dùng chung dừng khởi tạo trước khi cập nhật dữ liệu nghiệp vụ. Ảnh được đọc theo luồng khi kiểm tra hash để giữ mức dùng bộ nhớ nhỏ.

Tên đường dẫn được xử lý bằng Compose và đối số có cấu trúc; giữ nguyên fuzcake-data cạnh apps, config và scripts khi giải nén. Các app dùng một bản dữ liệu nguồn; bản sao trong image và dữ liệu nhập vào database phục vụ runtime, không phải bản source thứ hai để chỉnh sửa.

## Thêm và cập nhật nội dung

1. Sửa đúng nhóm JSON, giữ schema và ID/SKU ổn định. Thêm ảnh vào assets/fuzcake/products và cập nhật manifest nguồn/hash.
2. Kiểm tra các liên kết, số dư, tổng tiền và profile tiêu thụ. Bổ sung ánh xạ ở adapter khi thêm một loại nghiệp vụ mới.
3. Chạy setup --app của app cần nạp. Để khởi tạo và chạy suite mặc định ngay, dùng setup --run-tests; nếu cần kiểm tra code/seed trước UI, chọn setup → validate → robot. Đây là hai cách phục vụ mục tiêu khác nhau theo [WORKFLOWS](WORKFLOWS.md). Setup áp migration và thêm bản ghi còn thiếu; các giá, tồn kho và trường đã có được giữ theo hợp đồng của adapter.
4. Với dữ liệu đã khởi tạo, chỉnh qua UI quản trị hoặc migration có phạm vi rõ ràng. Thay một giá trong JSON không tự cập nhật giá của sản phẩm đã lưu. tests/data/INPUT_MODEL.json của từng app vẫn mô tả biên/phân vùng và quy tắc kiểm thử riêng, tách khỏi dữ liệu nghiệp vụ dùng chung. Không dùng reset/destroy để làm mới nội dung trên database cần giữ.

Process đang chạy có cache tham chiếu; restart hoặc setup app sau khi đổi nguồn. Dữ liệu tương tác không ghi ngược vào fuzcake-data. Không đặt .env, backup, thông tin cá nhân hay credential trong thư mục chung.

## Nâng cấp từ cấu trúc app riêng

Chạy down cho app đang hoạt động. Giữ .env, .runtime và backup của từng app trước khi thay source. Giải nén đầy đủ cấu trúc root có fuzcake-data; nếu chép đè cây cũ, xóa riêng hai thư mục source cũ đã chuyển là apps/shuup/data và apps/shuup/storefront/static/fuzcake để tránh còn bản sao asset cũ. Dữ liệu runtime nằm ở .runtime/data, tách khỏi các thư mục source này.

SKU, identifier và reference đã tồn tại được giữ. Setup chỉ nhập vào app được chọn; các app còn lại được cập nhật khi chủ động chạy setup của chúng. Khi phục hồi database, dùng cùng nguồn khóa và snapshot fuzcake-data với bộ backup để giữ khả năng tái dựng.

Địa chỉ mặc định của CUSTOMER tham chiếu bằng billing_address/shipping_address tới ID trong store.addresses. welcome_offer giữ ID, tên, mã khởi tạo và tỷ lệ giảm; adapter Shuup ánh xạ sang contact/address và campaign native. Các adapter khác có thể nạp nhóm store mà không phải triển khai cùng khả năng coupon.

[NAVIGATION](../NAVIGATION.md)
