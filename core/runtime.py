"""A background worker owns camera, timers, alerts and SQLite; never calls Streamlit."""
import atexit
import logging
import queue
import threading
import time
import weakref
from dataclasses import replace
import cv2
from config import SETTINGS
from core.controller import SafetyController
from core.demo import DemoInput
from core.pipeline import VisionPipeline
from core.types import CameraStatus, MonitorResult
from database.database import Repository
from emergency.alert_manager import AlertManager
from vision.camera import Camera, CameraError
from vision.face_mesh import FaceMesh

logger = logging.getLogger(__name__)
_camera_owner = threading.Lock()


class MonitorRuntime:
    def __init__(self, settings=SETTINGS, camera_factory=Camera, detector_factory=FaceMesh):
        self.settings = settings
        self.camera_factory = camera_factory
        self.detector_factory = detector_factory
        self._lock = threading.Lock()
        self._lifecycle = threading.Lock()
        self._stop = threading.Event()
        self._commands = queue.Queue()
        self._thread = None
        self._result = MonitorResult()
        self._heartbeat = time.monotonic()
        self._audio_enabled = settings.audio_enabled
        ref = weakref.ref(self)
        atexit.register(lambda: ref() and ref().stop())

    def heartbeat(self):
        with self._lock:
            self._heartbeat = time.monotonic()

    def latest(self):
        with self._lock:
            return self._result

    @property
    def audio_enabled(self):
        with self._lock:
            return self._audio_enabled

    def set_audio_enabled(self, enabled):
        with self._lock:
            self._audio_enabled = enabled

    def _publish(self, result):
        with self._lock:
            self._result = result

    def is_active(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self, source="CAMERA"):
        if source not in ("CAMERA", "DEMO"):
            raise ValueError("Source must be CAMERA or DEMO")
        with self._lifecycle:
            if self.is_active():
                return False
            self._commands = queue.Queue()
            self.heartbeat()
            self._stop.clear()
            self._publish(MonitorResult(status=CameraStatus.STARTING, message="Đang khởi tạo phiên...", source=source))
            self._thread = threading.Thread(target=self._run, args=(source,), daemon=True, name="DriverGuard-worker")
            self._thread.start()
            return True

    def command(self, command):
        if self.is_active():
            self._commands.put((command, time.monotonic()))

    def stop(self):
        with self._lifecycle:
            self._stop.set()
            if self.is_active():
                self._thread.join(timeout=self.settings.stop_timeout_seconds)
                if self._thread.is_alive():
                    self._publish(replace(self.latest(), status=CameraStatus.STOPPING,
                        message="Camera chưa phản hồi; chưa thể mở phiên mới. Đóng ứng dụng nếu vẫn bị kẹt."))

    def _consume_commands(self, controller, pipeline, demo, source):
        while True:
            try:
                command, when = self._commands.get_nowait()
            except queue.Empty:
                return
            reset = command == "CONFIRM" and controller.confirm(when)
            reset = reset or command == "RESET" and controller.reset_emergency()
            if reset:
                pipeline.eyes.reset()
                demo.clear()
            elif command == "RECENTER":
                pipeline.head.recenter()
            elif source == "DEMO":
                demo.trigger(command, when)

    def _run(self, source):
        camera = detector = repository = controller = audio = None
        owns_camera = False
        finish_status = "COMPLETED"
        status = CameraStatus.STOPPED
        message = "Đã lưu phiên và giải phóng webcam."
        try:
            owns_camera = _camera_owner.acquire(blocking=False)
            if not owns_camera:
                raise CameraError("DriverGuard đang chạy ở tab khác. Hãy Stop ở tab đó trước.")
            repository = Repository(self.settings.database_path)
            repository.recover_interrupted()
            controller = SafetyController(self.settings, repository, source, time.monotonic())
            if source == "CAMERA":
                camera = self.camera_factory(self.settings)
                camera.open()
                detector = self.detector_factory(self.settings)
            pipeline = VisionPipeline(self.settings)
            if source == "CAMERA" and self.settings.auto_ear_calibration:
                pipeline.eyes.begin_calibration()
            demo = DemoInput(self.settings)
            audio = AlertManager(self.settings)
            previous = None
            failures = 0
            fps = 0
            while not self._stop.is_set():
                tick = time.monotonic()
                with self._lock:
                    heartbeat_age = tick-self._heartbeat
                if heartbeat_age > self.settings.heartbeat_timeout_seconds:
                    message = "Đã tự dừng và lưu phiên vì giao diện mất kết nối."
                    finish_status = "INTERRUPTED"
                    break
                self._consume_commands(controller, pipeline, demo, source)
                raw_frame = None
                camera_ms = vision_ms = 0.0
                if source == "CAMERA":
                    try:
                        read_started = time.monotonic()
                        raw_frame = camera.read()
                        camera_ms = (time.monotonic()-read_started)*1000
                        # Bound model cost even if camera ignores requested resolution.
                        h, w = raw_frame.shape[:2]
                        analysis_frame = raw_frame
                        if w > self.settings.processing_width:
                            analysis_frame = cv2.resize(raw_frame, (self.settings.processing_width, round(h*self.settings.processing_width/w)))
                        now = time.monotonic()
                        display, count, eyes, yawn, head = pipeline.analyze(analysis_frame, detector, now-controller.stats.started, now)
                        vision_ms = (time.monotonic()-now)*1000
                        failures = 0
                    except CameraError as exc:
                        failures += 1
                        now = time.monotonic()
                        eyes = pipeline.eyes.update([], 0, 0, now)
                        yawn = pipeline.yawns.update_mar(None, now)
                        head = pipeline.head.update_angles(None, None, now)
                        display = None
                        count = 0
                        message = f"{exc} Thử lại {failures}/{self.settings.max_read_failures}."
                else:
                    now = time.monotonic()
                    display = demo.frame
                    count = 0
                    eyes, yawn, head = demo.measure(pipeline, now)
                result = controller.update(eyes, yawn, head, count > 0 or source == "DEMO", now, raw_frame)
                if previous is not None:
                    instant = 1/max(.0001, now-previous)
                    fps = instant if fps == 0 else .8*fps+.2*instant
                previous = now
                jpeg = None
                if display is not None:
                    ok, encoded = cv2.imencode(".jpg", cv2.cvtColor(display, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, self.settings.jpeg_quality])
                    if ok:
                        jpeg = encoded.tobytes()
                current_message = (message if failures else "Tự hiệu chỉnh mắt: nhìn thẳng và mở mắt (%.0f%%)." % (eyes.calibration_progress*100) if eyes.calibrating
                                   else "Đang mô phỏng dữ liệu; không sử dụng webcam." if source == "DEMO"
                                   else "Đã phát hiện khuôn mặt." if count else "Không thấy khuôn mặt. Kiểm tra ánh sáng và nhìn vào camera.")
                if audio.settings.audio_enabled != self.audio_enabled:
                    audio.settings = replace(audio.settings, audio_enabled=self.audio_enabled)
                audio_message = audio.update(result.system_state, result.risk_level.value, now)
                self._publish(replace(result, frame_rgb=display, frame_jpeg=jpeg, landmark_count=count,
                                      frame_time=now, fps=fps, message=current_message, audio_message=audio_message,
                                      camera_ms=camera_ms, vision_ms=vision_ms))
                if failures >= self.settings.max_read_failures:
                    raise CameraError("Webcam đọc hình thất bại liên tiếp; đã dừng và lưu phiên.")
                self._stop.wait(max(0, 1/self.settings.target_fps-(time.monotonic()-tick)))
        except Exception as exc:
            logger.exception("Monitoring failed")
            status = CameraStatus.ERROR
            finish_status = "ERROR"
            message = f"{type(exc).__name__}: {exc}"
        finally:
            if controller is not None:
                try:
                    controller.finish(time.monotonic(), finish_status)
                except Exception as exc:
                    logger.exception("Session saving failed")
                    status = CameraStatus.ERROR
                    message += f" Không lưu được phiên: {exc}"
            for resource in (audio, camera, detector, repository):
                if resource is not None:
                    try:
                        resource.close()
                    except Exception as exc:
                        logger.exception("Cleanup failed")
                        status = CameraStatus.ERROR
                        message += f" Lỗi giải phóng tài nguyên: {exc}"
            if owns_camera:
                _camera_owner.release()
            final = replace(self.latest(), status=status, message=message, frame_rgb=None,
                            frame_jpeg=None, confirmation_remaining=0)
            if controller is not None:
                metrics = controller.stats.as_dict()
                final = replace(final, session_id=controller.session_id, session_seconds=metrics['duration'],
                                avg_risk=metrics['avg_risk'], max_risk=metrics['max_risk'])
            self._publish(final)
