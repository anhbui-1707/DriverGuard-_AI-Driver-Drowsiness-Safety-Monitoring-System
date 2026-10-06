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

    def update(self, closed_seconds, eye_state, now):
        # Escalation continues even if eyes reopen or the face disappears.
        event = None
        if self.state == EmergencyState.CONFIRMATION:
            if now >= self.deadline:
                self.state = EmergencyState.EMERGENCY
                self.deadline = None
                event = "EMERGENCY"
        elif self.state == EmergencyState.NORMAL:
            if not self.armed:
                if eye_state == "OPEN":
                    if self.open_since is None:
                        self.open_since = now
                    if now - self.open_since >= self.settings.awake_rearm_seconds:
                        self.armed = True
                else:
                    self.open_since = None
            if self.armed and eye_state == "CLOSED" and closed_seconds >= self.settings.eye_closure_threshold_seconds:
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
        self.reset()
        return True

    def reset(self):
        self.state = EmergencyState.NORMAL
        self.deadline = None
        self.armed = False
        self.open_since = None

    def remaining(self, now):
        return max(0.0, self.deadline - now) if self.deadline is not None else 0.0
