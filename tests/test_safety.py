from dataclasses import replace
import sqlite3
from types import SimpleNamespace
import numpy as np
import pytest
from config import SETTINGS
from core.controller import SafetyController
from core.demo import DemoInput
from core.pipeline import VisionPipeline
from database.database import Repository
from emergency.emergency_manager import EmergencyManager, EmergencyState
from emergency.alert_manager import AlertManager
from emergency.snapshot import save_snapshot
from vision.eye_detector import EyeResult, EyeState
from vision.yawn_detector import YawnDetector, YawnResult
from vision.head_pose import HeadPoseDetector, HeadResult
from analysis.risk_engine import RiskEngine, risk_level
from session.session_manager import SessionStats


def test_yawn_single_continuous_and_repeat():
    d = YawnDetector()
    for i in range(41):
        result = d.update_mar(.5, i*.1)
    assert result.yawn_count == 1
    d.update_mar(.1, 4.2)
    for i in range(43, 60):
        result = d.update_mar(.5, i*.1)
    assert result.yawn_count == 2
    result = d.update_mar(.1, 70)
    assert result.recent_count == 0


def test_short_mouth_open_and_tracking_loss_do_not_count():
    d = YawnDetector()
    d.update_mar(.5, 0)
    assert not d.update_mar(.5, .2).event
    d.update_mar(None, .3)
    assert not d.update_mar(.5, 3).event
    assert not d.update_mar(.1, 3.1).event
    assert d.count == 0


@pytest.mark.parametrize("yaw,pitch,direction", [(30, 0, "LEFT"), (-30, 0, "RIGHT"), (0, 25, "DOWN"), (0, -25, "UP")])
def test_head_directions_and_debounce(yaw, pitch, direction):
    d = HeadPoseDetector()
    assert d.update_angles(0, 0, 0).direction == "CENTER"
    events = 0
    for i in range(1, 51):
        result = d.update_angles(yaw, pitch, i*.1)
        events += result.event
    assert result.direction == direction
    assert events == 1
    assert d.update_angles(0, 0, 5.1).distraction_seconds == 0
    assert d.update_angles(None, None, 5.2).direction == "UNKNOWN"
    d.recenter()
    assert d.update_angles(yaw, pitch, 5.3).direction == "CENTER"


@pytest.mark.parametrize("score,level", [(0,"SAFE"),(29,"SAFE"),(30,"WARNING"),(60,"DROWSY"),(80,"CRITICAL"),(100,"CRITICAL")])
def test_risk_levels(score, level):
    assert risk_level(score).value == level


def test_risk_smoothing_and_no_face_is_not_safe_evidence():
    risk = RiskEngine()
    eyes = EyeResult(state=EyeState.CLOSED, closure_seconds=4)
    risk.update(eyes, 0, HeadResult(), True, 0)
    score, _, _ = risk.update(eyes, 0, HeadResult(), True, .1)
    assert 0 < score < 30
    risk.score = 70
    score, _, reasons = risk.update(EyeResult(), 0, HeadResult(), False, 1)
    assert score == 70
    assert "Không đủ dữ liệu khuôn mặt" in reasons


def test_confirmation_open_eyes_or_no_face_do_not_cancel_timeout():
    manager = EmergencyManager()
    assert manager.update(5, "CLOSED", 10) == "DROWSINESS"
    assert manager.remaining(12) == 8
    assert manager.update(0, "OPEN", 19) is None
    assert manager.update(0, "UNKNOWN", 20) == "EMERGENCY"
    assert manager.update(5, "CLOSED", 21) is None


def test_confirmation_success_rearm_requires_open_eyes():
    manager = EmergencyManager()
    manager.update(5, "CLOSED", 0)
    assert manager.confirm(9.99)
    assert manager.state == EmergencyState.NORMAL
    assert manager.remaining(10) == 0
    assert manager.update(9, "CLOSED", 10) is None
    manager.update(0, "OPEN", 11)
    manager.update(0, "UNKNOWN", 11.5)
    manager.update(0, "OPEN", 12)
    manager.update(0, "OPEN", 13.1)
    assert manager.update(5, "CLOSED", 18.1) == "DROWSINESS"


def test_late_confirmation_rejected():
    manager = EmergencyManager()
    manager.update(5, "CLOSED", 0)
    assert not manager.confirm(10)
    assert manager.state == EmergencyState.EMERGENCY


@pytest.fixture
def controller(tmp_path):
    settings = replace(SETTINGS, database_path=tmp_path/'test.db', snapshot_root=tmp_path)
    with Repository(settings.database_path) as repository:
        yield SafetyController(settings, repository, "CAMERA", 0)


def tick(controller, now, closure=0, recent=0, yawn_event=False, head=None, face=True, frame=None):
    eyes = EyeResult(state=EyeState.CLOSED if closure else EyeState.OPEN, closure_seconds=closure)
    return controller.update(eyes, YawnResult(yawn_count=recent, recent_count=recent, event=yawn_event), head or HeadResult(), face, now, frame)


def test_rest_warning_saved_once_and_rearms(controller):
    for now in (1, 2, 3):
        result = tick(controller, now, recent=3)
    assert result.rest_recommended
    assert [e['event_type'] for e in controller.events].count('REST_RECOMMENDED') == 1
    tick(controller, 65, recent=0)
    tick(controller, 66, recent=3)
    assert [e['event_type'] for e in controller.events].count('REST_RECOMMENDED') == 2


