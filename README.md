# DriverGuard — bản Cockpit

Ứng dụng Python chạy local trên Windows cho dự án đại học. Giao diện giám sát được
làm theo mẫu HTML bạn cung cấp: nền tối/cyan, webcam bên trái, đồng hồ nguy cơ bên phải,
EAR/MAR, biểu đồ mắt và nhật ký cảnh báo. Các chỉ số lấy từ bộ xử lý thật, không dùng
FPS, điểm nguy cơ hoặc độ trễ viết sẵn trong template.

## Cách chạy (Windows)

1. Giải nén ZIP **vào thư mục mới** để các file UI/config cùng phiên bản.
2. Nhấp đúp **START_DRIVERGUARD.bat ngay ngoài cùng thư mục vừa giải nén**.
3. Chờ cài thư viện lần đầu. Mở `http://127.0.0.1:8501` nếu Chrome không tự mở.
4. Trong màn hình giám sát, chọn Webcam thật hoặc Demo rồi Bắt đầu phiên.

Cần Python **3.11 hoặc 3.12 bản 64-bit**, không dùng 3.14 với bộ phiên bản này.
Model và âm báo đi kèm, chỉ lần đầu cài thư viện cần mạng. Không cần API key để giám sát.
Khi xong: Dừng & lưu phiên, sau đó Ctrl+C để tắt server.

Nếu dùng VS Code, mở Terminal rồi chạy trong thư mục **có app.py**:

```powershell
cd .\DriverGuard
.\run.bat
```

Nếu đã ở trong thư mục DriverGuard, chỉ cần ` .\run.bat `.
Hoặc chạy thủ công:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

Nếu vùng giám sát không hiện, bấm **Mở màn hình giám sát riêng** bên dưới vùng đó.
Nếu cả app không lên, đọc lỗi trong Terminal; màn hình trắng chưa đủ để biết lỗi cụ thể.
Không mở `ui/assets/live.html` để chạy app: mở file đó chỉ xem bố cục, các nút không kết nối Python.

## Cập nhật từ bản cũ

Đây là **gói đầy đủ**, không ghép thêm DriverGuard_LagFix.zip cũ.
Giữ thư mục cũ để có bản dự phòng. Sau khi hai app đã dừng, có thể copy
`data/driverguard.db` và `assets/screenshots/` từ DriverGuard cũ sang DriverGuard mới để giữ lịch sử.
Schema tự thêm các cột thiếu, không xóa phiên cũ. Phiên cũ vốn lưu số 0 không thể tái tạo dữ liệu đã mất.

## Thay đổi xử lý phần hiển thị

- Streamlit giữ menu, dashboard/history/report/settings.
- `ui/live_bridge.py`: HTTP server nhỏ bằng **thư viện chuẩn Python**, chỉ bind `127.0.0.1`
  với cổng trống tự chọn; các URL có token riêng của tab. Không thêm Flask/FastAPI/Node dependency.
- `/video` gửi luồng JPEG mới nhất trực tiếp tới trình duyệt (MJPEG), tránh URL media của Streamlit.
- `/state` trả JSON chỉ số; JavaScript cập nhật các ô trong DOM 4 lần/giây bằng một request mỗi lần.
- `/command` chuyển Start/Stop/Confirm/Demo vào runtime hiện có. Worker vẫn sở hữu timer,
  Risk Engine, state machine, alarm và SQLite. Mở màn hình riêng vẫn dùng cùng một phiên.
- Màn hình giám sát không rerun nhiều fragment mỗi khung hình và không gửi base64 lớn qua Streamlit.
- Khi mất kết nối, trang hiện thông báo lỗi; có đường mở trực tiếp nếu trình duyệt chặn iframe.
- CSS/JS đi kèm, không cần Tailwind/Chart.js/Google Fonts CDN.

Thư viện chuẩn server nằm trong `ui/` vì chỉ là lớp truyền dữ liệu/hiển thị,
không đưa quyết định an toàn ra JavaScript. Streamlit và video server cùng chạy trên laptop.
Không mở bằng máy khác, không deploy public. Cổng phụ tự tắt khi Python kết thúc bình thường.

## Chức năng

