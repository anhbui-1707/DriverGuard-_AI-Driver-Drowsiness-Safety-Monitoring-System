from dataclasses import replace
import streamlit as st
from ui.styles import heading


def render(runtime):
    heading("Cấu hình", "Hiệu chỉnh ngưỡng cho webcam và gương mặt của bạn.")
    settings = runtime.settings
    if runtime.is_active():
        st.info("Dừng phiên trước khi đổi cấu hình. Thay đổi áp dụng từ phiên tiếp theo.")
    with st.form("settings"), st.container(border=True):
        left, right = st.columns(2, gap="large")
        with left:
            st.markdown("### Nhận diện & hiệu suất")
            camera = st.number_input("Camera index", 0, 10, settings.camera_index)
            fps = st.select_slider("FPS xử lý mục tiêu", options=[10, 15, 20, 25], value=settings.target_fps)
            width = st.select_slider("Chiều ngang ảnh phân tích (px)", options=[320, 480, 640], value=settings.processing_width)
            closed = st.slider("EAR: ngưỡng mắt nhắm", .10, .35, settings.ear_closed_threshold, .01)
            opened = st.slider("EAR: ngưỡng mắt mở", .11, .40, settings.ear_open_threshold, .01)
            auto_calibration = st.checkbox("Tự hiệu chỉnh EAR khi bắt đầu phiên", settings.auto_ear_calibration)
            calibration_seconds = st.slider("Thời gian tự hiệu chỉnh mắt (s)", 1.5, 5.0, settings.ear_calibration_seconds, .5,
                                             disabled=not auto_calibration)
            mar = st.slider("MAR: ngưỡng miệng mở", .20, .80, settings.mar_open_threshold, .01)
            yawn_seconds = st.slider("Thời gian miệng mở để tính ngáp (s)", .5, 3.0, settings.yawn_duration_seconds, .1)
            head = st.slider("Góc lệch trái/phải (độ)", 10, 45, int(settings.head_yaw_threshold))
            pitch = st.slider("Góc cúi/ngẩng (độ)", 10, 40, int(settings.head_pitch_threshold))
        with right:
            st.markdown("### Cảnh báo")
            eye_seconds = st.slider("Mắt nhắm kéo dài (s)", 2.0, 8.0, settings.eye_closure_threshold_seconds, .5)
            timeout = st.slider("Thời hạn xác nhận (s)", 5.0, 20.0, settings.confirmation_timeout_seconds, 1.0)
            distraction = st.slider("Thời gian nhìn lệch (s)", 1.0, 6.0, settings.distraction_threshold_seconds, .5)
            count = st.slider("Số lần ngáp để khuyên nghỉ ngơi", 2, 6, settings.frequent_yawn_count)
            window = st.slider("Cửa sổ đếm ngáp (s)", 30, 180, int(settings.yawn_window_seconds), 10)
            audio = st.checkbox("Bật âm báo Windows", settings.audio_enabled)
            landmarks = st.checkbox("Vẽ điểm mắt / miệng (debug)", settings.show_landmarks)
            st.caption("480px phù hợp đa số máy; thử 320px nếu xử lý chậm, 640px nếu cần nhiều chi tiết. FPS thực tế phụ thuộc CPU/webcam.")
        if st.form_submit_button("Áp dụng cấu hình", type="primary", disabled=runtime.is_active()):
            if closed >= opened:
                st.error("EAR nhắm phải nhỏ hơn EAR mở để tránh trạng thái nhấp nháy.")
            elif mar <= settings.mar_closed_threshold:
                st.error("MAR mở phải lớn hơn MAR đóng (config.py).")
            else:
                runtime.settings = replace(settings, camera_index=camera, target_fps=fps, processing_width=width,
                    ear_closed_threshold=closed, ear_open_threshold=opened, mar_open_threshold=mar,
                    auto_ear_calibration=auto_calibration, ear_calibration_seconds=calibration_seconds,
                    yawn_duration_seconds=yawn_seconds, head_yaw_threshold=head, head_pitch_threshold=pitch,
                    eye_closure_threshold_seconds=eye_seconds, confirmation_timeout_seconds=timeout,
                    distraction_threshold_seconds=distraction, frequent_yawn_count=count,
                    yawn_window_seconds=window, audio_enabled=audio, show_landmarks=landmarks)
                runtime.set_audio_enabled(audio)
                st.success("Đã áp dụng; phiên tiếp theo sử dụng cấu hình mới.")
