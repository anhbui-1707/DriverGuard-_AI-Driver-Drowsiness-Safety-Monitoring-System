"""Small loopback-only HTTP bridge. Video never uses Streamlit media URLs.

The existing runtime remains the sole owner of camera, safety timers and SQLite.
This server only exposes the latest image, JSON indicators and a command queue.
"""
import atexit
import json
import logging
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from core.types import CameraStatus

ASSETS = Path(__file__).resolve().parent / "assets"
logger = logging.getLogger(__name__)


def state_payload(runtime):
    result = runtime.latest()
    return dict(active=runtime.is_active(), status=result.status.value, message=result.message,
                source=result.source, session_id=result.session_id, session_seconds=result.session_seconds,
                face_detected=result.face_detected, eye_state=result.eyes.state.value,
                ear=result.eyes.ear, open_score=result.eyes.open_score, eye_model_message=result.eyes.model_message, eye_closure=result.eyes.closure_seconds, mar=result.mar, yawn_score=result.yawn_score,
                mouth_open=result.mouth_open, yawn_count=result.yawn_count, drowsiness_count=result.drowsiness_count, distraction_count=result.distraction_count, recent_yawns=result.recent_yawns,
                rest_recommended=result.rest_recommended, head_direction=result.head_direction,
                distraction_seconds=result.distraction_seconds, risk_score=result.risk_score,
                risk_level=result.risk_level.value, system_state=result.system_state,
                confirmation_remaining=result.confirmation_remaining, events=list(result.events),
                avg_risk=result.avg_risk, max_risk=result.max_risk, emergency_count=result.emergency_count,
                fps=result.fps, preview_fps=result.preview_fps, camera_ms=result.camera_ms, vision_ms=result.vision_ms,
                frame_time=result.frame_time, encode_ms=result.encode_ms, has_frame=result.frame_jpeg is not None,
                storage_message=result.storage_message, audio_message=result.audio_message,
                audio_enabled=runtime.audio_enabled,
                thresholds=dict(eye_model=runtime.settings.eye_model_threshold, ear=runtime.settings.ear_closed_threshold,
                                closure=runtime.settings.eye_closure_threshold_seconds,
                                timeout=runtime.settings.confirmation_timeout_seconds,
                                yawn_count=runtime.settings.frequent_yawn_count,
                                yawn_window=runtime.settings.yawn_window_seconds))


class LiveBridge:
    def __init__(self, runtime):
        self.runtime = runtime
        self.token = secrets.token_urlsafe(24)
        self.closed = threading.Event()
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass  # Do not log the per-session URL token or every frame.

            def send_bytes(self, data, content_type, status=200, headers=None):
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Referrer-Policy", "no-referrer")
                for name, value in (headers or {}).items():
                    self.send_header(name, str(value))
                self.end_headers()
                self.wfile.write(data)

            def route(self):
                if self.headers.get("Host") != f"127.0.0.1:{bridge.port}":
                    return None
                parts = urlsplit(self.path).path.split("/")
                if len(parts) != 3 or not secrets.compare_digest(parts[1], bridge.token):
                    return None
                return parts[2]

            def do_GET(self):
                route = self.route()
                try:
                    if route in ("panel", "live.css", "live.js", "design.css", "voice.js"):
                        files = {"panel": ("live.html", "text/html; charset=utf-8"),
                                 "live.css": ("live.css", "text/css; charset=utf-8"),
                                 "live.js": ("live.js", "text/javascript; charset=utf-8"),
                                 "design.css": ("design.css", "text/css; charset=utf-8"),
                                 "voice.js": ("voice.js", "text/javascript; charset=utf-8")}
                        name, content_type = files[route]
                        self.send_bytes((ASSETS/name).read_bytes(), content_type)
                    elif route == "state":
                        bridge.runtime.heartbeat()
                        self.send_bytes(json.dumps(state_payload(bridge.runtime), ensure_ascii=False, allow_nan=False).encode(), "application/json")
                    elif route == "frame":
                        result = bridge.runtime.latest()
                        try:
                            since = float(self.headers.get("X-Last-Frame-Time", "-1"))
                        except ValueError:
                            since = -1
                        if result.frame_jpeg is None or result.frame_time == since:
                            self.send_bytes(b"", "image/jpeg", 204)
                        else:
                            age_ms = max(0, time.monotonic()-(result.frame_time or time.monotonic()))*1000
                            self.send_bytes(result.frame_jpeg, "image/jpeg", headers={"X-Frame-Age-Ms": round(age_ms,2), "X-Frame-Time": result.frame_time})
                    elif route == "video":
                        self.stream_video()
                    else:
                        self.send_bytes(b"Not found", "text/plain", 404)
                except (BrokenPipeError, ConnectionResetError):
                    pass  # Browser closed the stream; not a camera failure.
                except (OSError, ValueError) as exc:
                    logger.exception("Local live view failed")
                    self.send_bytes(str(exc).encode(), "text/plain", 500)

            def stream_video(self):
                self.send_response(200)
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                previous = None
                while not bridge.closed.is_set():
                    result = bridge.runtime.latest()
                    if result.status not in (CameraStatus.STARTING, CameraStatus.RUNNING):
                        return
                    if result.frame_jpeg and result.frame_time != previous:
                        frame = result.frame_jpeg
                        self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " + str(len(frame)).encode() + b"\r\n\r\n" + frame + b"\r\n")
                        self.wfile.flush()
                        previous = result.frame_time
                    bridge.closed.wait(.025)

            def do_POST(self):
                if self.route() != "command":
                    self.send_bytes(b"Not found", "text/plain", 404)
                    return
                origin = self.headers.get("Origin")
                if origin and origin != bridge.origin:
                    self.send_bytes(b"Origin not allowed", "text/plain", 403)
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if length < 1 or length > 1024 or self.headers.get("Content-Type") != "application/json":
                        raise ValueError("Invalid request")
                    data = json.loads(self.rfile.read(length))
                    action = data.get("action")
                    if action == "START":
                        bridge.runtime.start(data.get("source", "CAMERA"))
                    elif action == "STOP":
                        bridge.runtime.stop()
                    elif action == "AUDIO":
                        if not isinstance(data.get("enabled"), bool):
                            raise ValueError("Audio enabled must be a boolean")
                        bridge.runtime.set_audio_enabled(data["enabled"])
                    elif action in ("CONFIRM", "RESET", "RECENTER", "YAWN", "DISTRACTION", "DROWSINESS", "CRITICAL", "EMERGENCY"):
                        bridge.runtime.command(action)
                    else:
                        raise ValueError("Unknown command")
                    self.send_bytes(b'{"ok":true}', "application/json")
                except (ValueError, TypeError, AttributeError) as exc:
                    self.send_bytes(json.dumps({"error": str(exc)}).encode(), "application/json", 400)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.port = self.server.server_address[1]
        self.origin = f"http://127.0.0.1:{self.port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True, name="DriverGuard-live-view")
        self.thread.start()
        atexit.register(self.close)

    def url(self, route="panel"):
        return f"{self.origin}/{self.token}/{route}"

    def close(self):
        if not self.closed.is_set():
            self.closed.set()
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(timeout=2)