- Webcam OpenCV, MediaPipe Tasks một mặt; xử lý mặt/mắt/miệng/hướng đầu bằng hình học.
- EAR OPEN/CLOSED/UNKNOWN và thời gian nhắm thực tế; không tích lũy nhiều lần chớp mắt.
- MAR + thời gian mở miệng: một lần miệng mở liên tục chỉ ghi một potential yawn.
- **3 ngáp / 60 giây** → **Bạn nên nghỉ ngơi**; threshold chỉnh trong Cấu hình.
- Hướng CENTER/LEFT/RIGHT/DOWN/UP theo tư thế chuẩn; nhìn lệch liên tục 3s → distraction.
- Risk heuristic 0–100, có smoothing; SAFE/WARNING/DROWSY/CRITICAL.
- Mắt nhắm đủ **5s** → alarm + **ARE YOU AWAKE?** + **10s** xác nhận.
- **I'M AWAKE** trước hạn: lưu xác nhận, reset timer mắt, hủy leo thang.
  Phải quan sát mắt mở đủ 1s trước khi tái kích hoạt để tránh retrigger từ trạng thái cũ.
- Hết hạn: **EMERGENCY SIMULATION**, snapshot webcam + sự kiện/điểm/timestamp vào SQLite.
  Snapshot lỗi không làm mất cả sự kiện. Demo không tạo snapshot giả.
- Alarm Windows bất đồng bộ; nút Âm báo bật/tắt trong giao diện mới.
- Thống kê duration/average theo thời gian/max/counters; checkpoint và chốt khi dừng/lỗi.
- Dashboard, lịch sử/risk timeline/snapshots, báo cáo cục bộ hoặc Gemini optional sau phiên.
- Demo đi qua cùng detector timers, risk, confirmation và persistence; không sửa số liệu UI trực tiếp.

Ngưỡng mặc định: EAR đóng .20/mở .23, MAR mở .35/đóng .25, miệng mở >=1.2s.
Tư thế chuẩn lấy khi mặt xuất hiện đầu tiên; nhìn thẳng trước khi bắt đầu hoặc nhấn đặt hướng.
Nói chuyện/há miệng có thể bị coi là ngáp; kính/ánh sáng/tư thế có thể ảnh hưởng EAR.
Head pose không đo hướng nhìn của mắt. Cần hiệu chỉnh cho người demo.

## Kịch bản Demo

1. Chọn Demo / mô phỏng, Bắt đầu phiên.
2. Ngáp → chờ miệng đóng khoảng 1.6s → lặp 3 lần trong 60s: lời khuyên nghỉ ngơi.
3. Nhìn lệch → chờ khoảng 3s: ghi DISTRACTION.
4. Nhắm mắt → timer tăng đủ 5s → xác nhận I'M AWAKE trước 10s.
5. Chờ mắt mở hơn 1s, nhấn Emergency và không xác nhận: mô phỏng kích hoạt sau countdown.
6. Kết thúc mô phỏng hoặc Dừng & lưu phiên. Xem Lịch sử và Báo cáo phiên.

Critical kết hợp mắt nhắm/nhìn lệch/ngáp, vẫn dùng Risk Engine. Ngáp liên tục chỉ đếm một lần.
Mất mặt không tự hủy một countdown đã bắt đầu; cần bấm xác nhận.

## Hiệu suất

Ảnh phân tích mặc định rộng **480px**, có chọn 320/480/640 trong Cấu hình.
Ảnh webcam gốc vẫn dùng cho snapshot. Mục tiêu processing 20 FPS; FPS hiển thị đo thực tế.
MJPEG có thể hiển thị theo tốc độ worker, không bảo đảm 20/30 FPS nếu CPU/camera chỉ cung cấp 6 FPS.
Mở **Hiệu suất / chẩn đoán độ trễ** để xem Camera read và Vision:

- Camera read cao: tăng ánh sáng, đóng ứng dụng camera khác, kiểm tra webcam/driver.
- Vision cao: thử chiều ngang phân tích 320px, tắt vẽ điểm và đóng app nặng.
- Processing FPS tốt nhưng màn hình còn giật: kiểm tra Chrome/extensions và thử mở màn hình riêng.

