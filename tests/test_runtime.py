"""Hardware-free tests use the real runtime and pipeline with fake devices."""
from dataclasses import replace
import time
from types import SimpleNamespace

import numpy as np
import pytest

from config import SETTINGS
from core.runtime import MonitorRuntime
from core.types import CameraStatus
from vision.camera import CameraError


def wait_until(predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("Worker did not reach the expected condition")


class FakeCamera:
    instances = []
    fail_open = False
    fail_read = False

    def __init__(self, settings):
        self.closed = False
        self.read_count = 0
        self.instances.append(self)

    def open(self):
        if self.fail_open:
            raise CameraError("Camera unavailable")

    def read(self):
        self.read_count += 1
        if self.fail_read:
            raise CameraError("Camera read failure")
        return np.zeros((48, 64, 3), dtype=np.uint8)

    def close(self):
        self.closed = True


class FakeDetector:
    instances = []
    has_face = True
    fail_detection = False

    def __init__(self, settings):
        self.closed = False
        self.instances.append(self)

    def detect(self, frame, elapsed):
        if self.fail_detection:
            raise RuntimeError("Detection failed")
        landmarks = [SimpleNamespace(x=0.5, y=0.5)] if self.has_face else []
        return frame.copy(), landmarks

    def close(self):
        self.closed = True


@pytest.fixture
def runtime(tmp_path):
    FakeCamera.instances = []
    FakeCamera.fail_open = False
    FakeCamera.fail_read = False
    FakeDetector.instances = []
    FakeDetector.has_face = True
    FakeDetector.fail_detection = False
    worker = MonitorRuntime(replace(SETTINGS, database_path=tmp_path/'test.db', snapshot_root=tmp_path), FakeCamera, FakeDetector)
    yield worker
    worker.stop()
    wait_until(lambda: not worker.is_active())


def test_start_stop_restart_and_duplicate_start(runtime):
    assert runtime.latest().status == CameraStatus.STOPPED
    assert runtime.start()
    assert not runtime.start()
    wait_until(lambda: runtime.latest().face_detected)
    result = runtime.latest()
    assert result.landmark_count == 1
    assert result.frame_rgb.shape == (48, 64, 3)
    runtime.stop()
    assert not runtime.is_active()
    assert runtime.latest().frame_rgb is None
    assert FakeCamera.instances[0].closed
    assert FakeDetector.instances[0].closed
    assert runtime.start()
    wait_until(lambda: runtime.latest().face_detected)


def test_face_disappears_and_returns(runtime):
    runtime.start()
    wait_until(lambda: runtime.latest().face_detected)
    FakeDetector.has_face = False
    wait_until(lambda: not runtime.latest().face_detected)
    assert runtime.latest().landmark_count == 0
    assert runtime.latest().status == CameraStatus.RUNNING
    FakeDetector.has_face = True
    wait_until(lambda: runtime.latest().face_detected)


@pytest.mark.parametrize("failure", ["open", "read", "detect"])
def test_errors_release_resources(runtime, failure):
    FakeCamera.fail_open = failure == "open"
    FakeCamera.fail_read = failure == "read"
    FakeDetector.fail_detection = failure == "detect"
    runtime.start()
    wait_until(lambda: not runtime.is_active())
    assert runtime.latest().status == CameraStatus.ERROR
    assert runtime.latest().message
    assert FakeCamera.instances[0].closed
    if failure == "open":
        assert not FakeDetector.instances
    else:
        assert FakeDetector.instances[0].closed


def test_second_tab_cannot_own_camera(runtime):
    runtime.start()
    wait_until(lambda: runtime.latest().face_detected)
    other = MonitorRuntime(runtime.settings, FakeCamera, FakeDetector)
    try:
        other.start()
        wait_until(lambda: not other.is_active())
        assert other.latest().status == CameraStatus.ERROR
        assert len(FakeCamera.instances) == 1
        runtime.stop()
        other.start()
        wait_until(lambda: other.latest().face_detected)
    finally:
        other.stop()


def test_lost_heartbeat_stops_and_releases(runtime):
    runtime.settings = replace(runtime.settings, heartbeat_timeout_seconds=0.15)
    runtime.start()
    wait_until(lambda: runtime.latest().face_detected)
    wait_until(lambda: not runtime.is_active())
    assert runtime.latest().status == CameraStatus.STOPPED
    assert FakeCamera.instances[0].closed


def test_heartbeat_keeps_worker_alive(runtime):
    runtime.settings = replace(runtime.settings, heartbeat_timeout_seconds=0.15)
    runtime.start()
    wait_until(lambda: runtime.latest().face_detected)
    for _ in range(8):
        runtime.heartbeat()
        time.sleep(0.04)
    assert runtime.is_active()


def test_missing_model_is_actionable_and_camera_is_released(runtime, tmp_path):
    from vision.face_mesh import FaceMesh
    runtime.detector_factory = FaceMesh
    runtime.settings = replace(runtime.settings, model_path=tmp_path / "missing.task")
    runtime.start()
    wait_until(lambda: not runtime.is_active())
    assert runtime.latest().status == CameraStatus.ERROR
    assert "download_model.py" in runtime.latest().message
    assert FakeCamera.instances[0].closed


def test_demo_emergency_full_worker_flow(runtime):
    runtime.settings = replace(runtime.settings, eye_closure_threshold_seconds=.2,
                               confirmation_timeout_seconds=.25)
    runtime.start('DEMO')
    wait_until(lambda: runtime.latest().frame_jpeg is not None)
    runtime.command('EMERGENCY')
    wait_until(lambda: runtime.latest().system_state=='CONFIRMATION')
    wait_until(lambda: runtime.latest().system_state=='EMERGENCY')
    assert runtime.latest().emergency_count==1
    assert not FakeCamera.instances
    runtime.command('RESET')
    wait_until(lambda: runtime.latest().system_state=='NORMAL')
    runtime.stop()
    from database.database import Repository
    with Repository(runtime.settings.database_path) as repository:
        row=repository.sessions()[0]
        assert row['emergency_count']==1
        assert row['drowsiness_count']==1
        assert row['status']=='COMPLETED'


def test_demo_worker_confirm_resets_eye_timer(runtime):
    runtime.settings = replace(runtime.settings, eye_closure_threshold_seconds=.2,
                               confirmation_timeout_seconds=2)
    runtime.start('DEMO')
    wait_until(lambda: runtime.latest().frame_jpeg is not None)
    runtime.command('DROWSINESS')
    wait_until(lambda: runtime.latest().system_state=='CONFIRMATION')
    runtime.command('CONFIRM')
    wait_until(lambda: runtime.latest().system_state=='NORMAL')
    assert runtime.latest().eyes.closure_seconds==0
    assert runtime.latest().emergency_count==0
    assert any(e['event_type']=='DRIVER_CONFIRMED_AWAKE' for e in runtime.latest().events)


def test_sqlite_initialization_failure_is_visible_without_opening_camera(runtime, tmp_path):
    blocker = tmp_path/'not-a-directory'
    blocker.touch()
    runtime.settings = replace(runtime.settings, database_path=blocker/'test.db')
    runtime.start()
    wait_until(lambda: not runtime.is_active())
    assert runtime.latest().status == CameraStatus.ERROR
    assert runtime.latest().message
    assert not FakeCamera.instances
