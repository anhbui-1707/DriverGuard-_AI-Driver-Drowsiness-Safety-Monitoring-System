"""One in-flight landmark request; its original frame travels with its result."""
from dataclasses import dataclass
import threading
import time
import cv2
import mediapipe as mp


@dataclass(frozen=True)
class FaceSample:
    frame_bgr: object
    landmarks: object
    observed_at: float
    face_ms: float


class AsyncFaceMesh:
    def __init__(self, settings, landmarker_factory=None):
        self.settings = settings
        self._lock = threading.Lock()
        self._pending = None
        self._ready = None
        self._closed = False
        self._epoch = 0
        self._last_timestamp = -1
        self._last_submitted_at = None
        self._error = None
        if not settings.model_path.is_file():
            raise FileNotFoundError(f"Thiếu model landmark: {settings.model_path}")
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(settings.model_path)),
            running_mode=mp.tasks.vision.RunningMode.LIVE_STREAM,
            num_faces=1,
            min_face_detection_confidence=settings.detection_confidence,
            min_face_presence_confidence=settings.detection_confidence,
            min_tracking_confidence=settings.tracking_confidence,
            result_callback=self._receive,
        )
        factory = landmarker_factory or mp.tasks.vision.FaceLandmarker.create_from_options
        self.landmarker = factory(options)

    def submit(self, frame_bgr, observed_at):
        with self._lock:
            if self._closed or self._pending is not None:
                return False
            if self._last_submitted_at is not None and observed_at <= self._last_submitted_at:
                return False  # Never classify the same captured frame twice.
            timestamp = max(self._last_timestamp+1, int(observed_at*1000))
            self._last_timestamp = timestamp
            self._last_submitted_at = observed_at
            # Only this copy can be used for cropping the callback's landmarks.
            original = frame_bgr.copy()
            self._pending = (original, observed_at, timestamp, self._epoch, time.perf_counter())
        try:
            h, w = original.shape[:2]
            analysis = original
            if w > self.settings.processing_width:
                analysis = cv2.resize(original, (self.settings.processing_width,
                                                 round(h*self.settings.processing_width/w)))
            rgb = cv2.cvtColor(analysis, cv2.COLOR_BGR2RGB)
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            self.landmarker.detect_async(image, timestamp)
        except Exception:
            with self._lock:
                self._pending = None
            raise
        return True

    def _receive(self, result, output_image, timestamp_ms):
        try:
            with self._lock:
                pending = self._pending
                if pending is None or pending[2] != timestamp_ms:
                    return
                self._pending = None
                frame, observed_at, _, epoch, started = pending
                if self._closed or epoch != self._epoch:
                    return
                landmarks = result.face_landmarks[0] if result.face_landmarks else []
                self._ready = FaceSample(frame, landmarks, observed_at,
                                         (time.perf_counter()-started)*1000)
        except Exception as exc:
            with self._lock:
                self._error = exc

    def take_latest(self, now):
        with self._lock:
            if self._error is not None:
                raise RuntimeError(f"Callback landmark lỗi: {self._error}") from self._error
            if self._pending is not None and time.perf_counter()-self._pending[4] > self.settings.stop_timeout_seconds:
                raise RuntimeError("MediaPipe chưa trả kết quả landmark; đã dừng để tránh dùng dữ liệu cũ.")
            sample = self._ready
            self._ready = None
        if sample is not None and now-sample.observed_at <= self.settings.face_result_max_age_seconds:
            return sample
        return None

    def invalidate(self):
        with self._lock:
            self._epoch += 1
            self._ready = None

    def close(self):
        with self._lock:
            self._closed = True
            self._ready = None
        self.landmarker.close()
