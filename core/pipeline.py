"""Geometry only: safety decisions and storage belong to the worker."""
import cv2
from config import SETTINGS
from core.types import CameraStatus, MonitorResult
from vision.eye_detector import EyeDetector, LEFT_EYE, RIGHT_EYE
from vision.yawn_detector import YawnDetector
from vision.head_pose import HeadPoseDetector


class VisionPipeline:
    def __init__(self, settings=SETTINGS):
        self.settings = settings
        self.eyes = EyeDetector(settings)
        self.yawns = YawnDetector(settings)
        self.head = HeadPoseDetector(settings)

    def analyze(self, frame, detector, elapsed, now):
        rgb, landmarks = detector.detect(frame, elapsed)
        h, w = rgb.shape[:2]
        eyes = self.eyes.update(landmarks, w, h, now)
        yawn = self.yawns.update(landmarks, w, h, now)
        head = self.head.update(landmarks, w, h, now)
        if self.settings.show_landmarks:
            for index in LEFT_EYE + RIGHT_EYE + (13, 14, 78, 308):
                if index < len(landmarks):
                    point = landmarks[index]
                    cv2.circle(rgb, (int(point.x*w), int(point.y*h)), 2, (80, 210, 140), -1)
        return cv2.flip(rgb, 1), len(landmarks), eyes, yawn, head


def process_frame(frame_bgr, detector, elapsed, frame_time, fps, eye_detector=None,
                  yawn_detector=None, head_detector=None):
    """Compatibility helper for the real-model smoke test."""
    pipeline = VisionPipeline()
    if eye_detector is not None:
        pipeline.eyes = eye_detector
    if yawn_detector is not None:
        pipeline.yawns = yawn_detector
    if head_detector is not None:
        pipeline.head = head_detector
    display, count, eyes, yawn, head = pipeline.analyze(frame_bgr, detector, elapsed, frame_time)
    return MonitorResult(status=CameraStatus.RUNNING, frame_rgb=display, landmark_count=count,
                         face_detected=count > 0, eyes=eyes, mouth_open=yawn.mouth_open,
                         yawn_count=yawn.yawn_count, mar=yawn.mar, head_direction=head.direction,
                         distraction_seconds=head.distraction_seconds, frame_time=frame_time, fps=fps)
