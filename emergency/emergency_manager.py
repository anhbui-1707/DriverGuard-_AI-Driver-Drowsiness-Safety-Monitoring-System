from enum import Enum
from config import SETTINGS


class EmergencyState(str, Enum):
    NORMAL = "NORMAL"
    CONFIRMATION = "CONFIRMATION"
    EMERGENCY = "EMERGENCY"


class EmergencyManager:
    def __init__(self, settings=SETTINGS):
        self.settings = settings
        self.state = EmergencyState.NORMAL
        self.deadline = None
        self.armed = True
        self.open_since = None
        self.last_open_observation = None
        self.rearm_at = None

    def update(self, closed_seconds, eye_state, now, observed_new=True, allow_drowsiness=True):
        # Escalation continues even if eyes reopen or the face disappears.
        event = None
        if self.state == EmergencyState.CONFIRMATION:
            if now >= self.deadline:
                self.state = EmergencyState.EMERGENCY
                self.deadline = None
                event = "EMERGENCY"
        elif self.state == EmergencyState.NORMAL:
            if not self.armed:
                if self.rearm_at is not None:
                    if now >= self.rearm_at:
                        self.armed = True
                        self.rearm_at = None
                elif eye_state == "OPEN" and observed_new:
                    if (self.last_open_observation is None or
                        now-self.last_open_observation > self.settings.tracking_grace_seconds):
                        self.open_since = now
                    self.last_open_observation = now
                    if now-self.open_since >= self.settings.awake_rearm_seconds:
                        self.armed = True
                elif eye_state != "OPEN":
                    self.open_since = None
                    self.last_open_observation = None
            if (allow_drowsiness and self.armed and eye_state == "CLOSED"
                    and closed_seconds >= self.settings.eye_closure_threshold_seconds):
                self.state = EmergencyState.CONFIRMATION
                self.deadline = now + self.settings.confirmation_timeout_seconds
                self.armed = False
                event = "DROWSINESS"
        return event

    def confirm(self, now):
        if self.state != EmergencyState.CONFIRMATION:
            return False
        if now >= self.deadline:
            self.state = EmergencyState.EMERGENCY
            self.deadline = None
            return False
        self.reset(now)
        return True

    def reset(self, now=None):
        self.state = EmergencyState.NORMAL
        self.deadline = None
        self.armed = False
        self.open_since = None
        self.last_open_observation = None
        # A manual click is an explicit acknowledgement. The eye model can
        # misclassify open eyes; do not block every later warning on it.
        self.rearm_at = (now + self.settings.awake_rearm_seconds) if now is not None else None

    def remaining(self, now):
        return max(0.0, self.deadline - now) if self.deadline is not None else 0.0
