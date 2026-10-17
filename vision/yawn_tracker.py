"""Track sustained yawns using model confidence with geometric MAR support."""
from collections import deque
from dataclasses import dataclass, replace
import math
import numpy as np
from config import SETTINGS


@dataclass(frozen=True)
class YawnResult:
    mouth_open: bool = False
    yawn_count: int = 0
    mar: float | None = None
    recent_count: int = 0
    event: bool = False
    yawn_score: float | None = None


class YawnTracker:
    def __init__(self, settings=SETTINGS):
        self.settings = settings
        self.opened = False
        self.observed_seconds = 0.0
        self.counted = False
        self.count = 0
        self.timestamps = deque()
        self.last_time = None
        self.previous_valid = False
        self.smoothed_score = None
        self.score_time = None

    def invalidate_tracking(self, now):
        result = self.update_score(None, max(now, self.last_time or now))
        # A delayed landmark callback has its own capture timestamp. After loss,
        # restart observed-time accumulation without deleting session counts.
        self.last_time = None
        return result

    def update_score(self, score, now, mar=None):
        """Fuse model and mouth opening, then count one sustained event."""
        if self.score_time is not None and now < self.score_time:
            raise ValueError("Time must be monotonic")
        if score is None:
            self.smoothed_score = None
            self.score_time = None
            return self.update_signal(None, now)
        if not np.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("Yawn model score must be in [0, 1]")
        gap = now - self.score_time if self.score_time is not None else 0
        if self.smoothed_score is None or gap > self.settings.tracking_grace_seconds:
            self.smoothed_score = float(score)
        else:
            alpha = 1 - math.exp(-gap / self.settings.yawn_score_smoothing_seconds)
            self.smoothed_score += alpha * (score - self.smoothed_score)
        self.score_time = now
        model = self.smoothed_score
        if mar is not None and np.isfinite(mar):
            mar = float(mar)
            positive = (model >= self.settings.yawn_model_strong_threshold or
                        (model >= self.settings.yawn_model_threshold and
                         mar >= self.settings.mar_closed_threshold) or
                        (model >= self.settings.yawn_model_support_threshold and
                         mar >= self.settings.yawn_mar_strong_threshold))
            # Small fluctuations within an ongoing wide opening do not split
            # one yawn into multiple events.
            if self.opened and model >= self.settings.yawn_model_support_threshold and mar >= self.settings.mar_closed_threshold:
                positive = True
        else:
            mar = None
            positive = model >= self.settings.yawn_model_threshold
        result = self.update_signal(positive, now, mar=mar, score=model)
        return replace(result, mouth_open=positive, yawn_score=float(score))

    def update_mar_fallback(self, mar, now):
        """Use only clearly wide mouth geometry when a model crop is invalid."""
        if mar is None or not np.isfinite(mar):
            return self.update_score(None, now)
        return self.update_signal(float(mar) >= self.settings.yawn_mar_strong_threshold,
                                  now, mar=float(mar))

    def update_signal(self, positive, now, mar=None, score=None):
        """Shared observed-time counter; a continuous signal counts once."""
        while self.timestamps and now - self.timestamps[0] > self.settings.yawn_window_seconds:
            self.timestamps.popleft()
        dt = now - self.last_time if self.last_time is not None else 0.0
        if dt < 0:
            raise ValueError("Time must be monotonic")
        self.last_time = now
        if positive is None:
            self.previous_valid = False
            self.opened = False
            self.counted = False
            self.observed_seconds = 0.0
            return YawnResult(yawn_count=self.count, recent_count=len(self.timestamps))
        old_open = self.opened
        self.opened = positive
        event = False
        if not self.opened:
            self.observed_seconds = 0.0
            self.counted = False
        elif self.previous_valid and old_open and dt <= self.settings.yawn_max_sample_gap_seconds:
            self.observed_seconds += dt
        else:
            self.observed_seconds = 0.0
        if self.opened and not self.counted and self.observed_seconds >= self.settings.yawn_duration_seconds:
            self.count += 1
            self.counted = True
            self.timestamps.append(now)
            event = True
        self.previous_valid = True
        return YawnResult(self.opened, self.count, mar, len(self.timestamps), event, score)
