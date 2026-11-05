# FLOWKIT CUSTOM — HƯỚNG DẪN CÀI ĐẶT VÀ SỬ DỤNG

**Bộ tài liệu bàn giao dành cho khách hàng / người thuê bản FlowKit tùy chỉnh**  
**Nền tảng:** Windows 10/11 · PowerShell · Google Chrome · Google Flow · Codex CLI  
**Phiên bản tài liệu:** 1.0 · Ngày 05/11/2026  
**Đơn vị cung cấp:** `VŨ ĐỨC TIẾN`  
**Liên hệ hỗ trợ:** `vdtien19.dev@gmail.com`  
**Kho mã nguồn bản tùy chỉnh:** `https://github.com/VDTien19/flowkit-studio`  
**Kho mã nguồn tác giả:** `https://github.com/crisng95/flowkit`

> **Đọc trước khi cài:** Đây là hướng dẫn sử dụng **bản FlowKit đã được tùy chỉnh** với tính năng cấu hình một Google Flow Project ID tại `flowkit-settings.ps1`, khởi động bằng `start-flowkit.ps1`, và quy trình Codex **lập kịch bản → khách duyệt → chạy pipeline → xuất MP4**. **Không clone nhầm FlowKit gốc**: kho gốc không tự chứa các tùy chỉnh này. Người cung cấp phải cấp đúng repository/ZIP của bản đã sửa và kiểm tra bản phát hành trước khi bàn giao.

---

## 01 · GIỚI THIỆU NHANH

**FlowKit Custom** giúp người dùng tạo video AI nhiều cảnh từ một yêu cầu bằng tiếng Việt, mà không cần tự viết JSON hay gọi API thủ công. Bộ công cụ gồm:

| Thành phần | Công việc |
|---|---|
| **Codex CLI** | Đọc ý tưởng, lập kịch bản, chia cảnh, lập kế hoạch và điều phối các skill |
| **FlowKit Backend** | Nhận yêu cầu, lưu dự án/cảnh, điều phối tác vụ; chạy tại `127.0.0.1:8100` |
| **Google Flow + Chrome Extension** | Tạo ảnh và video bằng tài khoản Google Flow **của người sử dụng** |
| **Dashboard** | Theo dõi dự án, cảnh và trạng thái tại `localhost:5173` |
| **FFmpeg** | Chuẩn hóa, ghép các clip và tạo file MP4 |

**Một video đi qua 6 bước:** Gõ ý tưởng → Codex đề xuất kịch bản → **DUYỆT** → Tạo ảnh/clip qua Google Flow → Ghép video → Nhận MP4.

**Hai loại project:**

- **Google Flow Project ID:** UUID dự án thật trên `flow.google.com`. Bản tùy chỉnh ghim ID này để các request gửi đúng dự án đã chọn.
- **FlowKit Project ID:** Mã dự án nội bộ để quản lý từng bộ phim trong Dashboard. Mỗi bộ phim có thể có một ID nội bộ riêng nhưng cùng dùng Google Flow Project ID đã cấu hình.

**Giới hạn cần biết:** FlowKit không bảo đảm tạo video thành công 100%; kết quả phụ thuộc vào tình trạng tài khoản, tín dụng, hạn mức, chính sách và khả năng phản hồi của Google Flow. Codex cũng có hạn mức sử dụng riêng. Dashboard là bảng quản lý, không phải trình dựng timeline đầy đủ như CapCut.

## 02 · YÊU CẦU TRƯỚC KHI CÀI

### 2.1. Máy tính và tài khoản

- Windows 10 hoặc Windows 11; có quyền cài phần mềm và kết nối Internet ổn định.
- Tài khoản **Google Flow** riêng, đã có quyền tạo ảnh/video và dự án Google Flow hợp lệ.
- Tài khoản **ChatGPT có quyền dùng Codex** hoặc phương thức đăng nhập Codex phù hợp; hạn mức phụ thuộc tài khoản.
- Chrome đã đăng nhập tài khoản Google dự định sử dụng trong FlowKit.
- Đủ dung lượng ổ đĩa cho các video đầu ra; không có mức dung lượng cố định cho mọi dự án.

