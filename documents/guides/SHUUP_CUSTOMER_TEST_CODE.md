[NAVIGATION](../NAVIGATION.md)

# Hiện thực kiểm thử customer

Đọc [phạm vi tình huống](SHUUP_CUSTOMER_TEST_DESIGN.md) và [quy ước dữ liệu/ngôn ngữ](YAML_TEST_DATA.md) trước. Excel và Markdown dùng tiếng Việt. Tên, mô tả thực thi, console, CSV và JSON dùng tiếng Anh. ID cùng giá trị đầu vào cụ thể nối các bản trình bày.

## Điểm vào và sinh ca

Container gọi `python scripts/customer_design.py`. Điểm vào thêm thư mục gốc app vào sys.path trước khi nhập module scripts; PYTHONPATH cung cấp test-design. Điểm vào báo cáo hỗ trợ chạy trực tiếp và dạng module, cả trong repository lẫn bố cục /app/scripts của container.

| Thành phần | Trách nhiệm |
| --- | --- |
| scripts/commands.py | Chọn suite, lọc ca trước DataDriver rồi gọi Robot |
| scripts/customer_design.py | Kiểm tra model, sinh giá trị số lượng, gắn dữ liệu cụ thể và đóng băng dấu vân tay |
| scripts/customer_extensions.py | Kiểm tra 30 ca mở rộng, dữ liệu cụ thể và bảng BVA/EP/quyết định |
| tests/robot/CustomerExtensions.py | Thao tác giỏ, sổ địa chỉ, mật khẩu và phục hồi fixture qua UI |
| scripts/customer_inputs.py | Cụ thể hóa username, mật khẩu, số lượng và dữ liệu hành trình |
| tests/data/CUSTOMER_CASE_TEXT.json | Tên và mô tả thực thi tiếng Anh |
| scripts/customer_english_cases.py | Ca dễ đọc và nhãn đầu vào tiếng Anh từ cùng giá trị cụ thể |
| tests/data/CUSTOMER_EXCEL_TEXT.json | Nội dung tiếng Việt cho Excel và Markdown |
| scripts/customer_report_contract.py | Tạo dữ liệu workbook tiếng Việt và bản JSON tiếng Anh |
| tests/robot/CustomerJourney.py | Điều khiển UI, xác nhận kết quả hiển thị và chụp ảnh từng mốc/lỗi |
| scripts/customer_evidence.py | Lưu và xác minh ảnh đúng lần chạy, đúng TC |
| scripts/customer_report_output.py | Xuất nguyên tử và lưu tên thay thế nếu Excel khóa đích |
| storefront/stock_policy.py | Sửa một lần cấu hình tồn kho hữu hạn của danh mục bằng trường native |
| test-design/test_design/engine.py | Sinh BVA, EP và nghĩa vụ quyết định tường minh, độc lập ứng dụng |

DataDriver tạo một test Robot cho mỗi dòng truyền đã chọn; nó không suy luận biên hoặc kết quả mong đợi. robot_transport.csv mã hóa payload cho template nội bộ. test_cases.csv và execution_cases.csv là bản tiếng Anh dễ đọc; test_cases.md dùng tiếng Việt. Không dán payload truyền nội bộ vào ô dữ liệu Excel.

## Quan sát giao diện

| Hàm | Nội dung quan sát |
| --- | --- |
| _fill_registration, _login | Nhập đúng giá trị cụ thể; mật khẩu đi qua cơ chế nhập secret của Browser |
| _registration_rejection, _login_rejection | Yêu cầu lỗi native/server và trạng thái chưa đăng nhập |
| _search, _open_product | Dùng tìm kiếm, liên kết sản phẩm chính xác, chi tiết và giá trong vùng đặt hàng |
| _inspect_product_gallery | Xác nhận ảnh đang hiển thị đã tải, không suy từ kích thước khung |
| _quantity | Đối chiếu min/step, nhập một số lượng và quan sát giỏ |
| _quantity_error | Đọc lỗi tồn kho/số lượng native đang hiện, độc lập lớp overlay tạm thời |
| _activation_link | Đọc email local đúng người nhận và dùng liên kết kích hoạt thật |
| _coupon | Kiểm tra trạng thái thiếu, lạ, áp dụng và gỡ coupon bằng phép tính độc lập |
| _addresses | Kiểm tra thiếu đường, sao chép thanh toán và địa chỉ giao riêng |
| _checkout_methods | Báo giá từng đơn vị vận chuyển với Pay on delivery |
| _assert_order_lines | Đọc đúng giá, số lượng, tổng tiền và dòng coupon |
| _journey | Giữ cùng customer từ đăng ký tới checkout và đúng lịch sử đơn |

Locator giá là `css=#product-price-section .product-price strong:visible`; tiêu đề và thẻ cũng giới hạn đúng sản phẩm. Thao tác và xác nhận Browser hiện trong log Robot. Executor không dùng ORM, SQL hoặc HTTP client để đổi trạng thái nghiệp vụ. Chờ phản hồi do UI tạo ra phục vụ đồng bộ, không thay thao tác UI bằng lối tắt backend.

Giỏ native có các khối .single-item trong #update_basket_form. Hàm _extra_basket_line chờ form hiển thị rồi chọn đúng khối bằng tiêu đề văn bản trong .product-details .name; thiếu hoặc trùng khối sẽ báo lỗi trước khi nhập số lượng/nhấn xóa. Bảng trong trang xác nhận đơn không phải DOM giỏ.

## Số lượng bị từ chối

