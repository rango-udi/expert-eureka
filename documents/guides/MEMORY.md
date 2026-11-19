[NAVIGATION](../NAVIGATION.md)

# 🧠 Quản lý RAM

Quản lý tài nguyên theo ba phạm vi: container project, máy ảo chạy Docker và hệ điều hành host. Chọn ngân sách cho từng phạm vi trước khi khởi tạo môi trường.

## Ngân sách của ứng dụng

Tra stack, trần container, cấu hình và kiểu workload tại [danh mục ứng dụng](../APPS.md). Mỗi adapter có phân bổ riêng; mức dùng hoặc tổng trần của một app không xác nhận khả năng chạy app khác trong cùng ngân sách.

Theo dõi bằng `resources --app <id>` và log container. Khi có OOM, xác định thành phần cần tài nguyên trước khi thay đổi ngân sách. Trong một phiên chỉ một adapter được vận hành.

Pretix có [kiểm tra dự phòng host và xác nhận từng tác vụ](../helps/PRETIX_RESOURCE_PRESSURE.md), khởi động từng dịch vụ và profile swap/restart/scheduler riêng. Các kiểm tra giữa bước không giám sát liên tục tiến trình đang chạy. Shuup dùng một web container với SQLite; số container ít hơn không tự chứng minh RAM đỉnh thấp hơn khi chưa đo.

Nhóm PHP/.NET có xác nhận tải và policy dự phòng host riêng theo [NATIVE_COMMERCE](NATIVE_COMMERCE.md). Ngân sách cho browser và database phải được tính cùng web; giới hạn GC/PHP không bao gồm toàn bộ RAM của engine.

## Khoảng chấp nhận của RAM VM

Project quy định một **mốc RAM danh định** cùng **dung sai tăng thêm** cho engine. Mức VM phù hợp có thể cao hơn mốc trong khoảng cho phép; không cần khớp một giá trị duy nhất.

Công thức cận trên:

`accepted_maximum_mib = HOST_MEMORY_TARGET_MIB + HOST_MEMORY_TOLERANCE_MIB`

| RAM engine báo | Xử lý trước khi chuẩn bị image |
| --- | --- |
| Thấp hơn mốc | Cảnh báo; tiếp tục theo dõi khả năng đáp ứng workload |
| Từ mốc đến cận trên, gồm hai đầu | Chấp nhận |
| Vượt cận trên | Dừng và hướng dẫn điều chỉnh VM hoặc cấu hình project |

Mốc và dung sai nằm trong [config/host-memory.env](../../config/host-memory.env); xem cách ưu tiên biến terminal tại [ENVIRONMENT](ENVIRONMENT.md). Dung sai bằng 0 giữ cách kiểm tra cận trên tại đúng mốc. Mỗi lần doctor hoặc chuẩn bị image, launcher hiển thị các giá trị đang có hiệu lực.

Ví dụ về ý nghĩa: nếu mốc là 1,8 GiB và dung sai là 0,3 GiB, VM ở 1,9, 2,0 hoặc 2,1 GiB thuộc khoảng dự kiến. Đây là minh họa, không phải giá trị bắt buộc. Khi nhập cấu hình, quy đổi sang MiB nguyên và dùng cùng đơn vị để tránh sai khác làm tròn. Chẳng hạn mốc 1800 MiB, dung sai 300 MiB cho khoảng từ 1800 đến 2100 MiB.

Ngân sách container, mốc kiểm tra engine và RAM VM có vai trò riêng. Chọn phần dự phòng phù hợp cho hệ điều hành guest, Docker và các workload cùng VM. Mốc kiểm tra chưa phải kết quả đo RAM tối thiểu; VM thấp hơn mốc cần được theo dõi về OOM, log và hiệu năng.

## Áp dụng vào môi trường

| Môi trường | Nơi cấu hình giới hạn RAM |
| --- | --- |
| Docker Desktop WSL 2 | `.wslconfig`; xem [hướng dẫn WSL](../helps/WSL_VM_MEMORY_LIMIT.md) |
| Docker Desktop Hyper-V/macOS | Phần Resources của VM được hỗ trợ |
| Docker Engine từ xa | Máy hoặc VM đang cung cấp engine |
| Docker trực tiếp trên Linux | Tài nguyên host và trần container theo ngân sách vận hành |

Chọn RAM VM trong khoảng đã thống nhất, áp dụng ở backend rồi kiểm tra lại bằng `cmdc doctor`. Điều chỉnh mốc/dung sai trong project nếu ngân sách vận hành thay đổi. Dùng `cmdc wsl-vm-limit-help` để xem cách cấu hình WSL.

## Hạn chế RAM khi chuẩn bị image

Pull/giải nén image và BuildKit dùng tài nguyên engine ngoài trần của container ứng dụng. Page cache có thể tiếp tục chiếm RAM host sau khi tác vụ đã kết thúc. Kết hợp các lớp sau theo đúng phạm vi:

| Lớp | Thiết lập | Tác dụng |
| --- | --- | --- |
| VM | memory trong .wslconfig hoặc giới hạn của backend | Trần RAM guest, bao gồm engine và cache |
| Dịch vụ Compose | --parallel 1 | Chuẩn bị từng image, giảm số thao tác cùng lúc |
| Layer của image | max-concurrent-downloads=1 trong Docker Engine | Giảm số layer tải đồng thời theo cơ chế daemon |
| Cache của WSL | autoMemoryReclaim=gradual trong experimental | Trả dần page cache không còn dùng khi WSL nhàn rỗi |
| Image đã tải | Dùng bản cache tương ứng digest/tag hiệu lực | Tránh tải lại image đã sẵn sàng |

