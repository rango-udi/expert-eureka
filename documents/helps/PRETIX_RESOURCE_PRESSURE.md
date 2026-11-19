[NAVIGATION](../NAVIGATION.md)

# 🆘 Pretix: RAM cao, đĩa bận và mất kết nối engine

## Trước khi chạy

Pretix có web, queue worker, database, Redis, mail và gateway. Pull, giải nén, migration và khởi động có chi phí khác nhau; tổng trần container không phải trần toàn engine hoặc bộ nhớ Windows. Đọc [MEMORY](../guides/MEMORY.md), kiểm tra giới hạn VM có hiệu lực bằng doctor và đóng workload không cần thiết.

Các lệnh tạo tải yêu cầu xác nhận riêng cho từng lần gọi. Terminal tương tác yêu cầu gõ `pretix`; batch/CI hoặc terminal chuyển hướng cần cờ tường minh:

```bat
cmdc.cmd setup --app pretix --accept-pretix-risk
```

Setup đã khởi động stack; dùng start --app pretix --accept-pretix-risk cho lần mở lại sau stop/down. Muốn setup rồi chạy suite mặc định luôn, thêm --run-tests. Không cần tách các dịch vụ bằng tay cho luồng thông thường; thứ tự khởi động có kiểm tra RAM đã được launcher thực hiện.

Cờ xác nhận rủi ro không thay thế `--yes` của thao tác phá hủy và không bỏ qua ownership, khóa, ngưỡng RAM engine hoặc dự phòng host. Không lưu chấp thuận trong .env. Tác vụ bị từ chối hoặc hủy tại bước này chưa gọi Docker.

| Phạm vi | Yêu cầu xác nhận RAM |
| --- | --- |
| setup/bootstrap, start/up/restart, init, robot/robot-init, pull/source | Có |
| env, manage, backup/restore, validate/generate | Có, vì có thể chạy helper hoặc container quản trị |
| doctor, status/resources/logs, urls/config, stop/down | Không; giữ đường chẩn đoán và dừng ứng dụng |
| reset/destroy | Dùng xác nhận xóa --yes theo phạm vi; không cần chấp thuận khởi chạy |

Ảnh Task Manager có thể nhóm Docker Desktop Backend riêng với VmmemWSL. Bộ nhớ tiến trình Windows đó nằm ngoài trần RAM guest và ngoài page cache Linux mà autoMemoryReclaim xử lý. Kiểm tra cả các tiến trình Windows trước khi quy nguyên nhân cho VM:

```powershell
Get-Process -Name com.docker.backend,'Docker Desktop',VmmemWSL,vmmem -ErrorAction SilentlyContinue |
    Select-Object ProcessName,@{Name='WorkingSetMiB';Expression={[math]::Round($_.WorkingSet64 / 1MB)}}
```

Nếu backend Windows tiếp tục tăng RAM khi engine/workload đã dừng, lưu Docker Desktop diagnostics và phiên bản để kiểm tra riêng; không tăng trần container nhằm xử lý bộ nhớ của tiến trình Windows.

## Ngăn khởi động khi host thiếu dự phòng

[pretix-safety.env](../../config/pretix-safety.env) đặt HOST_FREE_MEMORY_MIN_MIB, mặc định 1024 MiB. Đây là ngưỡng dừng phòng ngừa, không phải RAM tối thiểu đo được của Pretix. Windows launcher đọc RAM vật lý còn trống qua CIM; POSIX đọc MemAvailable khi có /proc/meminfo. Khi chạy trong WSL, số Linux thuộc guest: kiểm tra Windows riêng.

Launcher kiểm tra trước thao tác và trước từng bước start dịch vụ. Mỗi dịch vụ khởi động riêng, với no-deps để tránh Compose tự mở rộng khởi động cùng lúc. Kiểm tra giữa bước không phải giám sát liên tục; một bước đang chạy vẫn có thể tăng tải. Không đọc được RAM Windows hoặc thiếu chính sách thì dừng trước tạo tải.

## Profile vận hành giảm tải

| Thiết lập trong apps/pretix/.env | Mặc định và tác động |
| --- | --- |
| EXECUTION_MODE | single: một web worker/thread và Celery solo |
| MEMORY_BUDGET_MIB | 1920 MiB chia thành trần mỗi instance; không cộng thành cgroup chung |
| CONTAINER_SWAP_ALLOWANCE_MIB | 0: đặt memory-swap bằng memory cho container có trần, tránh swap đĩa không kiểm soát |
| RESTART_POLICY | no: giữ dịch vụ lỗi ở trạng thái dừng để kiểm tra, tránh vòng lặp restart |
| PERIODIC_TASKS | manual: start thông thường không chạy scheduler; scheduled bật lại tác vụ định kỳ |

Gateway dùng Nginx riêng; web, worker và cron giữ ứng dụng upstream. PID/CPU và trần RAM được sinh trong compose.resources.yaml. Mỗi one-off có trần riêng, vì vậy chạy thêm một instance có thể tăng tổng sử dụng.

Manual scheduler phù hợp khi không kiểm thử tác vụ định kỳ. Các hành trình hết hạn đơn, dọn dữ liệu hoặc bảo trì cần chạy maintenance rõ ràng, hoặc chọn scheduled và dự phòng thêm tài nguyên:

```bat
cmdc.cmd manage --app pretix --accept-pretix-risk runperiodic
```

Tác vụ manage có thể tạo thêm instance quản trị. Dừng các thành phần không cần thiết trước khi chạy trên máy ít RAM. Đổi ngân sách sau khi đọc log và kiểm tra VM; để MEMORY_BUDGET_MIB rỗng tắt trần container và có thể làm host cạn RAM.

## Khi gặp EOF hoặc engine ngắt kết nối

EOF từ dockerDesktopLinuxEngine là kết nối API kết thúc bất thường. RAM/đĩa quá tải là khả năng cần kiểm tra; thông báo này tự nó chưa xác nhận OOM. Sau lỗi, không tiếp tục setup lặp lại khi máy còn quá tải.

1. Dừng lệnh đang lỗi; kiểm tra RAM khả dụng, đĩa và Docker Desktop diagnostics trên host.
2. Nếu engine chưa phản hồi, đợi host hồi phục rồi mở lại Docker Desktop. Lưu công việc WSL trước mọi thao tác shutdown toàn VM.
3. Khi Docker hoạt động, chạy các lệnh sau:

```bat
cmdc.cmd doctor
cmdc.cmd status --app pretix
cmdc.cmd logs --app pretix
cmdc.cmd resources --app pretix
```

4. Lấy ID container từ status và đối chiếu lý do dừng:

```bat
docker inspect CONTAINER_ID
```

Đọc State.OOMKilled, State.ExitCode, State.Error và log. Exit 137 cũng có thể do bị kill từ nguyên nhân khác. Dùng `cmdc.cmd down --app pretix` để dừng đúng stack; dữ liệu vẫn nằm trong named volume. Nếu có khóa còn lại sau engine gián đoạn, xử lý theo [APP_LIFECYCLE](../guides/APP_LIFECYCLE.md).

Giữ database/media và .env để phục hồi; reset/destroy không phải bước xử lý lỗi engine. Chỉ thử lại sau khi đã chỉnh tài nguyên hoặc chọn workload phù hợp, rồi xác nhận lại cho tác vụ mới.

[NAVIGATION](../NAVIGATION.md)
