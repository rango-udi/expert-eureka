[NAVIGATION](NAVIGATION.md)

# Thành phần bên thứ ba

## Dữ liệu fuzcake và công cụ sinh test

Dữ liệu hư cấu và artwork nguyên bản: Copyright 2026 [rango-udi](https://github.com/rango-udi), [CC BY 4.0](../fuzcake-data/LICENSE.txt); giữ credit, link license và ghi thay đổi. Ảnh cung cấp/nhãn hiệu, Noto và Lucide được loại khỏi grant này; giữ các thông báo tương ứng trong mục nền tảng/ảnh. Code thư viện test-design thuộc license phần mềm của workspace.

Robot DataDriver 1.11.2 theo Apache-2.0, được cài từ package upstream vào browser image; xem [nguồn và hướng dẫn](https://github.com/Snooz82/robotframework-datadriver). Robot Framework và Browser giữ license dependency đi kèm distribution. DataDriver chỉ tạo test từ các dòng dữ liệu, không cung cấp thuật toán BVA/EP/rule của workspace.

## Nền tảng, ảnh và dependency

[Django Oscar](https://github.com/django-oscar/django-oscar) dùng BSD-3-Clause, bản đầy đủ tại [OSCAR_LICENSE](licenses/OSCAR_LICENSE). Repository/tag/commit tại [SOURCE_LOCK](../apps/oscar/config/source-lock.json). Phạm vi và nguồn của mỗi adapter được liệt kê qua [APPS](APPS.md). Oscar được cài từ package PyPI đã khóa phiên bản.

[pretix](https://github.com/pretix/pretix) được tích hợp bằng image upstream đã khóa digest. Giấy phép đi kèm tại [PRETIX_LICENSE](licenses/PRETIX_LICENSE), nguồn tại [PRETIX_SOURCE_LOCK](../apps/pretix/config/source-lock.json). Adapter kế thừa mã tích hợp của bộ workspace được lưu trong archive; runtime pretix và dependency giữ giấy phép riêng.

Các template override extends template gốc, giữ giao diện và static do Oscar phân phối. Phần độc lập do rango-udi viết dùng [MIT](../LICENSE); MIT không thay giấy phép Oscar, Django, dependency hoặc tài nguyên trong các wheel được cài. Dependency và giấy phép được phân phối trong metadata của package tương ứng.

Browser Batteries và Chromium được tải khi dùng Robot theo [requirements-robot](../apps/oscar/requirements-robot.txt). Ảnh sản phẩm khởi tạo được đọc từ [nguồn fuzcake-data](guides/SHARED_DATA.md); seed của từng app ánh xạ vào media native.

[Shuup](https://github.com/shuup/shuup) được tích hợp bằng wheel 3.1.0 có SHA-256 khóa. Văn bản đi kèm tại [SHUUP_LICENSE](licenses/SHUUP_LICENSE) là OSL-3.0; setup metadata upstream có classifier khác. Bản sửa metadata dependency toml/pytz được mô tả trong [source lock](../apps/shuup/config/source-lock.json); mã ứng dụng và assets giữ nguyên. Giấy phép dependency đi kèm các package được cài trong image.

Gateway Pretix dùng image Nginx riêng, theo giấy phép của image và thành phần upstream. Khóa image tại compose.lock.yaml của app; runtime Pretix giữ giấy phép riêng.

Theme fuzcake là phần mở rộng riêng; base.jinja và cấu hình mặc định front_content trong index.jinja được điều chỉnh từ template Shuup 3.1.0, giữ ghi nhận OSL-3.0; các macro/plugin native được dùng trực tiếp. Ảnh nước hoa được người dùng cung cấp, sao chép nguyên vẹn với nguồn và hash trong [asset-provenance](../fuzcake-data/records/asset-provenance.json); thương hiệu trên ảnh giữ nhận diện gốc. Quyền với ảnh và nhãn hiệu vẫn thuộc chủ sở hữu tương ứng.

Bản notice Noto/Lucide dùng cho phân phối nằm thêm tại fuzcake-data/assets/fuzcake/licenses và đi theo static trong image.

Noto Sans/Noto Serif được đóng gói theo [NOTO_FONT_LICENSE](licenses/NOTO_FONT_LICENSE). Dấu hiệu QuantumGem điều chỉnh từ [Lucide gem 0.468.0](https://github.com/lucide-icons/lucide/blob/0.468.0/icons/gem.svg), theo [LUCIDE_LICENSE](licenses/LUCIDE_LICENSE); các dấu hiệu đối tác còn lại là SVG riêng của bộ dữ liệu.

[Wowy](https://github.com/manjurulhoque/wowy) theo [WOWY_LICENSE](licenses/WOWY_LICENSE), nguồn khóa trong [source-lock.json](../apps/wowy/config/source-lock.json). Lớp adapter dùng settings, checkout, kiểm soát quyền và nguồn fuzcake-data riêng. Các chỉnh sửa tương thích nguồn native được liệt kê trong scripts/prepare_upstream.py; phần static/vendor giữ thông báo giấy phép đi kèm upstream. Database/media/fixtures đi kèm repository không được dùng làm dữ liệu của adapter.

Ảnh, nhận diện và font fuzcake được phân phối từ nguồn dùng chung theo [SHARED_DATA](guides/SHARED_DATA.md), thay vì lưu bản source riêng trong từng app.

[nopCommerce](https://github.com/nopSolutions/nopCommerce) 5.00.1 được tải dưới dạng gói Linux x64 và xác minh SHA-256. Văn bản [NOPCOMMERCE_LICENSE](licenses/NOPCOMMERCE_LICENSE) giữ điều khoản nopCommerce Public License 4.0 và ghi nhận powered by nopCommerce. Adapter giữ theme/attribution native.

[PrestaShop](https://github.com/PrestaShop/PrestaShop) dùng image phân phối của dự án. [PRESTASHOP_LICENSE](licenses/PRESTASHOP_LICENSE) đi kèm core OSL-3.0; module có giấy phép riêng, gồm AFL-3.0 theo upstream. Theme Classic và dependency giữ ghi nhận đi kèm image.

[WooCommerce](https://github.com/woocommerce/woocommerce) theo [WOOCOMMERCE_LICENSE](licenses/WOOCOMMERCE_LICENSE), được tải từ release và kiểm SHA-256. WordPress, PHP, MariaDB, PostgreSQL và .NET giữ giấy phép của distribution/image tương ứng. Theme fuzcake Fragrance House của adapter là mã riêng, dùng API/template WooCommerce và giữ thông báo dependency upstream.

Source lock của từng nền tảng được liên kết từ [APPS](APPS.md). ZIP của workspace chứa adapter, không đóng gói lại binary runtime hay toàn bộ mã các nền tảng này; Docker tải chúng khi build/pull.


[NAVIGATION](NAVIGATION.md)