Launcher kiểm tra RAM engine trước khi bắt đầu; việc này không thay cấu hình VM và không theo dõi Working Set liên tục. Trần guest được áp dụng bởi backend. Nếu VM được chỉnh sau bước kiểm tra hoặc Docker context bị đổi, dừng thao tác và chạy lại doctor trước khi chuẩn bị image.

Các adapter giữ thao tác Compose tuần tự; pretix thêm policy missing cho các image dịch vụ và chỉ tải helper khi thiếu đúng digest. Start dùng cache với pull never. Giữ image cache giữa các phiên; tránh prune để xử lý RAM, vì xóa image/build cache trên đĩa sẽ làm phát sinh lượt tải/build tiếp theo. Browser chỉ được chuẩn bị khi chọn robot-init, robot hoặc tùy chọn kiểm thử tương ứng.

## Giảm tải layer đồng thời

Mẫu dùng chung tại [docker-engine-image-transfers.json](../../config/docker-engine-image-transfers.json):

```json
{
  "max-concurrent-downloads": 1,
  "max-concurrent-uploads": 1
}
```

Downloads áp dụng khi pull; uploads áp dụng khi push, không giảm đỉnh RAM của pull. Các giới hạn này giảm đồng thời, không quy định số byte RAM và không thay giới hạn VM. Hiệu lực còn phụ thuộc phiên bản engine và image store/backend; kiểm tra tiến độ cùng số đo sau áp dụng. Các thao tác bên ngoài launcher trên cùng engine vẫn có thể phát sinh thêm tải.

Với Docker Desktop:

1. Lưu lại JSON hiện có tại Settings → Docker Engine để hoàn tác.
2. Gộp hai khóa từ mẫu vào JSON hiện có; giữ các khóa khác, không tạo khóa trùng.
3. Dừng công việc Docker liên quan, chọn Apply & restart, đợi engine sẵn sàng.
4. Chạy doctor rồi setup cho app đã chọn. Quan sát lượt tải mới; kiểm tra dung lượng đĩa nếu giải nén chậm hoặc báo lỗi.

Với Docker Engine tự quản lý, cập nhật daemon.json trên chính máy engine và khởi động lại theo cách quản lý dịch vụ của máy đó. Không dùng đường dẫn cấu hình Windows Engine để sửa Docker Desktop Linux engine. Phục hồi JSON đã lưu và restart nếu cấu hình không được chấp nhận.

Mẫu là cấu hình do người vận hành gộp chủ động; setup giữ nguyên thiết lập engine và WSL của máy.

## Thu hồi cache sau tác vụ

WSL 2 dùng [mẫu có autoMemoryReclaim](../helps/templates/wsl-vm-memory-limit.wslconfig), với hướng dẫn sao lưu, gộp section, restart và hoàn tác tại [WSL_VM_MEMORY_LIMIT](../helps/WSL_VM_MEMORY_LIMIT.md). Gradual thu hồi cache theo từng phần khi nhàn rỗi; dropCache thu hồi nhanh hơn theo cơ chế của WSL. Chọn gradual rõ ràng có thể trả cache chậm hơn một cấu hình đã dùng dropCache.

Đỉnh khi pull đang hoạt động cần trần VM và giảm tải đồng thời. Thu hồi cache chỉ giải quyết phần bộ nhớ có thể trả lại. Swap sử dụng đĩa, không phải RAM bổ sung miễn phí; tăng swap không thay thế việc chọn ngân sách ứng dụng phù hợp.

Resource Saver trên backend WSL chủ yếu giảm CPU khi Docker nhàn rỗi; dùng autoMemoryReclaim để xử lý RAM cache. Không tự chạy drop_caches, shutdown WSL hoặc prune toàn engine trong setup; các thao tác này ảnh hưởng workload dùng chung.

## Đọc và xác nhận số đo

| Phép đo | Ý nghĩa |
| --- | --- |
| docker info / MemTotal | RAM engine có thể sử dụng; không phải mức RAM đang dùng |
| docker stats / resources --app | Bộ nhớ container; không bao quát toàn bộ daemon, pull/build và VM cache |
| Task Manager / Working Set VmmemWSL | RAM Windows hạch toán cho VM, gồm workload WSL cùng chia sẻ và chi phí liên quan |

Ghi phiên bản WSL/Docker, backend/context, mốc/dung sai, memory và chế độ reclaim; so sánh trước tác vụ, đỉnh lúc pull/build và sau khi đã down app rồi để WSL nhàn rỗi. Giữ cùng trạng thái image cache và workload khi so sánh; lượt pull mới và lượt dùng cache có chi phí khác nhau. Khi RAM cao kéo dài, kiểm tra các distro/container khác trước khi thay ngân sách.

Kết quả đo theo môi trường và phiên bản nằm trong nhật ký kiểm chứng (lưu riêng trong bản bàn giao đầy đủ). Giá trị trần VM không phải cam kết Working Set của toàn hệ thống sẽ bằng đúng con số đó.

Tham khảo: [Docker resource constraints](https://docs.docker.com/engine/containers/resource_constraints/), [WSL configuration](https://learn.microsoft.com/en-us/windows/wsl/wsl-config), [Docker Desktop WSL](https://docs.docker.com/desktop/features/wsl/), [Docker daemon transfer limits](https://docs.docker.com/reference/cli/dockerd/), [Compose parallelism](https://docs.docker.com/reference/cli/docker/compose/), [Compose pull policy](https://docs.docker.com/reference/cli/docker/compose/pull/), [Resource Saver trên WSL](https://docs.docker.com/desktop/use-desktop/resource-saver/).

[NAVIGATION](../NAVIGATION.md)
