"""Small data objects shared by the processing worker and the UI."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from vision.eye_detector import EyeResult
class RiskLevel(str, Enum):
    SAFE = "SAFE"
    WARNING = "WARNING"
    DROWSY = "DROWSY"
    CRITICAL = "CRITICAL"


class CameraStatus(str, Enum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class MonitorResult:
    status: CameraStatus = CameraStatus.STOPPED
    message: str = "Camera chưa được bật."
    frame_rgb: Any = None
    frame_jpeg: bytes | None = None
    face_detected: bool = False
    landmark_count: int = 0
    frame_time: float | None = None
    fps: float = 0.0
    camera_ms: float = 0.0
    vision_ms: float = 0.0
    eyes: EyeResult = field(default_factory=EyeResult)
    mouth_open: bool = False
    yawn_count: int = 0
    head_direction: str = "UNKNOWN"
    distraction_seconds: float = 0.0
    risk_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.SAFE
    system_state: str = "NORMAL"
    confirmation_remaining: float = 0.0
    mar: float | None = None
    recent_yawns: int = 0
    rest_recommended: bool = False
    yaw_degrees: float | None = None
    pitch_degrees: float | None = None
    risk_reasons: tuple[str, ...] = ()
    source: str = "CAMERA"
    session_id: int | None = None
    session_seconds: float = 0.0
    avg_risk: float = 0.0
    max_risk: float = 0.0
    drowsiness_count: int = 0
    distraction_count: int = 0
    emergency_count: int = 0
    events: tuple = ()
    storage_message: str = ""
    audio_message: str = ""
