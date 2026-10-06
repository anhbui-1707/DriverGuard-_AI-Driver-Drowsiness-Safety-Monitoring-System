"""One understandable safety flow, shared by camera and demo."""
from collections import deque
from analysis.risk_engine import RiskEngine
from core.types import CameraStatus, MonitorResult, RiskLevel
from emergency.emergency_manager import EmergencyManager, EmergencyState
from emergency.snapshot import save_snapshot
from session.session_manager import SessionStats


class SafetyController:
    def __init__(self, settings, repository, source, now):
        self.settings = settings
        self.repository = repository
        self.session_id = repository.start_session(source)
        self.source = source
        self.risk = RiskEngine(settings)
        self.emergency = EmergencyManager(settings)
        self.stats = SessionStats(now)
        self.events = deque(maxlen=8)
        self.previous_level = RiskLevel.SAFE
        self.rest_active = False
        self.last_sample = self.last_checkpoint = now
        self.storage_message = ""

    def record(self, typ, score, description, snapshot=""):
        self.events.append(self.repository.save_event(self.session_id, typ, score, description, snapshot))

    def confirm(self, when):
        manager = self.emergency
        if manager.state != EmergencyState.CONFIRMATION or when >= manager.deadline:
            return False
        if manager.confirm(when):
            self.record("DRIVER_CONFIRMED_AWAKE", self.stats.previous_score, "Người dùng xác nhận đang tỉnh táo.")
            self.risk.score = 0
            return True
        return False

    def reset_emergency(self):
        if self.emergency.state == EmergencyState.EMERGENCY:
            self.emergency.reset()
            self.risk.score = 0
            self.record("EMERGENCY_RESET", self.stats.previous_score, "Kết thúc Emergency Simulation; chờ mắt mở để tái kích hoạt.")
            return True
        return False

    def update(self, eyes, yawn, head, face, now, frame_bgr=None):
        transition = self.emergency.update(eyes.closure_seconds, eyes.state, now)
        state = self.emergency.state.value
        score, level, reasons = self.risk.update(eyes, yawn.recent_count, head, face, now, state)
        if yawn.event:
            self.record("YAWN", score, f"Ngáp lần {yawn.yawn_count}; {yawn.recent_count} lần trong {self.settings.yawn_window_seconds:g}s.")
        rest = yawn.recent_count >= self.settings.frequent_yawn_count
        if rest and not self.rest_active:
            self.record("REST_RECOMMENDED", score, "Bạn ngáp nhiều lần. Bạn nên nghỉ ngơi.")
        self.rest_active = rest
        if head.event:
            self.stats.distraction_count += 1
            self.record("DISTRACTION", score, f"Hướng {head.direction}, kéo dài {head.distraction_seconds:.1f}s.")
        if transition == "DROWSINESS":
            self.stats.drowsiness_count += 1
            self.record(transition, score, "Mắt nhắm kéo dài; bắt đầu xác nhận ARE YOU AWAKE?")
        elif transition == "EMERGENCY":
            self.stats.emergency_count += 1
            snapshot, self.storage_message = save_snapshot(frame_bgr, self.settings.snapshot_root)
            self.record(transition, score, "EMERGENCY SIMULATION: không phản hồi trong thời hạn. " + self.storage_message, snapshot)
        if level == RiskLevel.CRITICAL and self.previous_level != RiskLevel.CRITICAL:
            self.record("CRITICAL", score, "Risk Score đạt mức CRITICAL (heuristic).")
        self.previous_level = level
        self.stats.update(now, score, yawn.yawn_count)
        if now-self.last_sample >= self.settings.sample_interval_seconds:
            self.repository.sample(self.session_id, self.stats.duration, score)
            self.last_sample = now
        if now-self.last_checkpoint >= self.settings.checkpoint_interval_seconds:
            self.repository.checkpoint(self.session_id, self.stats.as_dict())
            self.last_checkpoint = now
        metrics = self.stats.as_dict()
        # NORMAL is the emergency-manager state; UI also shows risk-based warning/drowsy.
        ui_state = state if state != "NORMAL" else level.value if level != RiskLevel.SAFE else "NORMAL"
        return MonitorResult(status=CameraStatus.RUNNING, eyes=eyes, face_detected=face,
                             mouth_open=yawn.mouth_open, mar=yawn.mar, yawn_count=yawn.yawn_count,
                             recent_yawns=yawn.recent_count, rest_recommended=rest,
                             head_direction=head.direction, distraction_seconds=head.distraction_seconds,
                             yaw_degrees=head.yaw, pitch_degrees=head.pitch,
                             risk_score=score, risk_level=level, risk_reasons=reasons,
                             system_state=ui_state, confirmation_remaining=self.emergency.remaining(now),
                             source=self.source, session_id=self.session_id, session_seconds=metrics["duration"],
                             avg_risk=metrics["avg_risk"], max_risk=metrics["max_risk"],
                             drowsiness_count=self.stats.drowsiness_count,
                             distraction_count=self.stats.distraction_count,
                             emergency_count=self.stats.emergency_count, events=tuple(self.events),
                             storage_message=self.storage_message)

    def finish(self, now, status):
        self.stats.update(now, self.stats.previous_score, self.stats.yawn_count)
        self.repository.checkpoint(self.session_id, self.stats.as_dict(), status)
