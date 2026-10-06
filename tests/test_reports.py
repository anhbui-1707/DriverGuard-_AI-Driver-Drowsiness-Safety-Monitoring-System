import io
import json
from urllib.error import HTTPError
from services.gemini_service import generate_report

SESSION = dict(id=1,duration=120,avg_risk=25,max_risk=80,yawn_count=3,
               drowsiness_count=1,distraction_count=1,emergency_count=0,source='DEMO',status='COMPLETED')


def test_report_without_key_local_fallback():
    text, source, message = generate_report(SESSION)
    assert source == 'LOCAL'
    assert '3 lần' in text
    assert message


def test_report_gemini_structured_summary_no_images():
    def opener(req, timeout):
        assert timeout == 15
        payload = json.loads(req.data)
        assert set(payload['contents'][0]['parts'][0]) == {'text'}
        assert 'snapshot' not in req.data.decode()
        assert 'DEMO' in req.data.decode()
        return io.BytesIO(json.dumps({'candidates':[{'content':{'parts':[{'text':'Báo cáo thử nghiệm'}]}}]}).encode())
    text, source, message = generate_report(SESSION,'fake-test-key',opener=opener)
    assert source == 'GEMINI'
    assert text == 'Báo cáo thử nghiệm'
    assert not message


def test_report_api_failure_fallback_hides_key():
    def opener(req, timeout):
        raise HTTPError(req.full_url,429,'Quota',{},None)
    text, source, message = generate_report(SESSION,'private-secret',opener=opener)
    assert source == 'LOCAL'
    assert 'HTTP 429' in message
    assert 'private-secret' not in text+message


def test_report_empty_response_fallback():
    text, source, _ = generate_report(SESSION, 'fake', opener=lambda *args,**kwargs: io.BytesIO(b'{}'))
    assert source == 'LOCAL'