### 2.2. Phần mềm phải có

| Phần mềm | Kiểm tra trong PowerShell | Ghi chú |
|---|---|---|
| Git | `git --version` | Clone/nhận cập nhật |
| Python **3.10+** | `py --version` | Backend; cần `pip`, `venv` |
| Node.js + npm | `node -v` · `npm -v` | Dashboard và Codex CLI |
| FFmpeg + ffprobe | `ffmpeg -version` · `ffprobe -version` | Ghép MP4 |
| Google Chrome | Mở trình duyệt | Chạy extension và tab Flow |
| VS Code (khuyên dùng) | Mở ứng dụng | Dễ quản lý nhiều Terminal |

**Nơi tải:** Git — https://git-scm.com/ · Python — https://www.python.org/downloads/ · Node.js — https://nodejs.org/ · FFmpeg — https://ffmpeg.org/download.html · VS Code — https://code.visualstudio.com/ . Sau khi cài, **đóng và mở lại PowerShell** để cập nhật `PATH`.

> **Quan trọng:** Toàn bộ lệnh trong tài liệu dùng **PowerShell**, có dấu nhắc tương tự `PS C:\FlowKit>`. Không dán lệnh PowerShell vào Git Bash `MINGW64`; đặc biệt không chạy `./start-flowkit.ps1` trực tiếp trong Bash.

## 03 · NHẬN BẢN FLOWKIT CUSTOM VÀ CLONE MÃ NGUỒN

**Bước 1 — Nhận quyền truy cập:** Người cung cấp gửi cho bạn URL repository **đúng bản tùy chỉnh** và quyền đọc repo nếu repo đặt ở chế độ riêng tư. Nếu nhận file ZIP, giải nén vào thư mục không có ký tự lạ, ví dụ `C:\FlowKit`.

**Bước 2 — Clone:** Mở PowerShell, thay URL mẫu bằng URL đã được cấp:

```powershell
# Chọn thư mục khác nếu ổ C không phù hợp
 git clone "<URL_REPOSITORY_CUA_BAN>" "C:\FlowKit"
 cd C:\FlowKit
```

**Bước 3 — Xác nhận đúng bản:** Kiểm tra các file:

```powershell
Test-Path .\requirements.txt
Test-Path .\start-flowkit.ps1
Test-Path .\flowkit-settings.ps1
Test-Path .\dashboard\package.json
Test-Path .\extension
Test-Path .\AGENTS.md
```

Các kết quả cần thiết phải là `True`. Nếu thiếu `start-flowkit.ps1` hay `flowkit-settings.ps1`, **dừng lại và liên hệ bên cung cấp**: có thể bạn đã clone nhầm repo gốc hoặc nhận thiếu file. Nếu bản phát hành chỉ cung cấp `flowkit-settings.example.ps1`, hãy sao chép bản mẫu theo chỉ dẫn của bên cung cấp trước khi tiếp tục.

> **Không nhập URL kho gốc rồi kỳ vọng bản tùy chỉnh xuất hiện.** Kho upstream tham khảo: https://github.com/crisng95/flowkit . Đây không phải link phát hành riêng của người cung cấp tài liệu này.

## 04 · CÀI THƯ VIỆN PYTHON, DASHBOARD VÀ CODEX

Mở **PowerShell** trong thư mục `C:\FlowKit`:

### 4.1. Python Backend

