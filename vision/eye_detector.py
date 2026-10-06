"""EAR geometry and observed eye-closure time, independent of camera/UI."""
from dataclasses import dataclass
from enum import Enum
import numpy as np
from config import SETTINGS, Settings

# Six points around each eye: corners plus two upper/lower pairs.
LEFT_EYE = (362, 385, 387, 263, 373, 380)
RIGHT_EYE = (33, 160, 158, 133, 153, 144)

class EyeState(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    UNKNOWN = "UNKNOWN"

@dataclass(frozen=True)
class EyeResult:
    state: EyeState = EyeState.UNKNOWN
    left_ear: float | None = None
    right_ear: float | None = None
    ear: float | None = None
    closure_seconds: float = 0.0
    calibrating: bool = False
    calibration_progress: float = 0.0
    baseline_ear: float | None = None
    closed_threshold: float | None = None
    open_threshold: float | None = None

def eye_aspect_ratio(points) -> float | None:
    points = np.asarray(points, dtype=float)
    if points.shape != (6, 2) or not np.isfinite(points).all():
        return None
    width = np.linalg.norm(points[0] - points[3])
    if width < 1e-6:
        return None
    # EAR = sum of two vertical distances / twice the horizontal distance.
    return float((np.linalg.norm(points[1]-points[5]) + np.linalg.norm(points[2]-points[4])) / (2*width))

class EyeDetector:
    def __init__(self, settings: Settings = SETTINGS):
        if not 0 < settings.ear_closed_threshold < settings.ear_open_threshold:
            raise ValueError("EAR thresholds must satisfy 0 < closed < open")
        self.settings = settings
        self.reset()

    def reset(self):
        self.state = EyeState.UNKNOWN
        self.duration = 0.0
        self.last_time = None
        self.last_valid_time = None
        self.previous_valid = False
        self.calibrating = False
        self.calibration_started = None
        self.calibration_values = []
        self.baseline_ear = None
        self.closed_threshold = self.settings.ear_closed_threshold
        self.open_threshold = self.settings.ear_open_threshold

    def begin_calibration(self):
        """Collect an open-eye EAR baseline for this monitoring session."""
        self.reset()
        self.calibrating = True

    def _calibration_progress(self):
        if not self.calibrating or self.calibration_started is None or self.last_time is None:
            return 0.0
        return min(1.0, max(0.0, (self.last_time-self.calibration_started) /
                            self.settings.ear_calibration_seconds))

    def _result(self, state=None, left=None, right=None, ear=None, duration=None):
        return EyeResult(self.state if state is None else state, left, right, ear,
                         self.duration if duration is None else duration,
                         self.calibrating, self._calibration_progress(), self.baseline_ear,
                         self.closed_threshold, self.open_threshold)

    def _finish_calibration(self):
        # Median resists one or two ordinary blinks during this short setup step.
        self.baseline_ear = float(np.median(self.calibration_values))
        self.closed_threshold = self.baseline_ear * self.settings.ear_closed_ratio
        self.open_threshold = self.baseline_ear * self.settings.ear_open_ratio
        self.calibrating = False
        self.state = EyeState.OPEN
        self.duration = 0.0

    def update(self, landmarks, width: int, height: int, now: float) -> EyeResult:
        left = right = None
        if landmarks and len(landmarks) > max(LEFT_EYE+RIGHT_EYE):
            def measure(indices):
                points = [(landmarks[i].x*width, landmarks[i].y*height) for i in indices]
                return eye_aspect_ratio(points)
            left, right = measure(LEFT_EYE), measure(RIGHT_EYE)
        return self.update_ear(left, right, now)

    def update_ear(self, left: float | None, right: float | None, now: float) -> EyeResult:
        """Demo uses the same closure timer and hysteresis as the webcam."""
        if self.last_time is not None and now < self.last_time:
            raise ValueError("Time must be monotonic")
        gap = now-self.last_valid_time if self.last_valid_time is not None else 0
        if gap > self.settings.tracking_grace_seconds:
            self.state = EyeState.UNKNOWN
            self.duration = 0.0
            self.previous_valid = False
        if left is None or right is None:
            self.last_time = now
            self.previous_valid = False
            return self._result(state=EyeState.UNKNOWN, duration=self.duration)
        ear = (left+right)/2
        if self.calibrating:
            if self.calibration_started is None:
                self.calibration_started = now
            self.calibration_values.append(ear)
            self.last_valid_time = now
            self.last_time = now
            self.previous_valid = True
            if now-self.calibration_started < self.settings.ear_calibration_seconds:
                return self._result(state=EyeState.UNKNOWN, left=left, right=right, ear=ear, duration=0.0)
            self._finish_calibration()
            return self._result(state=EyeState.OPEN, left=left, right=right, ear=ear, duration=0.0)
        old_state = self.state
        if ear <= self.closed_threshold:
            self.state = EyeState.CLOSED
        elif ear >= self.open_threshold:
            self.state = EyeState.OPEN
        # In the hysteresis band retain the last valid state, or UNKNOWN initially.
        if self.state == EyeState.CLOSED:
            if old_state == EyeState.CLOSED and self.previous_valid and self.last_time is not None:
                self.duration += now-self.last_time
        else:
            self.duration = 0.0
        self.last_valid_time = now
        self.last_time = now
        self.previous_valid = True
        return self._result(left=left, right=right, ear=ear)
