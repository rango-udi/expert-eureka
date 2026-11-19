[NAVIGATION](../NAVIGATION.md)

# 🧠 Cấu hình RAM máy ảo WSL cho Docker Desktop

Hướng dẫn giới hạn RAM WSL và thu hồi page cache sau tải/build image. Dùng khi Docker Engine vượt ngưỡng cấu hình hoặc RAM host còn cao sau tác vụ. Đối chiếu số RAM và ngưỡng trong thông báo lỗi để chọn cấu hình phù hợp. Tra ID ứng dụng tại [APPS](../APPS.md).

## 1. Xác định môi trường Docker

Kiểm tra trong PowerShell:

```powershell
wsl --version
docker context show
docker info --format '{{.OSType}}'
docker info --format '{{.MemTotal}}'
```

| Môi trường | Nơi đặt giới hạn RAM |
| --- | --- |
| Docker Desktop dùng WSL 2 | `%UserProfile%\.wslconfig` theo các bước bên dưới |
| Docker Desktop dùng Hyper-V | Settings → Resources → Advanced, khi có tùy chọn Memory |
| Docker Engine từ xa | Máy hoặc VM của engine đang được Docker context sử dụng |
| Docker trên Linux hoặc macOS | Cấu hình tài nguyên của host hoặc VM tương ứng; xem [MEMORY](../guides/MEMORY.md) |

autoMemoryReclaim cần WSL hỗ trợ tính năng này; Docker ghi nhận hỗ trợ từ WSL 1.3.10. Nếu bản WSL không nhận khóa, cập nhật bằng `wsl --update`, kiểm tra lại phiên bản rồi khởi động lại theo bước 5.

Docker Desktop cần ở chế độ Linux containers. Backend WSL 2 được xác định tại Settings → General → Use the WSL 2 based engine.

## 2. Chọn mốc và khoảng RAM được chấp nhận

Đọc `HOST_MEMORY_TARGET_MIB` và `HOST_MEMORY_TOLERANCE_MIB` tại [config/host-memory.env](../../config/host-memory.env), đồng thời kiểm tra các biến cùng tên đã đặt trong terminal. Cận trên bằng mốc cộng dung sai. Chọn RAM VM từ mốc đến cận trên, gồm cả hai đầu.

Ví dụ: mốc 1800 MiB và dung sai 300 MiB cho phép chọn VM 1900, 2000 hoặc 2100 MiB. Đây chỉ là ví dụ về khoảng cấu hình; dùng giá trị phù hợp với project của bạn. Trường hợp engine báo thấp hơn mốc được cảnh báo để theo dõi khả năng đáp ứng workload, thay vì coi mốc là yêu cầu RAM tối thiểu.

Xem [MEMORY](../guides/MEMORY.md) để phân biệt mốc kiểm tra engine, trần container và giới hạn VM. GB là đơn vị thập phân; GiB/MiB là đơn vị nhị phân. Nhập cấu hình launcher bằng số nguyên MiB.

## 3. Sao lưu cấu hình WSL

Trong PowerShell:

```powershell
$wslConfigPath = Join-Path $env:USERPROFILE '.wslconfig'
if (Test-Path -LiteralPath $wslConfigPath) {
    $wslBackupPath = "$wslConfigPath.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Copy-Item -LiteralPath $wslConfigPath -Destination $wslBackupPath -ErrorAction Stop
    Write-Host "Backup saved: $wslBackupPath"
}
notepad.exe $wslConfigPath
```

Ghi lại đường dẫn backup để phục hồi khi cần. Lưu cấu hình dưới tên `.wslconfig`, kiểu văn bản UTF-8. Bật hiển thị phần mở rộng tên file trong Explorer để kiểm tra tên chính xác.

## 4. Áp dụng mẫu cấu hình

[Mẫu có sẵn](templates/wsl-vm-memory-limit.wslconfig) minh họa VM 2 GiB. Trước khi áp dụng, thay `memory` bằng mức đã chọn trong khoảng chấp nhận của project:

```ini
[wsl2]
memory=2048MB
processors=1
swap=1024MB

[experimental]
autoMemoryReclaim=gradual
```

| Khóa | Ý nghĩa trong mẫu |
| --- | --- |
| memory | Giới hạn RAM guest WSL 2 ở 2048 MiB |
| processors | Một CPU ảo cho kiểm thử tuần tự |
| swap | 1024 MiB trao đổi trên đĩa; tách khỏi trần RAM vật lý |
| autoMemoryReclaim | Thu hồi page cache không còn dùng theo từng phần khi WSL nhàn rỗi |

Với file đã có cấu hình, cập nhật các khóa trong `[wsl2]` và `[experimental]` hiện hữu, giữ các thiết lập khác. Mỗi section và khóa cần có một giá trị rõ ràng.