Timer dùng monotonic time. Mất tracking ngắn giữ phần đã quan sát nhưng không cộng thời gian mất;
mất lâu hơn .5s reset liên tục mắt. No-face là thiếu dữ liệu, không phải bằng chứng tỉnh táo.
Heartbeat mất 30s tự dừng và lưu phiên. Thread Python không cưỡng bức ngắt driver camera đang treo;
khi STOPPING không kết thúc phải đóng Python rồi kiểm tra driver.

## Gemini

Copy `.env.example` thành `.env` hoặc nhập key ở trang Báo cáo. Model chỉnh được qua GEMINI_MODEL.
Chỉ gửi thời lượng, điểm trung bình/max, số sự kiện, source/status khi chủ động tạo báo cáo Gemini.
Không gửi ảnh/video/landmarks/tên. Không key/quota/network lỗi → báo cáo cục bộ.
Gemini không tham gia quyết định realtime. REST qua `urllib`, không thêm SDK.

## File quan trọng

- `app.py`: khởi tạo runtime, menu và routing Streamlit.
- `config.py`: cấu hình camera, phép đo, timing, risk và đường dẫn.
- `core/runtime.py`: worker, command queue, lifecycle/heartbeat/cleanup.
- `core/controller.py`: kết hợp risk/emergency/session/event; Camera và Demo dùng chung.
- `core/pipeline.py`, `vision/`: MediaPipe landmarks, EAR/MAR/head pose.
- `core/demo.py`: phép đo tổng hợp đưa vào các detector thật.
- `analysis/risk_engine.py`: heuristic và smoothing.
- `emergency/`: state manager, async alarm và snapshot.
- `database/database.py`, `session/`: SQLite/migration và thống kê theo thời gian.
- `ui/live_monitor.py`: nhúng cockpit, có nút mở riêng.
- `ui/live_bridge.py`: truyền ảnh/JSON/command local, không quyết định drowsiness.
- `ui/assets/live.html`, `live.css`, `live.js`: bố cục/cập nhật trình duyệt, không phụ thuộc CDN.
- `ui/dashboard.py`, `history.py`, `report.py`, `settings.py`: các trang khác.
- `services/gemini_service.py`: báo cáo optional + fallback.
- `run.bat`: môi trường/cài dependencies/Streamlit; launcher ngoài ZIP gọi file này đúng thư mục.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\smoke_model.py
.\.venv\Scripts\python.exe scripts\smoke_worker.py
```

Đã kiểm tra 65 test Python trên Linux/Python3.12, gồm SQLite/session/safety/AppTest và HTTP:
asset tải được, luồng chứa JPEG thật, Start/Stop/lưu phiên, xác nhận/timeout/emergency, origin/token lỗi.
JavaScript thật có smoke test DOM cho cold start/video/confirmation/emergency/rest/error
(`node scripts/test_live_ui.cjs`, chỉ để dev; app không cần cài Node).
MediaPipe thật chạy blank-frame/worker rồi cleanup. API Gemini dùng mock; chưa gọi API thật có key.
Chưa nghiệm thu trên webcam/còi Windows của bạn. Browser QA từ xa chặn localhost/file local;
không có screenshot trình duyệt xác nhận bố cục. Cần kiểm tra ngay trên Chrome laptop:

- [ ] Vùng cockpit hoặc Mở màn hình riêng hiện đúng.
- [ ] Webcam có hình, FPS/Camera read/Vision là số đo thực tế.
- [ ] Ngáp nhiều → nghỉ ngơi; nhìn lệch → event; nhắm đủ ngưỡng → xác nhận.
- [ ] Confirm trước hạn hủy emergency; không confirm kích hoạt simulation/snapshot.
- [ ] Stop nhả webcam, history/report đọc được; Start/Stop nhiều lần không mở trùng.

Đây là nguyên mẫu học tập, không phải hệ thống an toàn xe được chứng nhận hoặc chẩn đoán y tế.
Emergency chỉ mô phỏng. Mẫu gốc có vận tốc/GPS/trạm nghỉ/SOS; các mục này không nằm trong dự án.
Tài liệu Phase1/Phase2/HOTFIX cũ chỉ mô tả lịch sử; README này mô tả bản hiện tại.
