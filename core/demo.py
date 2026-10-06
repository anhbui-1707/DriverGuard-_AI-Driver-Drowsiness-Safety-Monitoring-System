"""Synthetic measurements only: no fake camera face, no bypass of safety logic."""
import cv2
import numpy as np


class DemoInput:
    def __init__(self, settings):
        self.settings = settings
        self.clear()
        self.frame = np.full((360, 640, 3), (239, 234, 224), dtype=np.uint8)
        cv2.putText(self.frame, "DRIVERGUARD / DEMO", (55, 145), cv2.FONT_HERSHEY_SIMPLEX, 1, (80, 65, 40), 2)
        cv2.putText(self.frame, "Simulated measurements - no webcam", (55, 185), cv2.FONT_HERSHEY_SIMPLEX, .6, (110, 95, 75), 1)

    def clear(self):
        self.eye_until = self.yawn_until = self.head_until = float("-inf")

    def trigger(self, command, now):
        s = self.settings
        if command == "YAWN":
            self.yawn_until = max(self.yawn_until, now+s.yawn_duration_seconds+.4)
        elif command == "DISTRACTION":
            self.head_until = now+s.distraction_threshold_seconds+1
        elif command in ("DROWSINESS", "CRITICAL", "EMERGENCY"):
            self.eye_until = now+s.eye_closure_threshold_seconds+1
            if command == "EMERGENCY":
                self.eye_until += s.confirmation_timeout_seconds+1
            if command == "CRITICAL":
                self.head_until = self.eye_until
                self.yawn_until = now+s.yawn_duration_seconds+.4

    def measure(self, pipeline, now):
        s = self.settings
        ear = s.ear_closed_threshold*.5 if now < self.eye_until else s.ear_open_threshold+.05
        mar = s.mar_open_threshold+.15 if now < self.yawn_until else s.mar_closed_threshold*.5
        yaw = s.head_yaw_threshold+10 if now < self.head_until else 0
        return (pipeline.eyes.update_ear(ear, ear, now), pipeline.yawns.update_mar(mar, now),
                pipeline.head.update_angles(yaw, 0, now))
