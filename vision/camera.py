"""OpenCV owns the local machine's webcam, not the browser's camera."""
import sys
import cv2

from config import Settings


class CameraError(RuntimeError):
    pass


class Camera:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.capture = None

    def open(self) -> None:
        # DirectShow is generally useful on Windows; fall back to auto selection.
        backends = [cv2.CAP_DSHOW, cv2.CAP_ANY] if sys.platform == "win32" else [cv2.CAP_ANY]
        for backend in backends:
            capture = cv2.VideoCapture(self.settings.camera_index, backend)
            if capture.isOpened():
                self.capture = capture
                capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.settings.frame_width)
                capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.settings.frame_height)
                capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                capture.set(cv2.CAP_PROP_FPS, self.settings.target_fps)
                return
            capture.release()
        raise CameraError("Không mở được webcam. Kiểm tra quyền camera, camera index và đóng ứng dụng đang dùng camera.")

    def read(self):
        if self.capture is None:
            raise CameraError("Camera chưa được mở.")
        success, frame = self.capture.read()
        if not success or frame is None or frame.size == 0:
            raise CameraError("Không đọc được hình từ webcam.")
        return frame

    def close(self) -> None:
        if self.capture is not None:
            self.capture.release()
            self.capture = None
