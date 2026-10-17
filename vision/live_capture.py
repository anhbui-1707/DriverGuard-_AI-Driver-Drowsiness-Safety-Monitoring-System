"""Independent camera reader and preview encoder, each with a latest-frame slot."""
import csv
from datetime import datetime
from pathlib import Path
import logging
import threading
import time
from vision.camera import CameraError


class LiveCapture:
    def __init__(self, camera, preview, settings):
        self.camera = camera
        self.preview = preview
        self.settings = settings
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._stop = threading.Event()
        self._frame = None
        self._captured_at = 0.0
        self._error = None
        self._captured_perf = 0.0
        self._read_ms = 0.0
        self._read_count = 0
        self._profile = None
        self._started = time.perf_counter()
        self._last_log = self._started
        self._logged_reads = 0
        self._thread = threading.Thread(target=self._run, daemon=True, name="DriverGuard-camera")
        self._encoder = threading.Thread(target=self._encode, daemon=True, name="DriverGuard-preview")

    def start(self):
        self._thread.start()
        self._encoder.start()

    def _run(self):
        try:
            while not self._stop.is_set():
                try:
                    read_started = time.perf_counter()
                    frame = self.camera.read()
                    captured_perf = time.perf_counter()
                    with self._condition:
                        self._frame = frame
                        self._captured_perf = captured_perf
                        self._read_ms = (captured_perf-read_started)*1000
                        self._read_count += 1
                        self._captured_at = time.monotonic()
                        self._error = None
                        self._condition.notify()
                    # VideoCapture normally blocks at the hardware frame rate.
                    # A tiny yield prevents a faulty driver spinning without blocking.
                    self._stop.wait(.001)
                except CameraError as exc:
                    with self._lock:
                        self._error = str(exc)
                    self._stop.wait(.05)
        except Exception as exc:
            logging.getLogger(__name__).exception("Camera reader failed")
            with self._lock:
                self._error = str(exc)
        finally:
            self.camera.close()
            with self._condition:
                self._stop.set()
                self._condition.notify_all()

    def _encode(self):
        previous = None
        fps = getattr(self.settings, "preview_fps", self.settings.target_fps)
        try:
            while not self._stop.is_set():
                started = time.monotonic()
                with self._condition:
                    self._condition.wait_for(lambda: self._stop.is_set() or
                        (self._frame is not None and self._captured_at != previous and self._error is None), timeout=.5)
                    if self._stop.is_set():
                        return
                    if self._frame is None or self._captured_at == previous or self._error:
                        continue
                    frame, captured_at = self._frame, self._captured_at
                    captured_perf, read_ms, read_count = self._captured_perf, self._read_ms, self._read_count
                encoding_started = time.perf_counter()
                self.preview(frame, captured_at)
                finished = time.perf_counter()
                self._log_preview(read_ms, (finished-encoding_started)*1000,
                                  (finished-captured_perf)*1000, read_count, finished)
                previous = captured_at
                self._stop.wait(max(0, 1/fps-(time.monotonic()-started)))
        except Exception as exc:
            logging.getLogger(__name__).exception("Preview encoding failed")
            with self._lock:
                self._error = str(exc)
            self._stop.set()
        finally:
            if self._profile is not None:
                self._profile.close()

    def _log_preview(self, read_ms, encode_ms, age_ms, reads, now):
        if now-self._last_log < 1:
            return
        try:
            if self._profile is None:
                directory = Path(__file__).resolve().parents[1]/"logs"
                directory.mkdir(exist_ok=True)
                self._profile = (directory/f"camera_performance_{datetime.now():%Y%m%d_%H%M%S_%f}.csv").open("w", newline="", encoding="utf-8")
                csv.writer(self._profile).writerow(["session_seconds", "camera_read_ms", "reader_fps",
                                                   "preview_encode_ms", "capture_to_jpeg_ms"])
            reader_fps = (reads-self._logged_reads)/(now-self._last_log)
            csv.writer(self._profile).writerow([round(now-self._started,2), round(read_ms,2),
                                               round(reader_fps,2), round(encode_ms,2), round(age_ms,2)])
            self._profile.flush()
        except OSError as exc:
            logging.getLogger(__name__).warning("Không ghi được log camera: %s", exc)
            if self._profile is not None:
                self._profile.close()
                self._profile = None
        self._last_log = now
        self._logged_reads = reads

    def latest(self):
        return self.latest_sample()[0]

    def latest_sample(self, after=None):
        with self._lock:
            if self._error:
                raise CameraError(self._error)
            if self._frame is None:
                raise CameraError("Đang chờ khung hình đầu tiên.")
            if time.monotonic()-self._captured_at > self.settings.yawn_max_sample_gap_seconds:
                raise CameraError("Camera chưa gửi khung hình mới.")
            if after is not None and self._captured_at == after:
                return None, self._captured_at
            return self._frame.copy(), self._captured_at

    def read_ms(self):
        with self._lock:
            return self._read_ms

    def close(self):
        self._stop.set()
        with self._condition:
            self._condition.notify_all()
        self._thread.join(timeout=self.settings.stop_timeout_seconds)
        self._encoder.join(timeout=self.settings.stop_timeout_seconds)
        if self._thread.is_alive():
            logging.getLogger(__name__).warning("Camera driver is still waiting for a frame")
