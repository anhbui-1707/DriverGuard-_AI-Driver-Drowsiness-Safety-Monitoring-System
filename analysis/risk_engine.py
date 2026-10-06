"""Explainable demo heuristic; not a scientifically validated probability."""
import math
from config import SETTINGS
from core.types import RiskLevel


def risk_level(score, settings=SETTINGS):
    if score >= settings.critical_risk:
        return RiskLevel.CRITICAL
    if score >= settings.drowsy_risk:
        return RiskLevel.DROWSY
    if score >= settings.warning_risk:
        return RiskLevel.WARNING
    return RiskLevel.SAFE


class RiskEngine:
    def __init__(self, settings=SETTINGS):
        self.settings = settings
        self.score = 0.0
        self.last_time = None

    def update(self, eyes, recent_yawns, head, face_detected, now, state="NORMAL"):
        s = self.settings
        eye = min(s.eye_risk_cap, eyes.closure_seconds / s.eye_closure_threshold_seconds * s.eye_risk_cap)
        yawn = min(s.yawn_risk_cap, recent_yawns * s.yawn_risk_per_event)
        distraction = min(s.distraction_risk_cap, head.distraction_seconds / s.distraction_threshold_seconds * s.distraction_risk_weight)
        reasons = []
        if eye > 0:
            reasons.append(f"Mắt nhắm {eyes.closure_seconds:.1f}s")
        if recent_yawns:
            reasons.append(f"{recent_yawns} lần ngáp gần đây")
        if head.distraction_seconds > 0:
            reasons.append(f"Hướng đầu lệch {head.distraction_seconds:.1f}s")
        if not face_detected:
            reasons.append("Không đủ dữ liệu khuôn mặt")
        target = min(100.0, eye + yawn + distraction) if face_detected else max(s.no_face_risk_floor, self.score)
        dt = max(0.0, now - self.last_time) if self.last_time is not None else 0.0
        alpha = 1 - math.exp(-dt / self.settings.risk_smoothing_seconds)
        self.score += (target - self.score) * alpha
        self.last_time = now
        if state in ("CONFIRMATION", "EMERGENCY"):
            self.score = max(self.score, float(self.settings.critical_risk))
        score = round(min(100.0, self.score), 1)
        return score, risk_level(score, self.settings), tuple(reasons)
