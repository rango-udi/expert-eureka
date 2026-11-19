[NAVIGATION](documents/NAVIGATION.md)

# Robot Web Tests

Bộ môi trường kiểm thử giao diện web bằng Robot Framework. Mã ứng dụng nằm trong `apps/<id>`; root chỉ giữ điều phối chung. Các ứng dụng được quản lý tại [danh mục ứng dụng](documents/APPS.md), với cấu hình, dữ liệu và hành trình riêng. Docker là môi trường chạy cho ứng dụng, migration, seed và browser.

```bat
cmdc.cmd apps
cmdc.cmd setup --app oscar --run-tests
cmdc.cmd down --app oscar
```

Ví dụ trên chuẩn bị và chạy suite mặc định trong một lệnh. Chỉ cần cửa hàng để thao tác thủ công thì bỏ --run-tests; app đã khởi tạo có thể dùng start hoặc robot trực tiếp. Các cách chạy và lý do tách bước tại [WORKFLOWS](documents/guides/WORKFLOWS.md).

Shuup có [bộ customer từ đăng ký tới lịch sử đơn](documents/guides/SHUUP_CUSTOMER_TEST_DESIGN.md), chạy bằng robot --customer, kèm [giải thích selector/keyword/Python](documents/guides/SHUUP_CUSTOMER_TEST_CODE.md).

Cấu hình [dữ liệu kiểm thử YAML](documents/guides/YAML_TEST_DATA.md) là manages literal customer inputs. Excel uses Vietnamese; Robot, console, CSV, Markdown and exported JSON use English. Account names, passwords and addresses are concrete English test values.

Các app có profile phù hợp đọc [dữ liệu fuzcake dùng chung](documents/guides/SHARED_DATA.md). Chọn một app cho mỗi tác vụ; dừng app hiện tại trước khi chuyển ứng dụng. Host cung cấp Docker/Compose và shell hệ điều hành.

Xem [QUICKSTART](QUICKSTART.md), [COMMANDS](documents/guides/COMMANDS.md), [vòng đời và bảo vệ dữ liệu](documents/guides/APP_LIFECYCLE.md), [TESTING](documents/guides/TESTING.md), [thiết kế test từ dữ liệu](documents/guides/AUTOMATED_TEST_DESIGN.md) và nhật ký (lưu riêng trong bản bàn giao đầy đủ).

Dữ liệu fuzcake nguyên bản thuộc rango-udi theo [CC BY 4.0](fuzcake-data/LICENSE.txt); các thành phần bên thứ ba giữ quyền và giấy phép tương ứng.

Phần độc lập do [rango-udi](https://github.com/rango-udi) sở hữu theo [LICENSE](LICENSE). Giấy phép ứng dụng và dependency tại [THIRD_PARTY_NOTICES](documents/THIRD_PARTY_NOTICES.md).

[NAVIGATION](documents/NAVIGATION.md)
