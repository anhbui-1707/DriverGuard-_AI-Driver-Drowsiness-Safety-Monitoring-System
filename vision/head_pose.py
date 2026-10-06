"""Relative head orientation with a forward-facing calibration baseline."""
from dataclasses import dataclass
import cv2
import numpy as np
from config import SETTINGS


@dataclass(frozen=True)
class HeadResult:
    direction: str = "UNKNOWN"
    distraction_seconds: float = 0.0
    yaw: float | None = None
    pitch: float | None = None
    event: bool = False


class HeadPoseDetector:
    # Approximate canonical face. Image coordinates and model both have y down.
    MODEL = np.array([(0,0,0), (0,330,-65), (-225,-170,-135),
                      (225,-170,-135), (-150,150,-125), (150,150,-125)], dtype=np.float64)
    INDICES = (1, 152, 33, 263, 61, 291)

    def __init__(self, settings=SETTINGS):
        self.settings = settings
        self.baseline = None
        self.last_time = None
        self.duration = 0.0
        self.was_away = False
        self.counted = False

    def recenter(self):
        self.baseline = None
        self.duration = 0.0
        self.was_away = False
        self.counted = False

    @staticmethod
    def angle_delta(value, reference):
        return (value - reference + 180) % 360 - 180

    def update(self, landmarks, width, height, now):
        if not landmarks or len(landmarks) <= max(self.INDICES):
            return self.update_angles(None, None, now)
        points = np.array([(landmarks[i].x * width, landmarks[i].y * height)
                           for i in self.INDICES], dtype=np.float64)
        if not np.isfinite(points).all():
            return self.update_angles(None, None, now)
        camera = np.array([[width,0,width/2], [0,width,height/2], [0,0,1]], dtype=np.float64)
        try:
            ok, rotation, _ = cv2.solvePnP(self.MODEL, points, camera, np.zeros((4,1)), flags=cv2.SOLVEPNP_ITERATIVE)
            if not ok:
                return self.update_angles(None, None, now)
            matrix, _ = cv2.Rodrigues(rotation)
            angles = cv2.decomposeProjectionMatrix(np.column_stack((matrix, np.zeros(3))))[6].ravel()
            return self.update_angles(float(angles[1]), float(angles[0]), now)
        except cv2.error:
            return self.update_angles(None, None, now)

    def update_angles(self, yaw, pitch, now):
        dt = now - self.last_time if self.last_time is not None else 0.0
        self.last_time = now
        if yaw is None or pitch is None:
            self.duration = 0.0
            self.was_away = False
            self.counted = False
            return HeadResult()
        if self.baseline is None:
            self.baseline = (yaw, pitch)
        yaw = self.angle_delta(yaw, self.baseline[0])
        pitch = self.angle_delta(pitch, self.baseline[1])
        direction = "CENTER"
        if yaw > self.settings.head_yaw_threshold:
            direction = "LEFT"
        elif yaw < -self.settings.head_yaw_threshold:
            direction = "RIGHT"
        elif pitch > self.settings.head_pitch_threshold:
            direction = "DOWN"
        elif pitch < -self.settings.head_pitch_threshold:
            direction = "UP"
        away = direction != "CENTER"
        if away and self.was_away and 0 <= dt <= self.settings.tracking_grace_seconds:
            self.duration += dt
        else:
            self.duration = 0.0
            self.counted = False
        event = away and not self.counted and self.duration >= self.settings.distraction_threshold_seconds
        if event:
            self.counted = True
        self.was_away = away
        return HeadResult(direction, self.duration, yaw, pitch, event)
