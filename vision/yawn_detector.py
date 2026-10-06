"""Mouth opening sustained over time is a potential yawn, not a diagnosis."""
from collections import deque
from dataclasses import dataclass
import numpy as np
from config import SETTINGS


@dataclass(frozen=True)
class YawnResult:
    mouth_open: bool = False
    yawn_count: int = 0
    mar: float | None = None
    recent_count: int = 0
    event: bool = False


class YawnDetector:
    def __init__(self, settings=SETTINGS):
        self.settings = settings
        self.opened = False
        self.observed_seconds = 0.0
        self.counted = False
        self.count = 0
        self.timestamps = deque()
        self.last_time = None
        self.previous_valid = False

    def update(self, landmarks, width, height, now):
        mar = None
        if landmarks and len(landmarks) > 308:
            points = np.array([(landmarks[i].x * width, landmarks[i].y * height)
                               for i in (13, 14, 78, 308)], dtype=float)
            horizontal = np.linalg.norm(points[2] - points[3])
            if np.isfinite(points).all() and horizontal > 1e-6:
                mar = float(np.linalg.norm(points[0] - points[1]) / horizontal)
        return self.update_mar(mar, now)

    def update_mar(self, mar, now):
        while self.timestamps and now - self.timestamps[0] > self.settings.yawn_window_seconds:
            self.timestamps.popleft()
        dt = now - self.last_time if self.last_time is not None else 0.0
        if dt < 0:
            raise ValueError("Time must be monotonic")
        self.last_time = now
        if mar is None or not np.isfinite(mar):
            self.previous_valid = False
            self.observed_seconds = 0.0
            return YawnResult(yawn_count=self.count, recent_count=len(self.timestamps))
        old_open = self.opened
        if mar >= self.settings.mar_open_threshold:
            self.opened = True
        elif mar <= self.settings.mar_closed_threshold:
            self.opened = False
        event = False
        if not self.opened:
            self.observed_seconds = 0.0
            self.counted = False
        elif self.previous_valid and old_open and dt <= self.settings.tracking_grace_seconds:
            self.observed_seconds += dt
        else:
            self.observed_seconds = 0.0
        if self.opened and not self.counted and self.observed_seconds >= self.settings.yawn_duration_seconds:
            self.count += 1
            self.counted = True
            self.timestamps.append(now)
            event = True
        self.previous_valid = True
        return YawnResult(self.opened, self.count, mar, len(self.timestamps), event)