def test_emergency_snapshot_event_and_stats_saved_once(controller):
    tick(controller, 5, closure=5)
    frame = np.zeros((48,64,3), dtype=np.uint8)
    result = tick(controller, 15, face=False, frame=frame)
    tick(controller, 16, closure=8, frame=frame)
    assert result.system_state == "EMERGENCY"
    assert result.risk_score >= 80
    assert controller.stats.emergency_count == 1
    events = controller.repository.events(controller.session_id)
    emergency = [e for e in events if e['event_type'] == 'EMERGENCY']
    assert len(emergency) == 1
    assert (controller.settings.snapshot_root/emergency[0]['snapshot_path']).exists()
    controller.finish(20, "COMPLETED")
    session = controller.repository.sessions()[0]
    assert session['duration'] == 20
    assert session['emergency_count'] == session['drowsiness_count'] == 1
    assert session['max_risk'] >= 80
    assert session['avg_risk'] > 0
    assert session['status'] == "COMPLETED"
    assert controller.repository.samples(controller.session_id)


def test_controller_confirm_no_stale_immediate_trigger(controller):
    tick(controller, 5, closure=5)
    assert controller.confirm(6)
    result = tick(controller, 7, closure=7)
    assert result.system_state != 'CONFIRMATION'
    assert not controller.confirm(8)
    assert [e['event_type'] for e in controller.events].count('DRIVER_CONFIRMED_AWAKE') == 1


def test_controller_late_confirm_records_emergency(controller):
    tick(controller, 5, closure=5)
    assert not controller.confirm(15)
    tick(controller, 15)
    assert controller.stats.emergency_count == 1


def test_snapshot_write_failure_is_nonfatal(tmp_path, monkeypatch):
    monkeypatch.setattr('emergency.snapshot.cv2.imwrite', lambda *args: False)
    path, message = save_snapshot(np.zeros((8,8,3),dtype=np.uint8), tmp_path)
    assert not path
    assert 'Không lưu' in message


def test_database_migrates_old_schema_preserves_rows(tmp_path):
    path = tmp_path/'legacy.db'
    db = sqlite3.connect(path)
    db.execute('CREATE TABLE sessions(id INTEGER PRIMARY KEY,start_time TEXT,end_time TEXT,avg_risk REAL,max_risk REAL,yawn_count INTEGER,drowsiness_count INTEGER,distraction_count INTEGER,emergency_count INTEGER)')
    db.execute("INSERT INTO sessions VALUES(1,'2026-01-01',NULL,5,10,2,1,0,0)")
    db.commit()
    db.close()
    with Repository(path) as repository:
        assert repository.sessions()[0]['yawn_count'] == 2
        sid = repository.start_session('DEMO')
        repository.recover_interrupted()
        assert repository.sessions()[0]['status'] == 'INTERRUPTED'
        assert repository.sessions()[1]['status'] == 'COMPLETED'
        repository.save_event(sid, 'YAWN', 5, "O'Reilly; DROP TABLE sessions")
        assert len(repository.sessions()) == 2


def test_time_weighted_average():
    stats = SessionStats(0)
    stats.update(1, 80, 0)
    stats.update(4, 20, 0)
    stats.update(5, 0, 0)
    assert stats.as_dict()['avg_risk'] == 52


def test_audio_does_not_restart_every_frame():
    class Sound:
        SND_FILENAME=1
        SND_ASYNC=2
        SND_LOOP=4
        def __init__(self):
            self.calls=[]
            self.beeps=0
        def PlaySound(self, path, flags):
            self.calls.append((path,flags))
        def MessageBeep(self):
            self.beeps += 1
    sound = Sound()
    alert = AlertManager(backend=sound)
    for i in range(100):
        alert.update('CONFIRMATION','CRITICAL',i*.01)
    assert len(sound.calls) == 2
    alert.update('NORMAL','SAFE',2)
    assert len(sound.calls) == 3
    alert.close()


def test_demo_uses_normal_measurements_and_timers():
    settings = replace(SETTINGS, eye_closure_threshold_seconds=.5, confirmation_timeout_seconds=.5)
    pipeline = VisionPipeline(settings)
    demo = DemoInput(settings)
    demo.measure(pipeline, 0)
    demo.trigger('EMERGENCY', .1)
    manager = EmergencyManager(settings)
    transitions=[]
    for i in range(1, 16):
        eyes, _, _ = demo.measure(pipeline, i*.1)
        transition = manager.update(eyes.closure_seconds, eyes.state, i*.1)
        if transition:
            transitions.append(transition)
    assert transitions == ['DROWSINESS', 'EMERGENCY']


def test_head_geometry_solvepnp_and_down():
    import cv2
    d = HeadPoseDetector()
    camera = np.array([[640,0,320],[0,640,240],[0,0,1]],dtype=float)
    def landmarks(rotation):
        coordinates, _ = cv2.projectPoints(d.MODEL, np.array(rotation,dtype=float),
                                           np.array([0,0,1400],dtype=float),camera,np.zeros((4,1)))
        face = [SimpleNamespace(x=.5,y=.5) for _ in range(478)]
        for index, point in zip(d.INDICES, coordinates.reshape(-1,2)):
            face[index] = SimpleNamespace(x=point[0]/640,y=point[1]/480)
        return face
    assert d.update(landmarks([0,0,0]),640,480,0).direction=='CENTER'
    assert d.update(landmarks([0,.5,0]),640,480,.1).direction=='LEFT'
    assert d.update(landmarks([.5,0,0]),640,480,.2).direction=='DOWN'


def test_snapshot_failure_does_not_lose_emergency_event(controller, monkeypatch):
    monkeypatch.setattr('emergency.snapshot.cv2.imwrite', lambda *args: False)
    tick(controller,5,closure=5)
    result = tick(controller,15,frame=np.zeros((8,8,3),np.uint8))
    assert result.system_state=='EMERGENCY'
    assert 'Không lưu' in result.storage_message
    assert any(e['event_type']=='EMERGENCY' and not e['snapshot_path'] for e in controller.events)
