from dataclasses import replace
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import cv2
import numpy as np
import pytest
from config import SETTINGS
from core.runtime import MonitorRuntime
from database.database import Repository
from ui.live_bridge import LiveBridge
from test_runtime import wait_until


@pytest.fixture
def bridge(tmp_path):
    settings=replace(SETTINGS,database_path=tmp_path/'bridge.db',snapshot_root=tmp_path,
                     eye_closure_threshold_seconds=.2,confirmation_timeout_seconds=.5)
    runtime=MonitorRuntime(settings)
    live=LiveBridge(runtime)
    yield live
    runtime.stop()
    live.close()


def get_state(bridge):
    with urlopen(bridge.url('state'),timeout=3) as response:
        return json.load(response)


def post(bridge,action,**values):
    data=json.dumps(dict(action=action,**values)).encode()
    with urlopen(Request(bridge.url('command'),data=data,headers={'Content-Type':'application/json'},method='POST'),timeout=5) as response:
        return json.load(response)


def test_live_assets_and_no_external_dependencies(bridge):
    for route,marker in [('panel',b'ARE YOU AWAKE?'),('live.css',b'--cyan'),('live.js',b'fetch("state"')]:
        with urlopen(bridge.url(route),timeout=3) as response:
            data=response.read()
            assert marker in data
            assert response.headers['Cache-Control']=='no-store'
            assert b'cdn.' not in data
    assert get_state(bridge)['eye_state']=='UNKNOWN'
    assert not get_state(bridge)['active']


def test_stream_is_real_jpeg_and_stop_saves_session(bridge):
    post(bridge,'START',source='DEMO')
    wait_until(lambda: bridge.runtime.latest().frame_jpeg is not None)
    with urlopen(bridge.url('video'),timeout=3) as stream:
        assert 'multipart/x-mixed-replace' in stream.headers['Content-Type']
        assert stream.readline()==b'--frame\r\n'
        assert stream.readline()==b'Content-Type: image/jpeg\r\n'
        length=int(stream.readline().split(b':')[1])
        assert stream.readline()==b'\r\n'
        jpeg=stream.read(length)
        decoded=cv2.imdecode(np.frombuffer(jpeg,np.uint8),cv2.IMREAD_COLOR)
        assert decoded.shape==(360,640,3)
    post(bridge,'STOP')
    assert not get_state(bridge)['active']
    with Repository(bridge.runtime.settings.database_path) as repository:
        assert repository.sessions()[0]['status']=='COMPLETED'


def test_http_confirmation_and_emergency_flow(bridge):
    post(bridge,'START',source='DEMO')
    wait_until(lambda: bridge.runtime.latest().frame_jpeg is not None)
    post(bridge,'DROWSINESS')
    wait_until(lambda: get_state(bridge)['system_state']=='CONFIRMATION')
    post(bridge,'CONFIRM')
    wait_until(lambda: get_state(bridge)['system_state']=='NORMAL')
    assert get_state(bridge)['eye_closure']==0
    wait_until(lambda: bridge.runtime.latest().session_seconds>1.6)
    post(bridge,'EMERGENCY')
    wait_until(lambda: get_state(bridge)['system_state']=='EMERGENCY')
    assert get_state(bridge)['emergency_count']==1
    post(bridge,'RESET')
    wait_until(lambda: get_state(bridge)['system_state']=='NORMAL')


def test_invalid_token_origin_and_command_rejected(bridge):
    with pytest.raises(HTTPError) as err:
        urlopen(f'{bridge.origin}/wrong/state',timeout=3)
    assert err.value.code==404
    request=Request(bridge.url('command'),data=b'{"action":"START"}',headers={'Content-Type':'application/json','Origin':'https://example.invalid'},method='POST')
    with pytest.raises(HTTPError) as err:
        urlopen(request,timeout=3)
    assert err.value.code==403
    assert not bridge.runtime.is_active()
    with pytest.raises(HTTPError) as err:
        post(bridge,'NOT_A_COMMAND')
    assert err.value.code==400


def test_mute_setting_applies_to_active_runtime(bridge):
    post(bridge,'AUDIO',enabled=False)
    assert not get_state(bridge)['audio_enabled']
    post(bridge,'START',source='DEMO')
    wait_until(lambda: bridge.runtime.latest().frame_jpeg is not None)
    assert not get_state(bridge)['audio_enabled']
    post(bridge,'AUDIO',enabled=False)
    assert not get_state(bridge)['audio_enabled']
