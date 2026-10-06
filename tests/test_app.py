from pathlib import Path
from dataclasses import replace

from streamlit.testing.v1 import AppTest

from config import SETTINGS
from core.runtime import MonitorRuntime
from test_runtime import FakeCamera, FakeDetector, wait_until
from database.database import Repository
import pytest
import json
from urllib.request import Request, urlopen


def send_command(bridge, action, **values):
    req = Request(bridge.url('command'),data=json.dumps(dict(action=action,**values)).encode(),headers={'Content-Type':'application/json'},method='POST')
    with urlopen(req,timeout=5) as response:
        assert response.status==200


def test_application_cold_start(tmp_path):
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.session_state["runtime"] = MonitorRuntime(replace(SETTINGS, database_path=tmp_path/'ui.db'))
    app.run(timeout=10)
    assert not app.exception
    assert not app.session_state["runtime"].is_active()
    bridge=app.session_state['live_bridge']
    with urlopen(bridge.url(),timeout=3) as response:
        assert b'DRIVERGUARD' in response.read()
    bridge.close()


def test_ui_start_stop_and_rerun(tmp_path):
    FakeCamera.fail_open = False
    FakeCamera.fail_read = False
    FakeDetector.has_face = True
    FakeDetector.fail_detection = False
    runtime = MonitorRuntime(replace(SETTINGS, database_path=tmp_path/'ui.db'), FakeCamera, FakeDetector)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.session_state["runtime"] = runtime
    try:
        app.run(timeout=10)
        assert not app.exception
        bridge=app.session_state['live_bridge']
        send_command(bridge,'START',source='CAMERA')
        wait_until(lambda: runtime.latest().face_detected)
        app.run(timeout=10)
        assert not app.exception
        assert app.session_state["runtime"] is runtime
        assert app.session_state['live_bridge'] is bridge
        send_command(bridge,'STOP')
        app.run(timeout=10)
        assert not app.exception
        assert not runtime.is_active()
    finally:
        runtime.stop()
        if 'live_bridge' in app.session_state:
            app.session_state['live_bridge'].close()


@pytest.mark.parametrize('page', ['Tổng quan','Lịch sử phiên','Sự kiện an toàn','Báo cáo phiên','Cấu hình'])
def test_all_pages_render_with_data(tmp_path, page):
    settings = replace(SETTINGS, database_path=tmp_path/'pages.db')
    with Repository(settings.database_path) as repository:
        sid = repository.start_session('DEMO')
        repository.save_event(sid,'YAWN',10,'Một lần ngáp')
        repository.sample(sid,1,10)
        repository.checkpoint(sid,dict(duration=12,avg_risk=10,max_risk=20,yawn_count=1,drowsiness_count=0,distraction_count=0,emergency_count=0),'COMPLETED')
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'))
    app.session_state['runtime'] = MonitorRuntime(settings)
    app.run(timeout=10)
    app.radio(key='navigation').set_value(page).run(timeout=10)
    assert not app.exception
    app.session_state['live_bridge'].close()


def test_ui_demo_yawns_rest_warning_and_save(tmp_path):
    settings = replace(SETTINGS, database_path=tmp_path/'demo.db', yawn_duration_seconds=.15)
    runtime = MonitorRuntime(settings)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'))
    app.session_state['runtime'] = runtime
    try:
        app.run(timeout=10)
        bridge=app.session_state['live_bridge']
        send_command(bridge,'START',source='DEMO')
        wait_until(lambda: runtime.latest().frame_jpeg is not None)
        for count in range(1,4):
            # Use the same endpoint as the HTML UI buttons.
            send_command(bridge,'YAWN')
            wait_until(lambda: runtime.latest().yawn_count==count)
            wait_until(lambda: not runtime.latest().mouth_open)
        app.run(timeout=10)
        assert runtime.latest().rest_recommended
        assert not app.exception
        send_command(bridge,'STOP')
        with Repository(settings.database_path) as repository:
            row=repository.sessions()[0]
            assert row['yawn_count']==3
            assert row['source']=='DEMO'
            assert row['status']=='COMPLETED'
    finally:
        runtime.stop()
        if 'live_bridge' in app.session_state:
            app.session_state['live_bridge'].close()
