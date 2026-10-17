"""OpenCV owns the local machine's webcam, not the browser's camera."""
import logging
import sys
import time

import cv2

from config import Settings

log = logging.getLogger(__name__)

# Windows machine-wide failure modes worth naming in the error message.
WINDOWS_HINTS = (
    "Mở ứng dụng Camera của Windows để kiểm tra camera còn hoạt động.",
    "Đóng ứng dụng khác đang dùng camera (Teams, Zoom, Camera, trình duyệt).",
    "Kiểm tra Cài đặt › Quyền riêng tư › Camera, và nắp che camera trên máy.",
    "Nếu vừa rút/cắm lại hoặc camera bị treo: khởi động lại Windows rồi thử lại.",
)


class CameraError(RuntimeError):
    pass


class Camera:
    """Tries the configured index first, then other indices/backends before giving up."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.capture = None
        self.index = settings.camera_index
        self.attempts = []
        self._first_frame = None

    def _backends(self):
        # Prefer the backend used by the previously working Windows version.
        if sys.platform == "win32":
            return [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        return [cv2.CAP_ANY]

    def _indices(self):
        wanted = self.settings.camera_index
        others = [index for index in range(4) if index != wanted]
        return [wanted] + others

    def _configure(self, capture):
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.settings.frame_width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.settings.frame_height)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        capture.set(cv2.CAP_PROP_FPS, self.settings.preview_fps)

    def _try(self, index, backend, configure=True):
        capture = cv2.VideoCapture(index, backend)
        accepted = False
        try:
            if not capture.isOpened():
                return None
            if configure:
                self._configure(capture)
            # Some drivers open successfully but cannot deliver the requested format.
            for _ in range(10):
                ok, frame = capture.read()
                if ok and frame is not None and frame.size:
                    self._first_frame = frame
                    accepted = True
                    return capture
                time.sleep(0.05)
            return None
        finally:
            if not accepted:
                capture.release()

    def open(self) -> None:
        self.close()
        self.attempts = []
        for index in self._indices():
            for backend in self._backends():
                name = cv2.videoio_registry.getBackendName(backend)
                try:
                    capture = self._try(index, backend)
                    if capture is None:
                        # Reopen without forcing FPS or resolution.
                        capture = self._try(index, backend, configure=False)
                except cv2.error as exc:
                    self.attempts.append(f"index {index} / {name}: {exc.__class__.__name__}")
                    continue
                if capture is not None:
                    self.capture = capture
                    self.index = index
                    if index != self.settings.camera_index:
                        log.warning("camera index %s was empty; using index %s instead",
                                    self.settings.camera_index, index)
                    return
                self.attempts.append(f"index {index} / {name}: không mở được")
        detail = "; ".join(self.attempts[:6]) or "không có thiết bị nào phản hồi"
        raise CameraError(
            "Không mở được webcam. Đã thử: " + detail + ". "
            + " ".join(WINDOWS_HINTS)
        )

    def read(self):
        if self.capture is None:
            raise CameraError("Camera chưa được mở.")
        if self._first_frame is not None:
            frame = self._first_frame
            self._first_frame = None
            return frame
        success, frame = self.capture.read()
        if not success or frame is None or frame.size == 0:
            raise CameraError("Không đọc được hình từ webcam. "
                              + " ".join(WINDOWS_HINTS[:2]))
        return frame

    def close(self) -> None:
        self._first_frame = None
        if self.capture is not None:
            self.capture.release()
            self.capture = None
