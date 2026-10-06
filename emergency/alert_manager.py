"""Non-blocking Windows sound, changed only on transitions."""
import logging
import sys
from config import ROOT, SETTINGS


class AlertManager:
    def __init__(self, settings=SETTINGS, backend=None):
        self.settings = settings
        if backend is None and sys.platform == "win32":
            import winsound
            backend = winsound
        self.backend = backend
        self.current = None
        self.last_warning = float("-inf")
        self.message = "" if backend else "Âm thanh hỗ trợ trên Windows; cảnh báo hình ảnh vẫn hoạt động."

    def update(self, state, level, now):
        alarm = state in ("CONFIRMATION", "EMERGENCY") or level == "CRITICAL"
        desired = "ALARM" if alarm else "WARNING" if level in ("WARNING", "DROWSY") else "OFF"
        if not self.settings.audio_enabled:
            desired = "OFF"
        if self.backend is None:
            return self.message
        try:
            if desired != self.current:
                self.backend.PlaySound(None, 0)
                if desired == "ALARM":
                    sound = ROOT / "assets/sounds/alarm.wav"
                    if sound.exists():
                        self.backend.PlaySound(str(sound), self.backend.SND_FILENAME | self.backend.SND_ASYNC | self.backend.SND_LOOP)
                    else:
                        self.message = "Thiếu alarm.wav; dùng âm báo Windows thay thế."
                        self.backend.MessageBeep()
                self.current = desired
            if desired == "WARNING" and now-self.last_warning >= self.settings.warning_audio_interval:
                self.backend.MessageBeep()
                self.last_warning = now
            return self.message
        except RuntimeError as exc:
            logging.getLogger(__name__).exception("Audio unavailable")
            self.message = f"Âm thanh không khả dụng: {exc}. Cảnh báo hình ảnh vẫn hoạt động."
            return self.message

    def close(self):
        if self.backend:
            try:
                self.backend.PlaySound(None, 0)
            except RuntimeError:
                logging.getLogger(__name__).exception("Could not stop audio")
