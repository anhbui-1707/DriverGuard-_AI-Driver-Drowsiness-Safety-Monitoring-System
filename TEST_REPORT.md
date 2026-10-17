# Kết quả kiểm thử

Môi trường thực hiện không có webcam, OpenCV, MediaPipe hay TensorFlow. Do đó chưa chạy trực tiếp camera/model và **không có kết quả FPS hoặc độ trễ webcam thật**. Các kiểm thử dưới đây dùng camera/runtime giả, không chứng minh phần cứng Windows hoạt động.

- `python -m compileall -q DriverGuard`: cú pháp Python hợp lệ.
- `node --check ui/assets/live.js` và `node --check ui/assets/voice.js`: cú pháp JavaScript hợp lệ.
- `node tests/browser_smoke.js`: mô phỏng trình duyệt đọc trạng thái, bấm Start, nhận và hiển thị frame, cập nhật EAR, bấm Stop; kiểm tra API âm báo có `update` để tránh lỗi JavaScript làm ngừng render.
- `python -m unittest discover -s tests -p 'test_*.py' -v`: kiểm thử mô phỏng nhiều chu kỳ cảnh báo kể cả khi model không xác nhận mắt mở sau cú nhấn, ngưỡng nhắm mắt mặc định 3 giây, ngáp lặp lại và mất mặt giữa hai lần ngáp, ngắt bộ đếm khi mắt không xác định, không tái kích hoạt bằng frame cũ, camera chỉ lấy ảnh mới, đóng hai luồng, HTTP phục vụ ảnh/không trả lại ảnh cũ, lệnh Start/Stop lặp lại, panel một trang, countdown monotonic, xác nhận và khẩn cấp mô phỏng khi hết hạn.

Nghiệm thu còn cần thực hiện trên laptop Windows: camera thật, độ trễ chuyển động, nhận diện mắt/ngáp/hướng nhìn, âm báo, nút tròn trong trình duyệt, đổi theme, bật/tắt nhiều lần và phiên 15 phút. Hướng dẫn đo và xử lý lỗi ở README.
