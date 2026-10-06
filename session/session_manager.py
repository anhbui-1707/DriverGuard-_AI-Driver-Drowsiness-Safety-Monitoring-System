"""Time-weighted statistics, independent of camera frame rate."""
class SessionStats:
    def __init__(self, now):
        self.started = self.previous = now
        self.previous_score = self.integral = self.duration = self.max_risk = 0.0
        self.yawn_count = self.drowsiness_count = self.distraction_count = self.emergency_count = 0

    def update(self, now, score, yawns):
        self.integral += self.previous_score * max(0, now-self.previous)
        self.previous = now
        self.duration = max(0, now-self.started)
        self.previous_score = score
        self.max_risk = max(self.max_risk, score)
        self.yawn_count = yawns

    def as_dict(self):
        return dict(duration=round(self.duration, 2),
                    avg_risk=round(self.integral/self.duration, 2) if self.duration else 0,
                    max_risk=self.max_risk, yawn_count=self.yawn_count,
                    drowsiness_count=self.drowsiness_count,
                    distraction_count=self.distraction_count, emergency_count=self.emergency_count)