```powershell
cd C:\FlowKit
py -m venv venv
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Các lệnh trên tạo môi trường Python riêng cho dự án. Nếu máy không nhận `py`, kiểm tra Python/PATH; không cần cài lặp lại nhiều bản Python một cách tùy tiện.

### 4.2. Giao diện Dashboard

```powershell
cd C:\FlowKit\dashboard
npm ci
```

Nếu repository không có `package-lock.json` tương ứng, thử `npm install`. Khi cài hoàn tất, quay về thư mục gốc:

```powershell
cd C:\FlowKit
```

### 4.3. Codex CLI (AI Agent)

```powershell
npm install -g @openai/codex
codex --version
codex login
```

Đăng nhập theo màn hình trình duyệt của Codex. Nếu dùng mã thiết bị, làm theo hướng dẫn hiển thị trong Terminal; không chia sẻ mã đăng nhập hay cookie với người khác. Lần đăng nhập đầu có thể yêu cầu cấu hình sandbox/cho phép lệnh. **Không chọn chế độ bỏ toàn bộ bảo vệ chỉ để tránh hộp thoại.**

**Lưu ý về chi phí:** Tín dụng Google Flow dùng để tạo ảnh/video; hạn mức Codex/ChatGPT là cơ chế độc lập. Cài phần mềm không tự cấp sẵn tín dụng Google Flow hoặc quyền dùng Codex.

## 05 · CÀI EXTENSION VÀ ĐĂNG NHẬP GOOGLE FLOW

1. Mở Chrome tại `chrome://extensions`.
2. Bật **Developer mode / Chế độ dành cho nhà phát triển**.
3. Nhấn **Load unpacked / Tải tiện ích đã giải nén**.
4. Chọn thư mục `C:\FlowKit\extension` (không chọn file `README.md`).
5. Bật Extension; khi có bản cập nhật extension, nhấn **Reload** tại trang extensions.
6. Mở `https://flow.google.com/` và đăng nhập **tài khoản Google của bạn**.
7. Tạo một project Google Flow theo giao diện Google, hoặc mở project đã có. **Để tab Flow mở** trong suốt quá trình tạo media.

**Lấy Google Flow Project ID:** Từ URL dự án, sao chép UUID trong phần `/project/<UUID>`. ID của mỗi người dùng là khác nhau; không dùng ID của bên cung cấp.

## 06 · CẤU HÌNH GOOGLE FLOW PROJECT ID — CHỈ SỬA MỘT FILE

Bản FlowKit Custom được bàn giao nhằm cho phép người dùng tự đổi dự án Google Flow, **không cần Codex sửa mã nguồn**.

**Bước 1 — Mở cấu hình:**

```powershell
notepad C:\FlowKit\flowkit-settings.ps1
```

**Bước 2 — Nhập ID project của chính bạn:**

```powershell
$env:FLOW_PROJECT_ID = "PASTE_UUID_GOOGLE_FLOW_CUA_BAN_VAO_DAY"
```

Lưu file. Đừng ghi ID tùy ý; project Google Flow đó phải tồn tại và thuộc tài khoản đang đăng nhập trên Chrome.

**Bước 3 — Khởi động Backend (xem Mục 07), sau đó kiểm tra:**

```powershell
Invoke-RestMethod http://127.0.0.1:8100/api/flow/status
```

Kỳ vọng ở **bản đã kiểm chứng của bên cung cấp**: `connected: true`; `flow_project_id` là UUID đã nhập; `session_project.project_id` trùng UUID; `session_project.pinned: true`; `transport: batch`. `flow_key_present: false` là bình thường trong cơ chế mới. Nếu các trường khác nhau, **chưa tạo video** và kiểm tra lại cấu hình, file khởi động và tab Flow.

**Đổi ID về sau:** sửa `flowkit-settings.ps1` → lưu → dừng Backend bằng `Ctrl + C` → khởi động lại Backend → kiểm tra `/api/flow/status`. **Không phải chèn ID trong mỗi prompt video.** Các mã UUID xuất hiện trong `tests/` có thể chỉ là dữ liệu thử nghiệm, không phải nơi cấu hình chạy thực tế.

## 07 · KHỞI ĐỘNG MỖI NGÀY — 3 TERMINAL, 1 TAB GOOGLE FLOW

Sau mỗi lần tắt máy/đóng các Terminal, người dùng chạy lại theo thứ tự này. **Giữ cửa sổ Backend và Dashboard đang chạy.**

### Terminal A — Backend (PowerShell)

```powershell
cd C:\FlowKit
.\start-flowkit.ps1
```

Script tùy chỉnh dự kiến nạp `flowkit-settings.ps1` rồi chạy FastAPI/Uvicorn trên `127.0.0.1:8100`. **Không chạy thêm `python -m agent.main` trong Terminal khác**: hai Backend sẽ tranh cổng 8100.

