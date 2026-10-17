"""Central settings. Paths do not depend on the terminal's working directory."""
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Settings:
    ear_closed_threshold: float = 0.20
    ear_open_threshold: float = 0.23
    eye_model_path: Path = ROOT / "models" / "eye_model_cew_v3.keras"
    eye_model_threshold: float = 0.5
    eye_model_hysteresis: float = 0.06
    tracking_grace_seconds: float = 0.5
    eye_closure_threshold_seconds: float = 3.0
    confirmation_timeout_seconds: float = 10.0
    awake_rearm_seconds: float = 1.0
    mar_open_threshold: float = 0.35
    mar_closed_threshold: float = 0.25
    yawn_model_path: Path = ROOT / "models" / "yawn_model_v2.keras"
    yawn_model_threshold: float = 0.5
    yawn_model_strong_threshold: float = 0.78
    yawn_model_support_threshold: float = 0.35
    yawn_mar_strong_threshold: float = 0.48
    yawn_score_smoothing_seconds: float = 0.10
    yawn_max_sample_gap_seconds: float = 1.5
    yawn_inference_interval_seconds: float = 0.125
    eye_max_sample_gap_seconds: float = 1.5
    yawn_lite_threads: int = 1
    eye_lite_threads: int = 1
    async_face_enabled: bool = False
    face_result_max_age_seconds: float = 0.5
    inference_cpu_threads: int = 2
    yawn_duration_seconds: float = 0.8
    yawn_window_seconds: float = 60.0
    frequent_yawn_count: int = 3
    head_yaw_threshold: float = 22.0
    head_pitch_threshold: float = 18.0
    distraction_threshold_seconds: float = 3.0
    risk_smoothing_seconds: float = 0.5
    warning_risk: int = 30
    drowsy_risk: int = 60
    critical_risk: int = 80
    eye_risk_cap: float = 70.0
    yawn_risk_per_event: float = 5.0
    yawn_risk_cap: float = 15.0
    distraction_risk_weight: float = 15.0
    distraction_risk_cap: float = 20.0
    no_face_risk_floor: float = 15.0
    audio_enabled: bool = True
    warning_audio_interval: float = 8.0
    show_landmarks: bool = False
    database_path: Path = ROOT / "data" / "driverguard.db"
    snapshot_root: Path = ROOT
    sample_interval_seconds: float = 1.0
    checkpoint_interval_seconds: float = 5.0
    jpeg_quality: int = 75
    camera_index: int = 0
    frame_width: int = 640
    processing_width: int = 480
    frame_height: int = 480
    preview_fps: float = 30.0
    target_fps: float = 30.0
    inference_fps: float = 12.0
    ui_refresh_seconds: float = 0.10
    indicators_refresh_seconds: float = 0.25
    heartbeat_timeout_seconds: float = 30.0
    stop_timeout_seconds: float = 3.0
    max_read_failures: int = 3
    detection_confidence: float = 0.5
    tracking_confidence: float = 0.5
    model_path: Path = ROOT / "models" / "face_landmarker.task"

    def __post_init__(self):
        if not (0 < self.yawn_model_support_threshold < self.yawn_model_threshold < self.yawn_model_strong_threshold < 1) or self.yawn_score_smoothing_seconds <= 0:
            raise ValueError("Ngưỡng model ngáp hoặc smoothing không hợp lệ")
        if self.yawn_mar_strong_threshold <= self.mar_open_threshold:
            raise ValueError("Ngưỡng MAR mạnh phải lớn hơn ngưỡng mở miệng")
        if not 0 < self.eye_model_threshold < 1 or not 0 <= self.eye_model_hysteresis < min(self.eye_model_threshold, 1-self.eye_model_threshold):
            raise ValueError("Ngưỡng model mắt hoặc vùng ổn định không hợp lệ")
        if not 0 < self.ear_closed_threshold < self.ear_open_threshold:
            raise ValueError("EAR: closed phải nhỏ hơn open")
        if not 0 < self.mar_closed_threshold < self.mar_open_threshold:
            raise ValueError("MAR: closed phải nhỏ hơn open")
        if not 0 < self.warning_risk < self.drowsy_risk < self.critical_risk <= 100:
            raise ValueError("Risk thresholds phải tăng dần trong 0–100")
        for name in ("face_result_max_age_seconds", "preview_fps", "target_fps", "inference_fps", "ui_refresh_seconds", "eye_closure_threshold_seconds",
                     "confirmation_timeout_seconds", "yawn_duration_seconds", "yawn_window_seconds",
                     "risk_smoothing_seconds", "distraction_threshold_seconds", "sample_interval_seconds",
                     "checkpoint_interval_seconds", "frequent_yawn_count"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} phải lớn hơn 0")


SETTINGS = Settings()
