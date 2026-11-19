[NAVIGATION](../NAVIGATION.md)

# Sinh test hộp đen từ mô hình dữ liệu

## Phạm vi và cách chạy

Thư viện dùng chung nằm tại [test-design](../../test-design/test_design/engine.py). Adapter Shuup tích hợp sẵn lệnh sinh và chạy UI; các adapter khác hiện giữ generator cũ, chưa tự động dùng hành trình này. Package không import Django hay nghiệp vụ, nên có thể tái sử dụng khi adapter khác cung cấp build context, dữ liệu và binding UI tương ứng.

Nếu app chưa có, chạy setup --app shuup một lần. Sau đó chọn cách chạy gọn:

```bat
cmdc.cmd robot --app shuup --design
```

Hoặc dùng model tùy chọn trong apps/shuup/tests/data:

```bat
cmdc.cmd robot --app shuup --design --design-model tests/data/WALLET_DESIGN.yaml
```

Nếu cần duyệt kế hoạch trước, dùng generate --app shuup rồi mở reports/design/coverage.json và cases.csv; sau khi chốt model mới gọi robot --design. Generate không phải bước bắt buộc vì robot --design đã sinh lại. Dryrun là lựa chọn kiểm tra cấu trúc bằng robot --design --dryrun; validate là kiểm tra backend/thư viện độc lập. Không cần chạy đủ các lệnh trước mỗi lượt UI. Quy trình viết model, binding và test tại [WORKFLOWS](WORKFLOWS.md).

Lệnh generate mặc định đọc [WALLET_DESIGN.yaml](../../apps/shuup/tests/data/WALLET_DESIGN.yaml), xuất apps/shuup/reports/design. Folder tests/data được mount chỉ đọc vào browser container; sửa model ở đó không cần build lại dependency. Các đường dẫn model được hiểu bên trong container: thư mục apps/shuup trên host được mount tại /app. Robot --design tự sinh lại dữ liệu trước khi chạy. Không thêm --design thì suite smoke cũ vẫn được dùng. Generate --legacy xuất CSV cũ, có nhóm multi-fail riêng và không phải luồng single-fault tối ưu này. Luôn giữ .env/.runtime và dùng tài khoản/dữ liệu cục bộ dành cho kiểm thử.

Dryrun kiểm tra cấu trúc suite, không xác nhận hành vi trang web. Các ca accepted của ví thực sự bổ sung credit giả lập và lịch sử; mỗi ca dùng browser/context mới nhưng không xóa database. Số dư sau chạy tăng theo các khoản posted, không được dùng số dư cố định làm oracle cho những lần chạy tiếp theo.

Bộ customer Shuup có model và hành trình chuyên biệt qua --customer; xem [thiết kế customer](SHUUP_CUSTOMER_TEST_DESIGN.md) và [giải thích mã](SHUUP_CUSTOMER_TEST_CODE.md). Nó tái sử dụng engine cho quantity và DataDriver cho execution; các checkpoint decision của E01 được hiện thực tường minh bằng Browser helper. --design trên trang này vẫn là model ví.

## Thành phần và trách nhiệm

| Thành phần | Thực hiện | Không suy diễn |
| --- | --- | --- |
| test_design.engine | Sinh Robust BVA, Weak Robust EP, rule bảng quyết định; phân loại fault; gộp và giảm ca | Không học biên/luật từ implementation |
| decimal.Decimal | Tính min-step, min+step, max-step, max+step chính xác theo bước nhập | Không dùng sai số float làm biên |
| test_design.cli | Đóng băng model, xuất CSV, coverage.json và run.robot | Không thực thi nghiệp vụ khi generate |
| robotframework-datadriver 1.11.2 | Listener v3 tạo một test Robot cho mỗi dòng CSV của Test Template | DataDriver không tự tính BVA/EP hoặc tự biết oracle |
| Robot Framework 7.5.1 | Điều phối test, keyword, tag, log và assertion | Không thay thế thiết kế mô hình |
| Browser 21.0.0 / Chromium | Tương tác form, click, select, chờ và kiểm tra kết quả trên UI | Không gọi API/database để tạo lỗi nghiệp vụ |
| RobotJourney | Ánh xạ dữ liệu vào hành trình đã khai báo, giữ secret trong environment | Không chạy Python/JavaScript tùy ý từ model |

