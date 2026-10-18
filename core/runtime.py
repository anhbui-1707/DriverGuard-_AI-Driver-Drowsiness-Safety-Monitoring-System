"""A background worker owns camera, timers and alerts; no session data is persisted."""
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
from emergency.alert_manager import AlertManager
from vision.camera import Camera, CameraError
from vision.live_capture import LiveCapture
from vision.face_mesh import FaceMesh
from vision.async_face import AsyncFaceMesh
from vision.eye_tracker import EyeState

logger = logging.getLogger(__name__)
_camera_owner = threading.Lock()


class MonitorRuntime:
    def __init__(self, settings=SETTINGS, camera_factory=Camera, detector_factory=None):
        self.settings = settings
        self.camera_factory = camera_factory
        self.detector_factory = detector_factory or (AsyncFaceMesh if settings.async_face_enabled else FaceMesh)
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

    def _publish_preview(self, frame, captured_at):
        mirrored = cv2.flip(frame, 1)
        started = time.perf_counter()
        ok, encoded = cv2.imencode(".jpg", mirrored,
                                  [cv2.IMWRITE_JPEG_QUALITY, self.settings.jpeg_quality])
        if ok:
            with self._lock:
                published_at = time.monotonic()
                last = self._result.preview_published_at
                fps = self._result.preview_fps
                if last is not None and published_at > last:
                    instant = 1/(published_at-last)
                    fps = instant if fps == 0 else .8*fps+.2*instant
                self._result = replace(self._result, frame_jpeg=encoded.tobytes(), frame_time=captured_at, preview_fps=fps,
                    preview_published_at=published_at, encode_ms=(time.perf_counter()-started)*1000)

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

    def _consume_commands(self, controller, pipeline, demo, source, detector=None):
        while True:
            try:
                command, when = self._commands.get_nowait()
            except queue.Empty:
                return
            reset = command == "CONFIRM" and controller.confirm(when)
            reset = reset or command == "RESET" and controller.reset_emergency(when)
            if reset:
                pipeline.eyes.reset()
                if isinstance(detector, AsyncFaceMesh):
                    detector.invalidate()
                demo.clear()
            elif command == "RECENTER":
                pipeline.head.recenter()
            elif source == "DEMO":
                demo.trigger(command, when)

    def _run(self, source):
        camera = detector = controller = audio = capture_stream = pipeline = None
        owns_camera = False
        finish_status = "COMPLETED"
        status = CameraStatus.STOPPED
        message = "Đã lưu phiên và giải phóng webcam."
        try:
            owns_camera = _camera_owner.acquire(blocking=False)
            if not owns_camera:
                raise CameraError("DriverGuard đang chạy ở tab khác. Hãy Stop ở tab đó trước.")
            controller = SafetyController(self.settings, source, time.monotonic())
            if source == "CAMERA":
                camera = self.camera_factory(self.settings)
                camera.open()
                capture_stream = LiveCapture(camera, self._publish_preview, self.settings)
                capture_stream.start()
                detector = self.detector_factory(self.settings)
            pipeline = VisionPipeline(self.settings)
            demo = DemoInput(self.settings)
            audio = AlertManager(self.settings)
            previous = None
            failures = 0
            first_frame_deadline = time.monotonic() + 4.0
            fps = 0
            last_vision = None
            last_observed_at = None
            last_frame_processed_at = None
            last_frame_seen_at = None
            last_frame_for_snapshot = None
            next_inference_at = 0.0
            while not self._stop.is_set():
                tick = time.monotonic()
                with self._lock:
                    heartbeat_age = tick-self._heartbeat
                if heartbeat_age > self.settings.heartbeat_timeout_seconds:
                    message = "Đã tự dừng vì giao diện mất kết nối."
                    finish_status = "INTERRUPTED"
                    break
                self._consume_commands(controller, pipeline, demo, source, detector)
                raw_frame = None
                observed_new = True
                camera_ms = vision_ms = 0.0
                if source == "CAMERA":
                    try:
                        # Copy a frame only when another inference is due. The
                        # preview encoder reads the newest capture independently.
                        if tick >= next_inference_at:
                            raw_frame, captured_at = capture_stream.latest_sample(last_frame_seen_at)
                            last_frame_seen_at = captured_at
                        else:
                            captured_at = last_frame_seen_at
                        camera_ms = capture_stream.read_ms()
                        if raw_frame is not None:
                            last_frame_for_snapshot = raw_frame
                        now = time.monotonic()
                        vision_started = time.perf_counter()
                        observed_new = False
                        if pipeline.eyes.last_time is None:
                            last_vision = None
                        if isinstance(detector, AsyncFaceMesh):
                            # Consume before submitting: crop from the returned original frame.
                            sample = detector.take_latest(now)
                            if sample is not None and (pipeline.eyes.last_time is None or
                                                       sample.observed_at >= pipeline.eyes.last_time):
                                rgb = cv2.cvtColor(sample.frame_bgr, cv2.COLOR_BGR2RGB)
                                last_vision = pipeline.analyze_landmarks(
                                    rgb, sample.landmarks, sample.observed_at-controller.stats.started,
                                    sample.observed_at, face_ms=sample.face_ms)
                                last_observed_at = sample.observed_at
                                observed_new = True
                            if raw_frame is not None and now >= next_inference_at:
                                detector.submit(raw_frame, captured_at)
                                next_inference_at = now + 1/self.settings.inference_fps
                        elif raw_frame is not None and now >= next_inference_at:
                            # New captures only. UI commands/timeouts still run every loop.
                            h, w = raw_frame.shape[:2]
                            analysis_frame = raw_frame
                            if w > self.settings.processing_width:
                                analysis_frame = cv2.resize(raw_frame, (self.settings.processing_width,
                                    round(h*self.settings.processing_width/w)))
                            last_vision = pipeline.analyze(
                                analysis_frame, detector, now-controller.stats.started, now, eye_frame=raw_frame)
                            last_frame_processed_at = captured_at
                            next_inference_at = time.monotonic() + 1/self.settings.inference_fps
                            last_observed_at = captured_at
                            observed_new = True
                        now = time.monotonic()
                        if last_vision is not None and now-last_observed_at <= self.settings.face_result_max_age_seconds:
                            display, count, eyes, yawn, head = last_vision
                            if not observed_new:
                                # Cached observations do not advance timers or repeat events.
                                yawn = replace(yawn, event=False)
                                head = replace(head, event=False)
                        else:
                            eyes, yawn, head = pipeline.invalidate_camera_tracking(now)
                            display, count = None, 0
                            last_vision = None
                        vision_ms = (time.perf_counter()-vision_started)*1000
                        failures = 0
                    except CameraError as exc:
                        # Camera drivers may need a short warm-up after opening.
                        if time.monotonic() >= first_frame_deadline or last_frame_seen_at is not None:
                            failures += 1
                        now = time.monotonic()
                        eyes = pipeline.eyes.update_state(EyeState.UNKNOWN, now)
                        if pipeline.yawn_classifier is not None:
                            pipeline.yawn_classifier.invalidate()
                        yawn = pipeline.yawns.update_score(None, now)
                        head = pipeline.head.update_angles(None, None, now)
                        display = None
                        count = 0
                        message = (f"{exc} Thử lại {failures}/{self.settings.max_read_failures}."
                                   if failures else str(exc))
                else:
                    now = time.monotonic()
                    display = demo.frame
                    count = 0
                    eyes, yawn, head = demo.measure(pipeline, now)
                snapshot_frame = (last_frame_for_snapshot if source == "CAMERA" and
                                  last_frame_seen_at is not None and now-last_frame_seen_at <= 0.5
                                  else raw_frame)
                result = controller.update(eyes, yawn, head, count > 0 or source == "DEMO", now, snapshot_frame, observed_new)
                if observed_new and previous is not None:
                    instant = 1/max(.0001, now-previous)
                    fps = instant if fps == 0 else .8*fps+.2*instant
                if observed_new:
                    previous = now
                jpeg = None
                if display is not None and source == "DEMO":
                    ok, encoded = cv2.imencode(".jpg", cv2.cvtColor(display, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, self.settings.jpeg_quality])
                    if ok:
                        jpeg = encoded.tobytes()
                current_message = (message if failures else "Đang mô phỏng dữ liệu; không sử dụng webcam." if source == "DEMO"
                                   else "Đã phát hiện khuôn mặt." if count else "Không thấy khuôn mặt. Kiểm tra ánh sáng và nhìn vào camera.")
                if eyes.model_message:
                    current_message = eyes.model_message
                if audio.settings.audio_enabled != self.audio_enabled:
                    audio.settings = replace(audio.settings, audio_enabled=self.audio_enabled)
                # Speech is owned by the visible browser panel, never a blocking camera call.
                audio_message = ''
                with self._lock:
                    # Analysis must never overwrite the newer camera preview.
                    preview = self._result
                    self._result = replace(result,
                        frame_rgb=None if source == "CAMERA" else display,
                        frame_jpeg=preview.frame_jpeg if source == "CAMERA" else jpeg,
                        frame_time=preview.frame_time if source == "CAMERA" else now,
                        preview_fps=preview.preview_fps if source == "CAMERA" else fps,
                        preview_published_at=preview.preview_published_at if source == "CAMERA" else now,
                        encode_ms=preview.encode_ms if source == "CAMERA" else 0,
                        landmark_count=count, fps=fps, message=current_message,
                        audio_message=audio_message, camera_ms=camera_ms, vision_ms=vision_ms)
                if failures >= self.settings.max_read_failures:
                    raise CameraError("Webcam đọc hình thất bại liên tiếp; đã dừng.")
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
                    logger.exception("Runtime cleanup failed")
                    status = CameraStatus.ERROR
                    message += f" Lỗi kết thúc phiên: {exc}"
            if capture_stream is not None:
                capture_stream.close()
                if capture_stream._thread.is_alive() and owns_camera:
                    # Keep exclusive ownership until a blocked driver actually exits.
                    def release_when_closed():
                        capture_stream._thread.join()
                        _camera_owner.release()
                    threading.Thread(target=release_when_closed, daemon=True).start()
                    owns_camera = False
            for resource in (pipeline, audio, camera if capture_stream is None else None, detector):
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
