# Bản vá lag và ảnh webcam lỗi

**Đã được thay bằng bản Cockpit đầy đủ. Không ghép bản vá này vào source hiện tại.**
Xem README.md và chạy START_DRIVERGUARD.bat trong gói đầy đủ mới.

1. Trong app, Dừng & lưu phiên. Nhấn Ctrl+C trong Terminal để dừng server.
2. Giải nén DriverGuard_LagFix.zip vào một thư mục tạm.
3. Chép toàn bộ nội dung thư mục DriverGuard trong ZIP vào thư mục DriverGuard
   hiện tại của bạn (thư mục có app.py và run.bat), chọn Replace các file trùng.
4. Không xóa data/, assets/screenshots/ hoặc .venv/ đang có.
5. Chạy .\run.bat từ thư mục có app.py. Trong Chrome nhấn Ctrl+F5 rồi bắt đầu phiên mới.

ZIP này chỉ thay 5 file code và thêm tài liệu/test; không thay DB, môi trường Python
hay dependency. Các chức năng ngáp/confirmation/emergency/history giữ nguyên.

Thay đổi: webcam dùng inline JPEG thay đường dẫn /media từng frame; video và chỉ số
có fragment riêng, cập nhật lần lượt 10Hz/4Hz, sự kiện 1Hz. Khung ảnh giữ tỷ lệ 4:3
để tránh co giãn khi tải. Phân tích mặc định 480px, có chọn 320/480/640 trong Cấu hình;
snapshot giữ ảnh gốc. Timer vẫn chạy trong worker như trước.

Ảnh người dùng có 5.8 FPS và biểu tượng ảnh lỗi. Chưa đủ bằng chứng để kết luận toàn
bộ độ trễ do CPU, camera hay trình duyệt. Mở “Hiệu suất / chẩn đoán độ trễ” để xem:

- Camera read cao (ví dụ 150ms): chờ camera/driver; tăng ánh sáng, đóng Zoom/Teams,
  kiểm tra tốc độ camera. Giảm FPS mục tiêu không tự làm camera nhanh hơn.
- Vision cao (ví dụ 150ms): thử ảnh phân tích 320px, đóng chương trình nặng.
- Hai thời gian đều thấp nhưng hình còn giật: kiểm tra CPU Chrome, đóng tab nặng.

Đã kiểm thử 61 tests (logic/session/AppTest/ảnh JPEG) và syntax checks trên Linux.
Cần chạy bản vá trên Windows để đo cải thiện FPS và xác nhận ảnh hiển thị trong Chrome.