Đây là thư viện thuật toán nội bộ kết hợp DataDriver, không phải tuyên bố DataDriver có sẵn cả ba kỹ thuật. Dependency được khóa trong requirements-robot.txt. Tham chiếu: [DataDriver](https://github.com/Snooz82/robotframework-datadriver), [data-driven style](https://docs.robotframework.org/docs/testcase_styles/datadriven), [Browser](https://marketsquare.github.io/robotframework-browser/Browser.html).

## Khai báo trường và phân vùng

Model có schema_version=1, fields và decision_table tùy chọn. Giá trị UI nominal, representative và values đều là chuỗi, giữ đúng cách người dùng nhập. Mỗi field cần nominal hợp lệ và partitions có id riêng, valid kiểu Boolean và representative thuộc đúng phân vùng.

Trường số khai báo min, max, step. Step là độ phân giải thực tế của control: ví dụ 0.01 cho tiền, 1 cho số lượng nguyên. Các biên và nominal phải nằm trên cùng lưới bước nhập. Không áp dụng công thức biên số cho email, danh sách lựa chọn hay mọi chuỗi tùy ý.

| Thuộc tính phân vùng | Ý nghĩa |
| --- | --- |
| values: ["", ...] | Các giá trị rời rạc, bao gồm chuỗi rỗng nếu cần kiểm tra required |
| min / max | Giới hạn số bao gồm đầu mút |
| above / below | Giới hạn số không bao gồm đầu mút |
| representative | Một giá trị đại diện do người thiết kế chọn |
| valid | Giá trị có hợp lệ theo đặc tả đầu vào hay không |

Mỗi giá trị được sử dụng phải thuộc đúng một phân vùng. Engine phát hiện chồng lấp/khoảng trống tại các giá trị đã sinh; kiểm tra này không chứng minh toàn miền đã được phân hoạch đầy đủ. Người thiết kế chịu trách nhiệm về đặc tả, đặc biệt với chuỗi, định dạng, điều kiện liên trường và dữ liệu không thể nhập qua UI.

## Kỹ thuật, single fault và giảm ca

Robust BVA tạo baseline và thay lần lượt một trường số bằng min-step, min, min+step, max-step, max, max+step; các trường còn lại giữ nominal. Với n trường số, có tối đa 6n+1 đề xuất trước khi gộp giá trị trùng. Step là đơn vị nhập hợp lệ (ví dụ 0.01 USD), không phải epsilon tùy ý. Min/max/nominal phải thẳng hàng với step. Những giá trị ngoài miền hợp lệ hoặc lệch step cần có phân vùng invalid tương ứng. Với trường số, min/max/step giới hạn miền valid trước khi phân loại; phân vùng precision dạng values có thể khai báo giá trị như 5.001 khi step là 0.01.

Weak Robust EP chọn representative của từng phân vùng valid/invalid rồi thay một trường mỗi lần; các trường khác giữ nominal hợp lệ. Vì vậy một ca có nhiều nhất một trường invalid. Phân vùng dùng values cho tập giá trị chuỗi, hoặc min/max bao gồm đầu mút và above/below không bao gồm đầu mút. Generator kiểm tra một giá trị được dùng thuộc đúng một phân vùng; đây không phải chứng minh mọi giá trị chưa được khai báo đều đã được phân vùng đầy đủ.

Bảng quyết định dùng conditions (field, true, false) và rules (id, when, expected). When khai báo mọi condition với true/false hoặc dấu * là không quan tâm. Mỗi rule có một input đại diện; dấu * giữ nominal. Expected là nhãn outcome do người thiết kế định nghĩa; các rule chồng lấp có outcome khác nhau bị từ chối. Các input không khớp rule dùng accepted/rejected theo phân vùng, nên phải cung cấp các oracle mặc định này khi còn ca tương ứng. Generator không tự phát minh expected cho các tổ hợp chưa có trong bảng.

Constraints gồm when ánh xạ field sang giá trị và reason để loại những tổ hợp người thiết kế xác định không khả thi. Rule có thể ghi infeasible_reason. Rule cần từ hai trường invalid bị loại bởi single-fault và được ghi rõ; không được gọi đó là đã phủ rule. Những tổ hợp có nhiều điều kiện kinh doanh nhưng tất cả input vẫn thuộc phân vùng valid không tự động bị coi là multi-fault.


Ngoài bộ ca một trường, engine bổ sung vector EP-only ghép nhiều phân vùng valid và tối đa một invalid; các vector này có thể giảm số ca EP nhưng không được nhận nghĩa vụ BVA vốn yêu cầu các trường khác giữ nominal.

Các đề xuất cùng input và outcome được gộp; một lần thực thi có thể chứng kiến cả BVA, EP và rule. Greedy set cover chọn ca phủ nhiều nghĩa vụ chưa được chứng kiến nhất, rồi reverse deletion loại ca dư. Kết quả là irredundant trong tập ứng viên: bỏ thêm một ca sẽ mất nghĩa vụ. Không mặc định tuyên bố đó là tối ưu toàn cục. Lower bound kết hợp số nghĩa vụ chia sức phủ lớn nhất và số ứng viên bắt buộc có nghĩa vụ độc quyền; minimum_proven chỉ true nếu cận dưới bằng số ca chọn, và chỉ chứng minh trong tập ứng viên hữu hạn của model này.

Coverage.json chứa proposed_count (trước gộp), candidate_count (khả thi sau gộp), selected_count, declared_obligations, eligible_obligations, covered_obligations, excluded_obligations và excluded_candidates. Độ phủ model đủ điều kiện là covered/eligible; luôn đọc cùng danh sách bị loại và raw declared. Đây không phải code coverage, độ phủ toàn website hoặc tỷ lệ test đã chạy đạt. CSV sinh thành công cũng không có nghĩa ứng dụng đã đạt các assertion.

## Binding UI và oracle

ui khai báo setup, path, bindings, submit và oracles. Một hành trình được cấu hình một lần; sau đó thay biên, phân vùng và điều kiện không cần viết lại test case. Khi chuyển sang form khác, vẫn cần khai báo selector, điều kiện chuẩn bị và kết quả mong đợi vì engine không thể tự suy ra chúng từ các con số.

CSV lưu payload dạng base64 để không diễn giải ký hiệu biến Robot trong dữ liệu; model.json và coverage.json giữ đầu vào đọc được. Base64 không phải mã hóa bảo mật. Tên field/partition/condition/rule và outcome dùng chữ/số/_/- tối đa 64 ký tự.

Setup hỗ trợ navigate, fill_env, click và wait (visible hoặc attached); navigate chỉ nhận đường dẫn cùng origin. fill_env chỉ dùng biến tài khoản Robot cho phép, đi qua Browser.Fill Secret. Không đặt mật khẩu, token thanh toán hoặc .env vào model/CSV. Binding hỗ trợ fill và select; không ép thêm option không tồn tại hoặc sửa DOM để tạo đầu vào người dùng không thể nhập.

Oracle visible_text chờ selector hiển thị và kiểm tra text. Oracle native_invalid kiểm tra checkValidity của control sau click submit: nó kiểm chứng validation HTML ở UI, không chứng minh server từ chối payload khi bypass browser. Hành trình ví mẫu kiểm tra thông báo thành công cho accepted và validation HTML của amount cho rejected. Backend validation, idempotency và authorization vẫn cần các suite integration riêng.

## API, sửa đổi và kiểm tra

engine.validate kiểm tra cấu trúc/phân vùng; classify định danh phân vùng cho một giá trị; design trả kế hoạch; cli.export đọc model và ghi artifacts. RobotJourney.run_modelled_journey thực thi một dòng qua browser. Đọc docstring và các test tại test-design/tests; validate Shuup chạy chúng trong tools image. Thêm nghiệp vụ mới bằng model/binding và oracle trước; chỉ mở rộng runner khi hành động không thể biểu diễn bằng các primitive hiện có.

Mọi chạy generator, unittest, Robot và ứng dụng thực hiện trong Docker. Kiểm tra source/JSON/cú pháp trên host không thay thế việc chạy thư viện, DataDriver dryrun hoặc UI. Ghi trạng thái thực thi và hạn chế môi trường trong nhật ký phiên bản/evidence.

[NAVIGATION](../NAVIGATION.md)