`gradual` chọn cách trả cache từ từ. `dropCache` là lựa chọn thu hồi cache nhanh hơn khi cơ chế nhàn rỗi được kích hoạt; chọn theo phiên bản WSL và hiệu năng của workload. `disabled` tắt thu hồi tự động. Việc đặt gradual không có nghĩa tiết kiệm RAM hơn dropCache đã có trên máy.

Thu hồi cache không đặt trần RAM và không ép giảm bộ nhớ đang hoạt động của Docker. Khi pull/giải nén đang bận, RAM vẫn có thể tăng tới trần VM. Để hạn chế đỉnh tải image, kết hợp memory với giới hạn tải đồng thời trong [MEMORY](../guides/MEMORY.md). Không đặt khóa experimental vào section wsl2.

Mẫu này dành cho Docker Desktop dùng WSL 2. Với Docker daemon tự cài trong distro, kiểm tra tương thích WSL/cgroup trước khi chọn gradual; không áp dụng mẫu Desktop trực tiếp cho backend khác.

Với file chưa tồn tại, dùng lệnh sau từ thư mục project:

```powershell
$wslConfigPath = Join-Path $env:USERPROFILE '.wslconfig'
if (Test-Path -LiteralPath $wslConfigPath) {
    throw 'A WSL config already exists. Back it up and merge the sample manually.'
}
Copy-Item -LiteralPath '.\documents\helps\templates\wsl-vm-memory-limit.wslconfig' -Destination $wslConfigPath -ErrorAction Stop
```

## 5. Khởi động lại WSL và Docker Desktop

Cấu hình áp dụng cho toàn bộ WSL 2 của tài khoản Windows. Lưu công việc trong các distro trước khi thực hiện:

1. Dừng project bằng `cmdc.cmd down --app <id>`.
2. Chọn Quit Docker Desktop tại system tray.
3. Chạy `wsl --shutdown` trong PowerShell hoặc CMD.
4. Mở lại Docker Desktop và chờ engine sẵn sàng.

Việc khởi động lại VM là điều kiện để WSL đọc cấu hình mới.

## 6. Kiểm tra và khởi tạo project

Kiểm tra RAM engine cùng mốc, dung sai và cận trên hiệu lực:

```powershell
.\cmdc.cmd doctor
```

Với kết quả nằm trong khoảng chấp nhận, tiếp tục:

```powershell
$appId = Read-Host 'Application ID (see cmdc apps)'
.\cmdc.cmd setup --app $appId
.\cmdc.cmd resources --app $appId
```

Sau lượt pull/build, so sánh mức dùng khi tác vụ đang chạy và khi đã dừng project bằng down. Chờ WSL nhàn rỗi rồi quan sát Working Set trên Windows:

```powershell
Get-Process -Name VmmemWSL,vmmem -ErrorAction SilentlyContinue |
    Select-Object ProcessName,@{Name='WorkingSetMiB';Expression={[math]::Round($_.WorkingSet64 / 1MB)}}
```

Các distro, container hoặc tác vụ nền khác cùng VM có thể tiếp tục dùng RAM và làm chậm điều kiện thu hồi. Đánh giá hiệu quả bằng số đo trước/sau trong cùng workload; không lấy docker info làm chỉ số RAM đang dùng hoặc bằng chứng cache đã được trả về Windows.

Nếu engine vẫn vượt ngưỡng, kiểm tra Docker context, backend, tài khoản Windows, tên `.wslconfig`, các section trùng và bước khởi động lại VM.

RAM engine, mức dùng của container và Working Set VmmemWSL là các phép đo khác nhau. Windows có thể hạch toán thêm chi phí ngoài RAM guest. Trần container cũng có phạm vi riêng so với tài nguyên dùng để tải và giải nén image; xem [MEMORY](../guides/MEMORY.md).

## 7. Hoàn tác

Dừng project, lưu công việc WSL và Quit Docker Desktop. Phục hồi `.wslconfig` từ đúng đường dẫn backup ở bước 3. Nếu ban đầu chưa có file, xóa file đã tạo trong quá trình cấu hình. Khởi động lại WSL/Docker theo bước 5 rồi kiểm tra RAM engine và mốc/dung sai launcher tương ứng.

## Tham khảo

[Microsoft: cấu hình WSL](https://learn.microsoft.com/en-us/windows/wsl/wsl-config), [Docker Desktop WSL 2 và autoMemoryReclaim](https://docs.docker.com/desktop/features/wsl/), [Microsoft: cơ chế gradual và tương thích cgroup](https://devblogs.microsoft.com/commandline/windows-subsystem-for-linux-september-2023-update/).

[NAVIGATION](../NAVIGATION.md)