Nếu Windows chặn PowerShell script, xem hướng dẫn PowerShell Execution Policy trong phần xử lý lỗi; tránh tắt bảo vệ toàn hệ thống.

### Terminal B — Dashboard (PowerShell)

```powershell
cd C:\FlowKit\dashboard
npm run dev
```

Mở `http://localhost:5173`. Nếu Vite hiện URL/cổng khác, dùng đúng URL in trong Terminal.

### Terminal C — Codex (PowerShell)

```powershell
cd C:\FlowKit
codex
```

Cho Codex truy cập đúng thư mục dự án khi được hỏi. Chỉ chấp thuận các quyền/phạm vi mà bạn hiểu. Phiên làm việc có thể có hộp thoại cho phép chạy lệnh; đây là bảo vệ riêng, không phải bước duyệt kịch bản.

### Mở tab Google Flow

Mở `https://flow.google.com/` trên Chrome đã cài Extension, vào project đã chọn; **không đóng tab khi pipeline đang tạo media**.

### Kiểm tra nhanh

```powershell
Invoke-RestMethod http://127.0.0.1:8100/health
Invoke-RestMethod http://127.0.0.1:8100/api/flow/status
```

Nếu Backend trả `status: ok`, kết nối Flow `connected: true` và ID trùng cấu hình thì có thể chuẩn bị dự án.

## 08 · TẠO VIDEO KHÔNG CẦN JSON — CHỈ NHẬP Ý TƯỞNG

### Giai đoạn 1 — Giao ý tưởng, chưa tiêu tín dụng

Trong ô chat Codex, nhập yêu cầu ngắn bằng tiếng Việt, ví dụ:

```text
Sử dụng các skills của FlowKit để tạo video dọc 9:16 dài khoảng 1 phút,
chủ đề món thịt cuốn lá lốt chiên trong căn bếp hiện đại.
Không có người hoặc bàn tay; nguyên liệu tự di chuyển và tự chế biến.
Phong cách chân thực, camera cố định trong từng clip, không nhạc nền.

Hãy tự nghĩ câu chuyện, chia cảnh, tạo nhân vật/đạo cụ tham chiếu và
kế hoạch pipeline. Chỉ dùng Google Flow Project ID đang cấu hình.
Đưa kịch bản và phạm vi tác vụ cho tôi xem; CHƯA tạo ảnh hoặc video.
```

Codex cần trả về tên dự án, danh sách cảnh, thời lượng, các hình ảnh/nhân vật cần nhất quán và kế hoạch thực hiện. Bạn có thể trả lời **“SỬA…”** nếu kịch bản chưa phù hợp.

### Giai đoạn 2 — Duyệt một lần

Sau khi kiểm tra nội dung, nếu đồng ý, gửi:

```text
DUYỆT. Hãy sử dụng kế hoạch vừa được duyệt và tự chạy các bước còn lại
trong phạm vi quyền đã cấp; không hỏi lại từng cảnh hoặc quyết định
sáng tạo thông thường. Không tạo Google Flow project mới.
Dừng ngay nếu phát sinh lỗi unusual_activity hoặc cần thay đổi đáng kể.
```

Bản tùy chỉnh hướng tới việc Codex tự tạo reference → ảnh cảnh → clip → xử lý lỗi thông thường → ghép MP4. **“DUYỆT” là xác nhận kịch bản; không thay thế cơ chế cấp quyền bảo mật của Codex hoặc sự chấp thuận khi thay đổi đáng kể phạm vi/chi phí.**

### Cách biết Codex đã xong một lượt

Lượt Codex thường kết thúc khi có phần tổng kết, thời gian làm việc và ô nhập `Ask Codex to do anything` xuất hiện lại. **Kết thúc một lượt trả lời không đồng nghĩa đã có MP4**: đọc trạng thái dự án và file kết quả trước khi đánh dấu hoàn tất.

### Kết quả cuối và vị trí tệp