Ô không hợp lệ theo native phải bị từ chối và để giỏ trống. Với số vượt tồn nhưng hợp lệ theo ràng buộc HTML, phải quan sát nút thêm bị vô hiệu hóa hoặc thông báo nghiệp vụ native. Lỗi server chung không được tính là từ chối tồn kho. Bộ quan sát đọc mọi thông báo phù hợp đang hiển thị thay vì chọn tùy ý phần tử đầu tiên.

Nếu giỏ nhận hàng, executor báo lỗi ngay kèm số lượng quan sát. Nếu chưa thấy từ chối, lỗi hết thời gian chờ gồm số nhập, số trong giỏ và trạng thái nút. Kết quả chưa xác định không được chuyển thành PASS.

Simple Supplier chỉ kiểm tra giới hạn khi nhà cung cấp và StockCount bật stock_managed, đồng thời backorder_maximum hữu hạn. Seed ghi tồn kho không tự bật cờ nhà cung cấp mặc định. stock_policy sửa cờ/chính sách của SKU fuzcake một lần và đánh dấu hoàn tất qua cấu hình shop native; giữ số lượng tồn, adjustment, giá, tài khoản và giao dịch. Setup lặp sau marker giữ chỉnh sửa mới của người vận hành. Đây là cấu hình native, không phải luật kiểm tra giỏ viết lại trong theme.

Shuup front BasketUpdateMethods ghi lỗi bằng messages.warning, nên bộ quan sát phải xét .alert-warning và nội dung lỗi bội số ngoài .alert-danger. Seed áp dụng purchase_multiple=1 một lần cho SKU fuzcake bán theo đơn vị không cho phân số khi bội số đang là 0; giữ bội số dương tùy chỉnh và tồn kho/giao dịch. Điều này dùng quy tắc native thay vì viết lại validation trong theme. Khi không quan sát được thông báo, test chụp trang rồi tải lại để nêu số lượng đã lưu trong lỗi; không suy diễn giữ nguyên giỏ là PASS.

Trước khi unit.from_display làm tròn, storefront.basket.WholeUnitBasketUpdateMethods kiểm tra tích chính xác của số nhập và tỷ lệ đơn vị. Khi sản phẩm cấm phân số, lượng nội bộ có phần lẻ nhận invalid_quantity qua warning native; lượng hợp lệ được chuyển nguyên cho lớp cha để giữ kiểm tra min, stock, bội số và cập nhật giỏ. Cách này vẫn cho phép số lẻ ở đơn vị hiển thị nếu quy đổi thành số nguyên đơn vị nội bộ. Không chỉ kiểm tra chuỗi nhập có dấu thập phân.

## Vòng đời bằng chứng và báo cáo

execute_customer_case tạo một thư mục bằng chứng mỗi suite và công bố run ID/manifest bằng metadata. Ca độc lập chụp trang kết quả. E01 chụp đăng ký/đăng nhập, tìm kiếm, chi tiết/ảnh, giỏ, coupon, địa chỉ, báo giá vận chuyển, điều khoản, xác nhận và lịch sử. ID nghiệp vụ được chọn trước hành động tương ứng để ảnh lỗi thuộc mốc đang thực hiện.

Nhánh lỗi chụp trang trước Test Teardown đóng Browser. Lỗi chụp được ghi riêng và giữ lỗi chức năng ban đầu. Manifest lưu metadata ảnh/thực thi, không lưu mật khẩu hoặc văn bản trang thô. Báo cáo gắn ảnh theo XML đã chọn thay vì đoán tệp mới nhất có tên giống nhau.

Report ghi workbook hoàn chỉnh vào tệp tạm cùng thư mục rồi thay đích bằng os.replace. Lỗi khóa đích chuyển sang tên riêng cùng thư mục và in WARNING với đường dẫn; mã thoát thành công chỉ sau khi lưu được. Lỗi tạo/ghi hoặc cả hai lần công bố thất bại trả mã lỗi có hướng dẫn, giữ tệp hoàn chỉnh phục hồi nếu có. Cơ chế này không cần đọc workbook đang mở và không thay trạng thái Robot.

## Phạm vi kiểm chứng

validate gồm kiểm tra thiết kế và tích hợp Django trong image tools đã chuẩn bị. Regression điểm vào trực tiếp kiểm tra PYTHONPATH chỉ chứa test-design. Bộ ghi keyword trên host kiểm tra điều phối/quan sát mà không mở browser. Kiểm tra xuất báo cáo mô phỏng khóa chia sẻ Windows, lỗi quyền và hết dung lượng. Chạy `robot --customer --dryrun` chỉ kiểm tra cấu trúc suite; kết quả UI cần thực thi browser thật.

Chạy riêng Q06 bằng `cmdc.cmd robot --app shuup --customer --customer-case SH-CUST-Q06`. E01 thành công để lại tài khoản và đơn; lượt đầy đủ tiếp theo cần danh tính cụ thể mới được duyệt trước khi chạy. Bằng chứng từng phiên bản nằm trong nhật ký (lưu riêng trong bản bàn giao đầy đủ).

## Theo dõi một lượt customer cụ thể

Xem [đường đi từ lệnh CMD](SHUUP_CUSTOMER_EXECUTION.md), [từng dòng Robot và hàm Python](SHUUP_CUSTOMER_ROBOT_WALKTHROUGH.md), cùng [luồng dữ liệu và ảnh](SHUUP_CUSTOMER_DATA_FLOW.md). Ví dụ xuyên suốt là chạy toàn bộ customer và chọn riêng SH-CUST-B09.

[NAVIGATION](../NAVIGATION.md)
