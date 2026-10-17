# DriverGuard

DriverGuard mở **một trang giám sát duy nhất**, vừa một màn hình desktop, chạy tại `127.0.0.1`. Webcam và AI chạy trên laptop; trình duyệt chỉ xem video, chỉ số và phát âm báo. Khẩn cấp **chỉ mô phỏng**; không gọi điện, gửi SMS hoặc dùng GPS.

## Chạy trên Windows / VS Code

1. Giải nén ZIP đầy đủ vào một thư mục. Đừng chạy code bên trong ZIP.
2. Cài Python 3.11 hoặc 3.12 bản 64-bit, bật quyền camera cho ứng dụng desktop trong Windows Settings.
3. Nhấp đúp `START_DRIVERGUARD.bat` ở ngoài cùng. Lần đầu nó tạo `.venv` và cài thư viện; giữ cửa sổ Terminal mở.
4. Trang giám sát mở tự động. Nếu trình duyệt không tự bật, sao chép địa chỉ `DriverGuard đang chạy tại: http://127.0.0.1:...` được in trong Terminal.
5. Nhấn **Bắt đầu giám sát** ngay dưới camera. Khi dừng, camera được giải phóng; có thể bắt đầu lại.

Trong VS Code, mở thư mục `DriverGuard` rồi chạy `..\START_DRIVERGUARD.bat` trong Terminal. Nếu đã tạo môi trường thủ công: `py -3.11 -m venv .venv`, `.venv\Scripts\python.exe -m pip install -r requirements.txt`, `.venv\Scripts\python.exe app.py`.

## Nếu webcam không lên

- Xem thông báo ngay dưới camera và lỗi trong Terminal. Ứng dụng báo rõ thiết bị/backend đã thử; không cần cấp quyền webcam cho trình duyệt, nhưng **phải cấp quyền cho ứng dụng desktop** trong Windows.
- Đóng Camera, Zoom, Teams hoặc chương trình khác đang dùng webcam. Kiểm tra nắp camera, mở ứng dụng Camera của Windows để xác nhận phần cứng.
- Nếu Windows Camera hoạt động mà DriverGuard không hoạt động, gửi nguyên văn lỗi trên màn hình/Terminal và các dòng mới nhất của `logs/camera_performance_*.csv` để xác định backend/driver. Đừng kết luận FPS trước khi có ảnh webcam thật.

## Cách hoạt động

Luồng đọc camera, luồng nén JPEG và vòng AI hoạt động riêng. Mỗi luồng giữ frame mới nhất, không tích hàng đợi. AI lấy mẫu khoảng 12 lần/giây, trình duyệt chỉ tải frame mới. Con số FPS trên ảnh là số frame **thực sự giải mã để hiển thị**. Camera đầu vào yêu cầu 640 × 480; kích thước hiển thị tự giãn nhưng không méo tỷ lệ. `logs/` ghi thời gian đọc camera, nén JPEG và xử lý model.

EAR và MAR là chỉ số hình học để quan sát; model TFLite vẫn phân loại mắt/ngáp. Nhắm mắt liên tục khoảng 3 giây bật cảnh báo tròn. Nhấn tròn để xác nhận; hết 10 giây chuyển thành **khẩn cấp mô phỏng**. Bộ đếm dựa trên đồng hồ monotonic và không tự hủy vì vài frame mất mặt. Điểm rủi ro 0–100 và ba bộ đếm vẫn hoạt động.

Các phiên/sự kiện được lưu cục bộ trong `data/driverguard.db` theo cơ chế có sẵn của dự án; video không được gửi lên mạng. Mô hình AI được đóng gói trong `models/`.

## Kiểm thử trên laptop

Bật/tắt webcam 5 lần, theo dõi FPS sau 30 giây; nhắm mắt, ngáp, quay đầu trong điều kiện đủ sáng; thử nhấn cảnh báo tròn và để hết hạn; đổi giao diện sáng/tối; chạy liên tục 15 phút. Đối chiếu `logs/` và Task Manager. Môi trường đóng gói không có webcam/MediaPipe để đo FPS thật; `TEST_REPORT.md` phân biệt các bài kiểm thử mô phỏng.

### Sửa lỗi hiển thị 17/10

Bản trước có lỗi JavaScript `window.DriverVoice?.update is not a function`. Giao diện ngừng cập nhật trước khi vẽ video dù lệnh Start đã gửi. Bản này xuất đúng `update`, bảo vệ render khi phần âm thanh lỗi, và có `tests/browser_smoke.js` kiểm tra đường đi Start → frame → Stop. Trên màn hình desktop, camera cùng các panel và nút điều khiển dùng chiều cao viewport để không cần cuộn.

### Cảnh báo nhiều lần

Sau mỗi lần nhấn xác nhận, DriverGuard đặt lại bộ đếm mắt và cho phép cảnh báo mới sau 1 giây. Việc này không phụ thuộc model có nhận đúng mắt mở trong khoảng nghỉ đó hay không; nếu model vẫn nhận mắt nhắm liên tục thêm 3 giây, cảnh báo sẽ xuất hiện lại. Mất mặt, crop mắt lỗi hoặc điểm model không chắc chắn kéo dài sẽ ngắt chuỗi nhắm mắt trước đó. Vùng ổn định quanh điểm model 0,5 giảm đảo trạng thái khi điểm dao động sát ngưỡng; nó không thay thế kiểm thử độ chính xác với webcam thật.

### Nhận diện ngáp

Model TFLite và độ mở miệng MAR được ghép theo cùng thời điểm lấy mẫu. Điểm model mạnh có thể báo ngáp; điểm trung bình cần MAR đủ lớn. Chỉ một lần ngáp được đếm khi tín hiệu kéo dài đủ 0,8 giây; mất mặt/crop lỗi sẽ kết thúc lần ngáp đang theo dõi để lần kế tiếp có thể được đếm. Đây là quy tắc heuristic, cần kiểm tra trên webcam của bạn với tình huống ngáp, nói và cười trước khi kết luận độ chính xác.
