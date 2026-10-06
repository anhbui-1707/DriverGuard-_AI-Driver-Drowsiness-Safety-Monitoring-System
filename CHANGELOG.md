# Bản nâng cấp DriverGuard

## Cockpit — sửa luồng hiển thị và dùng mẫu HTML được cung cấp

- Thay màn hình nhiều fragment/base64 bằng HTML local và luồng MJPEG trực tiếp.
- Thêm ui/live_bridge.py (stdlib HTTP, chỉ localhost), ui/assets/live.html/live.css/live.js.
- Thay ui/live_monitor.py bằng iframe ổn định với link mở riêng khi iframe bị chặn.
- Theme dark/cyan theo mẫu; gauge/risk/EAR/MAR/chart/events dùng dữ liệu thực.
- Không dùng số liệu giả hoặc CDN; giữ scope không GPS/vận tốc/SOS/cứu hộ thật.
- Thêm toggle audio kết nối worker; timer/risk/state/database giữ trong Python.
- Thêm HTTP integration tests và JavaScript DOM smoke test; 65 Python tests đã qua.
- Thêm START_DRIVERGUARD.bat ngoài ZIP để tránh chạy sai thư mục.
- Bản đầy đủ thay các bản vá nhỏ. Chưa có traceback Windows nên chưa thể kết luận
  nguyên nhân cụ thể của màn hình trắng trên máy người dùng; Windows/browser QA cần thử thực tế.

Các mục phía dưới ghi lại thay đổi của bản trước.

## Sửa nguyên nhân gây độ trễ

- Thay còi blocking gọi từ UI bằng alarm WAV Windows bất đồng bộ theo chuyển trạng thái.
- Worker sở hữu bộ đếm/state machine; UI chỉ đọc kết quả mới nhất và gửi command.
- Giảm frame xử lý tối đa 640px ngang, nén JPEG trong worker, tắt vẽ toàn bộ mesh mặc định.
- Yêu cầu buffer camera 1; 20 FPS processing mục tiêu, ~10 Hz UI. Có chọn 10/15/20/25 FPS.

## Hoàn thiện chức năng còn thiếu hoặc chưa đúng

- Yawn/hướng đầu có tính theo thời gian, đếm sự kiện một lần và thời gian ngáp gần đây.
- 3 ngáp/60s → REST_RECOMMENDED và “Bạn nên nghỉ ngơi”, không flood mỗi frame.
- Head pose thêm DOWN/UP và đặt tư thế chuẩn, thay cách đo head rất đơn giản của bản cũ.
- Confirmation/timeout không phụ thuộc rerun; confirm reset mắt + rearm yêu cầu mắt mở đủ lâu.
- Emergency ghi snapshot webcam thật với đường dẫn tương đối; snapshot lỗi không làm crash event.
- Stats thực có time-weighted average/max/duration/counters; không còn lưu tất cả bằng 0.
- SQLite thêm migration, risk samples, report; kết thúc ERROR/INTERRUPTED vẫn cố lưu phiên.
- Demo không sửa trực tiếp UI/Boolean/state, dùng cùng timers/Risk/Controller như webcam.
- Dashboard, History, timeline/chart/snapshots, báo cáo cục bộ/Gemini optional, settings page.
- Theme sáng gọn, tham khảo shadcn dashboard và Tabler; giữ Streamlit, không thêm frontend stack.

## File chính được thay đổi

`app.py`, `config.py`, `requirements.txt`, `core/runtime.py`, `core/pipeline.py`, `core/types.py`,
`vision/camera.py`, `vision/eye_detector.py`, `vision/yawn_detector.py`, `vision/head_pose.py`,
`analysis/risk_engine.py`, các file trong `emergency/`, `database/database.py`,
`ui/live_monitor.py`, `ui/styles.py`, tests AppTest/runtime, smoke_worker, README, theme config.

## File chính được tạo

`core/controller.py`, `core/demo.py`, `session/session_manager.py`, `services/gemini_service.py`,
`utils/environment.py`, `ui/dashboard.py`, `ui/history.py`, `ui/report.py`, `ui/settings.py`,
`tests/test_safety.py`, `tests/test_reports.py`, `scripts/benchmark.py`, `scripts/ui_preview.py`,
`scripts/make_alarm.py`, `assets/sounds/alarm.wav`, `run.bat`, `pytest.ini`, `.env.example`.

## Kiểm tra

- Compile/import: qua; 60 unit/integration/AppTest: qua.
- MediaPipe thật: blank không có mặt; ảnh mặt có 478 landmarks, EAR/MAR/head được tính.
- Worker thật: model đọc frame và cleanup khi Stop; heartbeat và lỗi có tests giả lập.
- Benchmark 100 ảnh mặt: median 13.1ms, p95 18.9ms xử lý+nén trên CPU môi trường Linux.
- Gemini test mock: text-only request, success, thiếu key, HTTP429, empty reply → local fallback.
- Chưa nghiệm thu webcam/còi Windows thật, Gemini có API key và visual browser QA; cần checklist README.
- Không thêm GPS/SMS/cứu hộ/identity/cloud hoặc các chức năng ngoài phạm vi.

Các checklist Phase1/Phase2 trong source chỉ là tài liệu lịch sử của giai đoạn trước;
README và CHANGELOG này mô tả phiên bản hiện tại.
