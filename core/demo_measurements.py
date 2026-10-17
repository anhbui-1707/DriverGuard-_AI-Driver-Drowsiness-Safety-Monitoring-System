"""EAR/MAR geometry and threshold rules are used only by synthetic Demo Mode."""
from dataclasses import replace
import numpy as np
from vision.eye_tracker import EyeState

LEFT_EYE = (362, 385, 387, 263, 373, 380)
RIGHT_EYE = (33, 160, 158, 133, 153, 144)


def eye_aspect_ratio(points):
    points = np.asarray(points, dtype=float)
    if points.shape != (6, 2) or not np.isfinite(points).all():
        return None
    width = np.linalg.norm(points[0]-points[3])
    if width < 1e-6:
        return None
    return float((np.linalg.norm(points[1]-points[5]) +
                  np.linalg.norm(points[2]-points[4])) / (2*width))


class DemoEyeInput:
    """Convert synthetic EAR values to states, then reuse the actual eye timer."""
    def __init__(self, tracker):
        self.tracker = tracker
        self.settings = tracker.settings

    def reset(self):
        self.tracker.reset()

    def update(self, landmarks, width, height, now):
        left = right = None
        if landmarks and len(landmarks) > max(LEFT_EYE+RIGHT_EYE):
            left = eye_aspect_ratio([(landmarks[i].x*width, landmarks[i].y*height) for i in LEFT_EYE])
            right = eye_aspect_ratio([(landmarks[i].x*width, landmarks[i].y*height) for i in RIGHT_EYE])
        return self.update_ear(left, right, now)

    def update_ear(self, left, right, now):
        ear = (left+right)/2 if left is not None and right is not None else None
        state = self.tracker.state
        last = self.tracker.last_valid_time
        if last is not None and now-last > self.settings.tracking_grace_seconds:
            state = EyeState.UNKNOWN
        if ear is None or not np.isfinite(ear):
            state = EyeState.UNKNOWN
        elif ear <= self.settings.ear_closed_threshold:
            state = EyeState.CLOSED
        elif ear >= self.settings.ear_open_threshold:
            state = EyeState.OPEN
        result = self.tracker.update_state(state, now)
        if state == EyeState.UNKNOWN:
            return result
        return replace(result, left_ear=left, right_ear=right, ear=ear)


def update_demo_yawn(tracker, mar, now):
    if mar is None or not np.isfinite(mar):
        positive = None
    elif mar >= tracker.settings.mar_open_threshold:
        positive = True
    elif mar <= tracker.settings.mar_closed_threshold:
        positive = False
    else:
        positive = tracker.opened
    return tracker.update_signal(positive, now, mar=mar)