Codex phải báo rõ đường dẫn MP4 thực tế (thường trong thư mục `output/`, nhưng tên và vị trí tùy dự án), thời lượng và các cảnh đã hoàn thành. Mở MP4 để nghe/xem, đối chiếu khung 9:16, thứ tự cảnh và âm thanh. Không suy đoán đường dẫn tệp khi chưa được báo cáo.

## 09 · TIẾP TỤC DỰ ÁN CŨ, KHÔNG TẠO TRÙNG

Nếu đóng Codex, mất kết nối hoặc pipeline dừng, mở lại Backend/Chrome/ Codex rồi nhập:

```text
Hãy tìm dự án FlowKit gần nhất đã được tôi DUYỆT nhưng chưa xuất MP4.
Kiểm tra database và trạng thái từng scene/request. Tiếp tục từ phần
chưa hoàn thành, không tạo lại project, scene, reference hoặc clip đã xong.
Chỉ dùng Google Flow Project ID đang cấu hình. Dừng khi Google chặn.
```

Dự án nội bộ vẫn tồn tại trong SQLite nếu database không bị xóa. Không dùng thao tác “create project” mới khi chỉ muốn tiếp tục dự án cũ.

**Đổi Google Flow Project ID giữa chừng:** không tự chuyển media/reference của dự án đang dở sang project mới; nên hoàn thành dự án cũ ở project cũ hoặc hỏi bên cung cấp cách di chuyển hợp lệ.

## 10 · CÁCH QUẢN LÝ PROJECT, DASHBOARD VÀ TÍN DỤNG

- **Dashboard:** `http://localhost:5173` để theo dõi các dự án nội bộ FlowKit, tiến trình từng cảnh và các tác vụ có lỗi. Dashboard không phải giao diện bấm nút tạo phim trọn gói; Codex là nơi nhận ý tưởng và điều phối.
- **Google Flow:** `https://flow.google.com/` để theo dõi tài khoản, project Google và lượt tạo media. Số tín dụng, mô hình và hạn mức phụ thuộc Google.
- **Codex:** là AI Agent riêng biệt, dùng quyền truy cập/hạn mức trong tài khoản Codex/ChatGPT của từng người; không phải tín dụng Google Flow.
- **Chi phí và khả năng:** video nhiều cảnh có thể cần nhiều lượt tạo ảnh + clip và có thể có lượt thử lại; không có cam kết một mức tiêu tín dụng cố định cho mọi video.

**An toàn tài khoản:** Không gửi mật khẩu, token, cookie, mã đăng nhập hoặc toàn bộ Chrome profile cho bên hỗ trợ; không cho nhiều khách dùng chung tài khoản Google nếu chưa xác minh quyền sử dụng và điều khoản dịch vụ. Người dùng tự chịu trách nhiệm về nội dung, quyền sử dụng tư liệu và chi phí tài khoản của mình.

## 11 · LỖI THƯỜNG GẶP VÀ CÁCH KHẮC PHỤC

| Triệu chứng | Cách xử lý an toàn |
|---|---|
| `./start-flowkit.ps1: command not found` trong Git Bash | Dùng **PowerShell**: `.\start-flowkit.ps1`; hoặc từ Git Bash: `powershell.exe -NoProfile -File ./start-flowkit.ps1` |
| `Set-Location: command not found` | Đang dùng Bash để đọc script PowerShell; chuyển sang PowerShell |
| `Errno 10048` / cổng `8100` đang dùng | Backend cũ còn chạy. Kiểm tra PID, xác minh đúng Python FlowKit trước khi dừng; **không tắt toàn bộ Python** |
| `/health` không mở được | Backend chưa chạy, lỗi Terminal, firewall hoặc thiếu dependencies |
| `connected: false` | Mở Chrome + tab Flow đã đăng nhập; bật/reload Extension; kiểm tra Backend |
| `NO_FLOW_PROJECT` | Kiểm tra UUID trong `flowkit-settings.ps1`, khởi động lại Backend |
| `flow_project_id` khác cấu hình | Dừng tạo media; xem script có đọc file cấu hình và có ghi đè ID hay không; liên hệ hỗ trợ |
| `node` / `npm` không nhận | Cài Node.js, mở lại Terminal |
| `ffmpeg` hoặc `ffprobe` không nhận | Cài công cụ và cập nhật PATH |
| `unusual_activity` | **Dừng gửi yêu cầu tự động.** FlowKit có cooldown nội bộ; không xóa cooldown hay spam retry. Kiểm tra hoạt động thủ công và chờ khôi phục phù hợp |
| Tạo thủ công được nhưng Extension bị từ chối | Không kết luận tài khoản bị khóa; kiểm tra logs, request/transport, chính sách dịch vụ; tránh cố vượt cơ chế chống lạm dụng |
| Dự án hiện nhưng không có MP4 | Kiểm tra từng request/scene, lỗi FFmpeg và đường dẫn output; chỉ concat khi clip đã hoàn thành |
| Script bị chặn thực thi | Hỏi bên hỗ trợ cách chạy PowerShell với quyền phù hợp; không đổi chính sách bảo mật toàn máy chỉ vì một file chưa xác minh |

