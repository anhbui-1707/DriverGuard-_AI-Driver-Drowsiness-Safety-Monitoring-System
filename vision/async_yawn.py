"""One mouth worker and a single latest crop; timers stay on the safety thread."""
import csv
import logging
from pathlib import Path
from datetime import datetime
import threading
import time
from dataclasses import replace
import cv2
import numpy as np
from config import SETTINGS
from vision.mouth_crop import crop_mouth_rgb
from vision.yawn_classifier import YawnClassifier


class AsyncYawn:
    def __init__(self, settings=SETTINGS, factory=YawnClassifier):
        self.settings = settings
        self.factory = factory
        self._condition = threading.Condition()
        self._closed = False
        self._pending = None
        self._ready = None
        self._error = None
        self._epoch = 0
        self._last_submit = None
        self._last_result = None
        self._last_observation = None
        self.inference_ms = 0.0
        self.backend = "LOADING"
        self.completed_inferences = 0
        self._thread = threading.Thread(target=self._run, daemon=True, name="DriverGuard-yawn")
        self._thread.start()

    def _run(self):
        log_file = None
        try:
            classifier = self.factory(self.settings)
            self.backend = getattr(classifier, "backend", "INJECTED")
            try:
                directory = Path(__file__).resolve().parents[1]/"logs"
                directory.mkdir(exist_ok=True)
                log_file = (directory/f"yawn_inference_{datetime.now():%Y%m%d_%H%M%S_%f}.csv").open("w", newline="", encoding="utf-8")
                csv.writer(log_file).writerow(["backend", "observation_time", "queue_ms", "inference_ms", "result_age_ms", "raw_score", "mar", "pre_submit_ms"])
            except OSError as exc:
                logging.getLogger(__name__).warning("Không ghi được log ngáp: %s", exc)
            while True:
                with self._condition:
                    self._condition.wait_for(lambda: self._closed or self._pending is not None)
                    if self._closed:
                        return
                    crop, observed_at, epoch, submitted_at, pre_submit_ms, mar = self._pending
                    self._pending = None
                start = time.perf_counter()
                score = float(np.asarray(classifier.model(crop[None], training=False)).reshape(-1)[0])
                if not np.isfinite(score) or not 0 <= score <= 1:
                    raise ValueError("Model ngáp trả về score không hợp lệ")
                with self._condition:
                    self.inference_ms = (time.perf_counter()-start)*1000
                    self.completed_inferences += 1
                    if epoch == self._epoch and not self._closed:
                        self._ready = (score, observed_at, mar)
                if log_file is not None:
                    try:
                        csv.writer(log_file).writerow([self.backend, round(observed_at,4), round(max(0,start-submitted_at)*1000,2), round(self.inference_ms,2), round(pre_submit_ms+(time.perf_counter()-submitted_at)*1000,2), round(score,6), round(mar,4) if mar is not None else "", round(pre_submit_ms,2)])
                        log_file.flush()
                    except OSError as exc:
                        logging.getLogger(__name__).warning("Không ghi được log ngáp: %s", exc)
                        log_file.close()
                        log_file = None
        except Exception as exc:
            with self._condition:
                self._error = exc
        finally:
            if log_file is not None:
                log_file.close()

    def invalidate(self):
        with self._condition:
            self._epoch += 1
            self._pending = self._ready = None
        self._last_submit = None
        self._last_result = None
        self._last_observation = None

    def update(self, rgb, landmarks, timer, now, mar=None):
        with self._condition:
            error = self._error
        if error is not None:
            raise RuntimeError(f"Model ngáp: {error}") from error
        if not landmarks:
            self.invalidate()
            return timer.update_score(None, now)
        due = (self._last_submit is None or
               now-self._last_submit >= self.settings.yawn_inference_interval_seconds)
        if due:
            try:
                crop = crop_mouth_rgb(rgb, landmarks)
            except (ValueError, cv2.error):
                self.invalidate()
                return timer.update_mar_fallback(mar, now)
        with self._condition:
            ready = self._ready
            self._ready = None
            if due:
                self._pending = (crop.copy(), now, self._epoch, time.perf_counter(),
                                 max(0, time.monotonic()-now)*1000, mar)
                self._last_submit = now
                self._condition.notify()
        if ready is not None:
            score, observed_at, observed_mar = ready
            if now-observed_at <= self.settings.yawn_max_sample_gap_seconds:
                self._last_result = timer.update_score(score, observed_at, observed_mar)
                self._last_observation = observed_at
                return self._last_result
        if self._last_observation is None:
            # Do not advance the timer while waiting for the first real observation.
            from vision.yawn_tracker import YawnResult
            return YawnResult(yawn_count=timer.count)
        if now-self._last_observation > self.settings.yawn_max_sample_gap_seconds:
            self.invalidate()
            return timer.update_score(None, now)
        return replace(self._last_result, event=False)

    def close(self):
        with self._condition:
            self._closed = True
            self._pending = None
            self._condition.notify()
        self._thread.join(timeout=self.settings.stop_timeout_seconds)
