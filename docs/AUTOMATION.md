# Quy trình tự động lâu dài

Quy định này ưu tiên hơn các ví dụ cũ trong skills. Áp dụng cho mọi ý tưởng video,
kể cả khi người dùng không gõ lệnh `/fk-*`.

Google Flow dùng ID người dùng đặt trong `flowkit-settings.ps1`, được nạp vào
`FLOW_PROJECT_ID` bởi `start-flowkit.ps1` trước khi khởi động backend.
Người dùng chỉ cần sửa dòng `$env:FLOW_PROJECT_ID = '<UUID>'` trong file đó rồi
khởi động lại. Không sửa mã Python hoặc các tài liệu để đổi ID.
Codex phải đọc `GET /api/flow/status` để lấy ID có hiệu lực của backend đang chạy;
file cấu hình có thể đã được sửa nhưng chưa restart. Không lấy ID từ kế hoạch cũ,
lịch sử hội thoại hay ví dụ trong tài liệu. Không tự sửa file cấu hình để chuyển đích.
Không tạo Google project hoặc dùng project-level override khác cấu hình hiện hành.
`POST /api/projects` chỉ tạo bộ phim nội bộ với UUID riêng, không gọi Google.
ID project nội bộ dùng trong queue và API quản lý; FlowProvider chuyển sang ID cấu hình
ngay trước khi gọi FlowClient. Direct `/api/flow/*` để trống ID đích hoặc dùng đúng ID
đọc từ status. Không nhầm UUID phim nội bộ với ID Google.
Session không luân chuyển, không đọc lại ID session cũ trên đĩa.
Thiếu ID, ID không phải UUID hoặc override sai khiến request bị chặn, không fallback.
Đổi ID không đổi khóa chính, không di chuyển/xóa media Google hay các phim đã có.
Media cũ vẫn giữ nguyên metadata; nếu một tác vụ cũ cần project nguồn để truy cập,
báo rõ thay vì tự chuyển project hoặc tạo lại media. Approval đã lưu không bị reset
chỉ vì người dùng đổi cấu hình; kế hoạch sáng tạo và hạn mức đã duyệt vẫn áp dụng.

## A — Lập kế hoạch, không tiêu tín dụng

1. Gộp kiểm tra chỉ đọc: `/health`, `/api/flow/status`, `/api/providers/status`,
   `/api/materials`. Kiểm tra cả flow_project_id lẫn session_project.project_id.
   Hai ID phải bằng nhau và session phải `pinned: true` (khóa theo cấu hình hiện hành).
   Nếu cấu hình trên đĩa khác status, giải thích cần restart trước khi dùng đích mới.
2. Đọc `/fk-research` và nghiên cứu web trước khi viết nội dung thực tế. Không bịa sự kiện.
   Với truyện hư cấu, ghi rõ hư cấu; không biến chi tiết tưởng tượng thành sự kiện thật.
3. Tự chọn câu chuyện tiếng Việt, material, tỷ lệ, thời lượng, số cảnh, entities,
   prompt ảnh hành động, video_prompt theo các đoạn 0–3/3–6/6–8 giây, lời kể,
   âm thanh và kế hoạch ghép. Nêu model/provider, số lượt reference/ảnh/video,
   hạn mức retry và dự toán tín dụng (ghi chưa xác định nếu API không có giá),
   output MP4 và các tùy chọn có chi phí. Không tự thêm 4K/TTS trả phí.
4. Có thể tạo metadata nội bộ (project/video/scenes), không tạo request media,
   TTS, nhạc, review trả phí hay upload/publish trong giai đoạn A.
5. Lưu kế hoạch đầy đủ tại `.omc/research/<local-project-id>-plan.json` và
   `PUT /api/automation/plans/<local-project-id>` với JSON `{"plan": {...}}`.
   Lưu cả revision trả về; trình bày kế hoạch một lần và chờ người dùng nói **DUYỆT**.
   Không tự suy ra xác nhận từ việc người dùng im lặng hoặc yêu cầu sửa mã nguồn.

## B — Thực thi sau DUYỆT

1. Chỉ sau tin nhắn DUYỆT, gọi
   `POST /api/automation/plans/<local-project-id>/approve` với
   `{"revision":"<revision đã trình bày>","confirmation":"DUYỆT"}`.
   Đây là xác nhận của toàn bộ kế hoạch. API lưu trạng thái qua restart, không tự sinh media.
   Sửa/lưu lại kế hoạch luôn hủy duyệt; revision cũ không thể duyệt bản mới.
2. Đọc `skills/fk-pipeline.md` và các skill từng giai đoạn cần thiết. Tự chạy nối tiếp:
   references → xác minh mọi media_id UUID → ảnh cảnh → video → review light
   theo kế hoạch → tải file → normalize/concat → MP4, kiểm tra ffprobe.
   Nộp toàn bộ request của mỗi giai đoạn qua `/api/requests/batch`, poll batch-status,
   kiểm tra failed và all_succeeded. Không viết script lặp gửi request, không stagger tay.
3. Queue yêu cầu project nội bộ có kế hoạch đã duyệt; worker kiểm tra lại trước dispatch.
   FlowProvider giữ ngữ cảnh kế hoạch và thay ID Google tại ranh giới provider.
   Direct API có tính phí cần header `X-FlowKit-Plan-Project: <local-project-id>`;
   ID đích Google vẫn phải đúng. Header không phải xác thực người dùng: API này dành
   cho máy cục bộ; agent chỉ gọi approve sau lời duyệt thật trong hội thoại.
4. Tiếp tục sau restart bằng đọc plan và queue; bỏ qua kết quả hoàn thành, không nhân đôi
   request đang chạy. Không hỏi lại quyết định sáng tạo hoặc từng scene.
   Tự sửa lỗi thông thường trong hạn mức đã duyệt (mặc định tối đa 2 lần sửa/tạo lại
   mỗi cảnh, tính cả review). Không tự mở rộng chi phí vượt dự toán/hạn mức.
5. Dừng khi đổi đáng kể kế hoạch/chi phí, bảo mật/quyền hạn, hoặc lỗi cần người dùng
   quyết định. Giữ nguyên unusual-activity cooldown; không tự clear-hijack, đổi tài khoản,
   mạng hoặc tìm cách vượt captcha/sandbox. Không tự gửi thông báo hay xuất bản video.
6. Báo file MP4 cuối cùng và lỗi còn lại. Quy trình do Codex điều phối khi phiên hoạt động;
   không phải dịch vụ tự viết truyện/chạy agent khi Codex đã đóng. Backend giữ queue,
   kế hoạch và approval để phiên sau tiếp tục.

## Khởi động lại sau khi sửa code

Sửa một dòng trong `flowkit-settings.ps1` để chọn một Google Flow project đã tồn tại.
Không chạy setup.py để đổi ID. Dừng đúng backend cũ bằng Ctrl+C rồi chạy từ thư mục repo:

```powershell
.\start-flowkit.ps1
# Chỉ kiểm tra cấu hình, không khởi động hoặc tạo media:
.\start-flowkit.ps1 -CheckConfig
```

Kiểm tra lại health/status; session phải `pinned: true` và đúng ID đã cấu hình. Không tự khởi động
thêm server trùng cổng hoặc tự tiêu tín dụng để thử. Request cũ chưa có plan được chặn;
chỉ tiếp tục sau khi lập và duyệt kế hoạch cho project nội bộ tương ứng.