**Kiểm tra tiến trình cổng 8100 (PowerShell):**

```powershell
Get-NetTCPConnection -LocalPort 8100 -State Listen |
  Select-Object LocalAddress,LocalPort,OwningProcess
# Thay 12345 bằng PID thực tế, xác minh trước khi dừng
Get-CimInstance Win32_Process -Filter "ProcessId = 12345" |
  Select-Object ProcessId,Name,CommandLine
```

Nếu đúng Backend FlowKit cũ, ưu tiên quay lại Terminal đó và nhấn `Ctrl + C`. Chỉ sử dụng `Stop-Process -Id 12345` sau khi xác nhận đúng tiến trình.

## 12 · CẬP NHẬT PHIÊN BẢN / CÀI LẠI TRÊN MÁY KHÁC

**Trước khi cập nhật:** Sao lưu database `flow_agent.db`, cấu hình `flowkit-settings.ps1` và các tệp đầu ra cần giữ. Chỉ cập nhật từ repository **bản tùy chỉnh được bên cung cấp chỉ định**, không tùy tiện `git pull` từ repo FlowKit gốc để tránh mất các cải tiến. Thực hiện cập nhật khi không có tác vụ đang chạy.

Quy trình cập nhật tham khảo (nếu bên cung cấp đã hướng dẫn nhánh/tag phát hành):

```powershell
cd C:\FlowKit
git status
git pull
.\venv\Scripts\python.exe -m pip install -r requirements.txt
cd dashboard
npm ci
```

Sau đó quay về thư mục gốc, khởi động lại Backend và Dashboard rồi kiểm tra project ID. Nếu có xung đột Git, không chọn “discard all changes” khi chưa biết dữ liệu nào là cục bộ.

**Máy mới:** phải tự cài dependencies, tự thêm extension, tự đăng nhập Google Flow/Codex, tự đặt Project ID. Không chuyển nguyên `venv/`, `node_modules/`, cookies, tài khoản đăng nhập hoặc profile Chrome từ máy khác.

## 13 · QUYỀN SỬ DỤNG VÀ ĐIỀU KIỆN KHI NHẬN BẢN TÙY CHỈNH

**Phần dành cho khách hàng:**

1. Gói phần mềm được bàn giao **không bao gồm** tài khoản/tín dụng Google Flow hay gói ChatGPT/Codex, trừ khi hợp đồng ghi rõ.
2. Khách hàng dùng tài khoản của mình, quản lý dữ liệu dự án và tuân thủ điều khoản của Google, OpenAI và quy định pháp luật có liên quan.
3. Không cung cấp mật khẩu, token, cookie cho nhân viên hỗ trợ; ưu tiên chia sẻ log đã loại bỏ thông tin nhạy cảm.
4. Tính năng, hạn mức và tương thích API bên thứ ba có thể thay đổi theo thời gian. Không bảo đảm mọi yêu cầu đều tạo thành công hoặc hoàn toàn không phải xác nhận quyền.
5. Quyền cập nhật, hỗ trợ, số máy, thời hạn sử dụng và việc có được chia sẻ bản tùy chỉnh cho bên thứ ba hay không phải được ghi trong **thỏa thuận cung cấp/thuê riêng**.

