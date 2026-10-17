"""Geometry only: safety decisions and storage belong to the worker."""
import cv2
import math
from dataclasses import replace
import time
import csv
import logging
from pathlib import Path
from datetime import datetime
from config import SETTINGS
from core.types import CameraStatus, MonitorResult
from vision.eye_tracker import EyeTracker
from vision.eye_classifier import EyeClassifier, LEFT_CONTOUR, RIGHT_CONTOUR
from vision.yawn_tracker import YawnTracker
from vision.async_yawn import AsyncYawn
from vision.head_pose import HeadPoseDetector


class VisionPipeline:
    def __init__(self, settings=SETTINGS):
        self.settings = settings
        self.eyes = EyeTracker(settings)
        self.yawns = YawnTracker(settings)
        self.head = HeadPoseDetector(settings)
        self.eye_classifier = None
        self.yawn_classifier = None
        self._profile = None
        self._last_log = 0.0

    def analyze(self, frame, detector, elapsed, now, eye_frame=None):
        started = time.perf_counter()
        rgb, landmarks = detector.detect(frame, elapsed)
        face_ms = (time.perf_counter()-started)*1000
        return self.analyze_landmarks(rgb, landmarks, elapsed, now, eye_frame, face_ms, started)

    def analyze_landmarks(self, rgb, landmarks, elapsed, now, eye_frame=None, face_ms=0.0, started=None):
        if started is None:
            started = time.perf_counter()
        h, w = rgb.shape[:2]
        # Load once in the worker; classify before display mirroring/landmark drawing.
        if self.eye_classifier is None:
            self.eye_classifier = EyeClassifier(self.settings)
        eye_rgb = rgb if eye_frame is None else cv2.cvtColor(eye_frame, cv2.COLOR_BGR2RGB)
        eye_started = time.perf_counter()
        eyes = self.eye_classifier.update(eye_rgb, landmarks, self.eyes, now)
        eye_ms = (time.perf_counter()-eye_started)*1000
        # Geometry is cheap and stays paired with the capture timestamp used
        # by the asynchronous yawn model.
        mar = None
        if landmarks:
            try:
                def distance(a, b):
                    p, q = landmarks[a], landmarks[b]
                    return math.hypot((p.x-q.x)*w, (p.y-q.y)*h)
                left = (distance(160, 144)+distance(158, 153))/(2*max(distance(33, 133), 1e-6))
                right = (distance(385, 380)+distance(387, 373))/(2*max(distance(362, 263), 1e-6))
                mar = distance(13, 14)/max(distance(78, 308), 1e-6)
                eyes = replace(eyes, left_ear=left, right_ear=right, ear=(left+right)/2)
            except (IndexError, AttributeError, TypeError):
                pass
        if self.yawn_classifier is None:
            self.yawn_classifier = AsyncYawn(self.settings)
        mouth_started = time.perf_counter()
        yawn = self.yawn_classifier.update(eye_rgb, landmarks, self.yawns, now, mar=mar)
        mouth_ms = (time.perf_counter()-mouth_started)*1000
        yawn = replace(yawn, mar=mar)
        head = self.head.update(landmarks, w, h, now)
        if self.settings.show_landmarks:
            for index in LEFT_CONTOUR + RIGHT_CONTOUR + (13, 14, 78, 308):
                if index < len(landmarks):
                    point = landmarks[index]
                    cv2.circle(rgb, (int(point.x*w), int(point.y*h)), 2, (80, 210, 140), -1)
        try:
            if now-self._last_log >= 1:
                if self._profile is None:
                    directory = Path(__file__).resolve().parents[1]/"logs"
                    directory.mkdir(exist_ok=True)
                    self._profile = (directory/f"performance_{datetime.now():%Y%m%d_%H%M%S_%f}.csv").open("w", newline="", encoding="utf-8")
                    csv.writer(self._profile).writerow(["session_seconds", "face_ms", "eye_ms", "mouth_prepare_ms", "yawn_inference_ms", "analysis_ms", "yawn_backend", "yawn_completed", "eye_backend"])
                csv.writer(self._profile).writerow([round(elapsed,2), round(face_ms,2), round(eye_ms,2), round(mouth_ms,2), round(self.yawn_classifier.inference_ms,2), round((time.perf_counter()-started)*1000,2), self.yawn_classifier.backend, self.yawn_classifier.completed_inferences, getattr(self.eye_classifier, "backend", "INJECTED")])
                self._profile.flush()
                self._last_log = now
        except OSError as exc:
            logging.getLogger(__name__).warning("Không ghi được logs hiệu năng: %s", exc)
            if self._profile is not None:
                self._profile.close()
                self._profile = None
            self._last_log = now
        return cv2.flip(rgb, 1), len(landmarks), eyes, yawn, head

    def invalidate_camera_tracking(self, now):
        from vision.eye_tracker import EyeResult
        self.eyes.reset()
        if self.yawn_classifier is not None:
            self.yawn_classifier.invalidate()
        yawn = self.yawns.invalidate_tracking(now)
        head = self.head.update_angles(None, None, now)
        self.head.last_time = None
        return EyeResult(), yawn, head

    def close(self):
        if self.yawn_classifier is not None:
            self.yawn_classifier.close()
        if self._profile is not None:
            self._profile.close()


def process_frame(frame_bgr, detector, elapsed, frame_time, fps, eye_tracker=None,
                  yawn_tracker=None, head_detector=None):
    """Compatibility helper for the real-model smoke test."""
    pipeline = VisionPipeline()
    if eye_tracker is not None:
        pipeline.eyes = eye_tracker
    if yawn_tracker is not None:
        pipeline.yawns = yawn_tracker
    if head_detector is not None:
        pipeline.head = head_detector
    try:
        display, count, eyes, yawn, head = pipeline.analyze(frame_bgr, detector, elapsed, frame_time)
    finally:
        pipeline.close()
    return MonitorResult(status=CameraStatus.RUNNING, frame_rgb=display, landmark_count=count,
                         face_detected=count > 0, eyes=eyes, mouth_open=yawn.mouth_open,
                         yawn_count=yawn.yawn_count, mar=yawn.mar, head_direction=head.direction,
                         distraction_seconds=head.distraction_seconds, frame_time=frame_time, fps=fps)
