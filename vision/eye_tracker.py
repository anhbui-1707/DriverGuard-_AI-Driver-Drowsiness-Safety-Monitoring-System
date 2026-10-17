"""Track model-supplied eye states and elapsed closure time; no EAR rules."""
from dataclasses import dataclass
from enum import Enum
from config import SETTINGS, Settings

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
    open_score: float | None = None
    model_message: str = ""

class EyeTracker:
    def __init__(self, settings: Settings = SETTINGS):
        self.settings = settings
        self.reset()

    def reset(self):
        self.state = EyeState.UNKNOWN
        self.duration = 0.0
        self.last_time = None
        self.last_valid_time = None
        self.last_confident_time = None
        self.previous_valid = False

    def update_score(self, score: float, now: float) -> EyeResult:
        """Hysteresis prevents an uncertain score oscillating around the model threshold."""
        center = self.settings.eye_model_threshold
        margin = self.settings.eye_model_hysteresis
        if score <= center-margin:
            state = EyeState.CLOSED
            self.last_confident_time = now
        elif score >= center+margin:
            state = EyeState.OPEN
            self.last_confident_time = now
        elif (self.previous_valid and self.last_confident_time is not None and
              now-self.last_confident_time <= self.settings.tracking_grace_seconds):
            state = self.state
        else:
            state = EyeState.UNKNOWN
        return self.update_state(state, now, open_score=score,
                                 sample_gap_limit=self.settings.eye_max_sample_gap_seconds)

    def update_state(self, state: EyeState, now: float, open_score=None, model_message="", sample_gap_limit=None) -> EyeResult:
        """Accumulate valid consecutive CLOSED observations, never missing time."""
        if self.last_time is not None and now < self.last_time:
            raise ValueError("Time must be monotonic")
        gap = now-self.last_valid_time if self.last_valid_time is not None else 0
        # Slow valid samples differ from an explicit tracking-loss observation.
        limit = self.settings.tracking_grace_seconds
        if sample_gap_limit is not None and self.previous_valid and state != EyeState.UNKNOWN:
            limit = sample_gap_limit
        if gap > limit:
            self.state = EyeState.UNKNOWN
            self.duration = 0.0
            self.previous_valid = False
        if state == EyeState.UNKNOWN:
            # An unknown sample breaks a continuous closure. Never carry the
            # previous alarm timer across lost face/crop/model confidence.
            self.state = EyeState.UNKNOWN
            self.duration = 0.0
            self.last_time = now
            self.last_valid_time = None
            self.last_confident_time = None
            self.previous_valid = False
            return EyeResult(model_message=model_message)
        old_state = self.state
        self.state = state
        if self.state == EyeState.CLOSED:
            if old_state == EyeState.CLOSED and self.previous_valid and self.last_time is not None:
                self.duration += now-self.last_time
        else:
            self.duration = 0.0
        self.last_valid_time = now
        self.last_time = now
        self.previous_valid = True
        return EyeResult(state=self.state, closure_seconds=self.duration,
                         open_score=open_score, model_message=model_message)