**Phần dành cho nhà cung cấp trước khi thương mại hóa:** Kho FlowKit gốc công bố giấy phép **MIT**, nên khi phân phối bản sửa phải giữ các thông báo bản quyền và điều khoản giấy phép liên quan; kiểm tra quyền của từng thành phần phụ thuộc. **Giấy phép mã nguồn mở không đồng nghĩa Google hoặc OpenAI cho phép bán lại tài khoản, tín dụng hay mọi hình thức tự động hóa**. Cần kiểm tra các điều khoản dịch vụ hiện hành, đặc biệt trước khi bán/cho thuê quyền truy cập nhiều khách, triển khai dịch vụ đám mây hoặc chia sẻ tài khoản. Tài liệu này không phải ý kiến pháp lý. Không quảng bá bản tùy chỉnh là sản phẩm chính thức của Google, OpenAI hoặc tác giả FlowKit gốc.

## 14 · CHECKLIST BÀN GIAO VÀ HỖ TRỢ

### Người dùng mới — kiểm tra trước video đầu tiên

- [ ] Tôi đã nhận **đúng repository/ZIP FlowKit Custom** từ nhà cung cấp.
- [ ] Máy đã nhận Git, Python 3.10+, Node/npm, FFmpeg và ffprobe.
- [ ] Đã cài dependencies Python và Dashboard.
- [ ] Đã cài Codex, đăng nhập tài khoản của mình.
- [ ] Đã Load unpacked Extension, mở tab Google Flow đã đăng nhập.
- [ ] Đã điền UUID project Google Flow **của mình** vào `flowkit-settings.ps1`.
- [ ] Backend và Dashboard chạy; `/health` có `status: ok`.
- [ ] `/api/flow/status` có `connected: true`, đúng ID và `pinned: true`.
- [ ] Codex đã lập kịch bản và tôi đã **DUYỆT** trước khi tiêu tín dụng.
- [ ] MP4 đầu ra đã được mở kiểm tra hình, âm thanh và thời lượng.

### Khi cần gửi yêu cầu hỗ trợ

Gửi **phiên bản bản tùy chỉnh**, hệ điều hành, ảnh lỗi, lệnh đã chạy, `/health`, phần `/api/flow/status` đã loại bỏ ID/chi tiết nhạy cảm nếu cần, tên bước pipeline thất bại, và log liên quan **sau khi xóa token, cookie, thông tin đăng nhập**. Không gửi database chứa dữ liệu riêng nếu không cần thiết.

---

### BẢNG LỆNH NHANH — LƯU ĐỂ DÙNG HẰNG NGÀY

| Việc | Lệnh / địa chỉ |
|---|---|
| Khởi động Backend | `cd C:\FlowKit` → `.\start-flowkit.ps1` |
| Khởi động Dashboard | `cd C:\FlowKit\dashboard` → `npm run dev` |
| Khởi động AI Agent | `cd C:\FlowKit` → `codex` |
| Đổi Google Flow Project ID | Sửa `C:\FlowKit\flowkit-settings.ps1`, sau đó restart Backend |
| Xem Backend | `http://127.0.0.1:8100/health` |
| Xem kết nối / ID | `http://127.0.0.1:8100/api/flow/status` |
| Xem Dashboard | `http://localhost:5173` |
| Mở Google Flow | `https://flow.google.com/` |
| Duyệt kịch bản trong Codex | Nhập `DUYỆT` sau khi xem kế hoạch |
| Kết thúc công việc | Dừng Backend/Dashboard bằng `Ctrl + C` trong Terminal tương ứng |

**Tài liệu tham khảo:** FlowKit upstream README và license: https://github.com/crisng95/flowkit ; trang Codex: https://developers.openai.com/codex/ ; chính sách AI tạo sinh Google: https://policies.google.com/terms/generative-ai/use-policy?hl=vi . **Tính năng của bản tùy chỉnh** được mô tả theo các lần cấu hình/kiểm tra trước khi viết tài liệu; nhà cung cấp phải đối chiếu với tag phát hành thực tế trước khi gửi khách.
