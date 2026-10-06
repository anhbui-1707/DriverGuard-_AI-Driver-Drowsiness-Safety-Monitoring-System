from types import SimpleNamespace
import pytest
from vision.eye_detector import EyeDetector, EyeState, LEFT_EYE, RIGHT_EYE, eye_aspect_ratio
from config import SETTINGS
from dataclasses import replace


def face(ear):
    points = [SimpleNamespace(x=.5, y=.5) for _ in range(478)]
    for indices in (LEFT_EYE, RIGHT_EYE):
        coordinates = [(0,0),(.3,ear/2),(.7,ear/2),(1,0),(.7,-ear/2),(.3,-ear/2)]
        for index, (x,y) in zip(indices, coordinates):
            points[index] = SimpleNamespace(x=x, y=y)
    return points


def test_ear_geometry():
    assert eye_aspect_ratio([(0,0),(.3,.1),(.7,.1),(1,0),(.7,-.1),(.3,-.1)]) == pytest.approx(.2)
    assert eye_aspect_ratio([(0,0)]*6) is None


def test_elapsed_time_and_open_reset():
    detector = EyeDetector()
    detector.update(face(.1),100,100,0)
    for i in range(1,51):
        result = detector.update(face(.1),100,100,i*.1)
    assert result.closure_seconds == pytest.approx(5)
    assert result.state == EyeState.CLOSED
    assert detector.update(face(.3),100,100,5.1).closure_seconds == 0


def test_blink():
    detector = EyeDetector()
    detector.update(face(.3),100,100,0)
    detector.update(face(.1),100,100,.1)
    assert detector.update(face(.1),100,100,.2).closure_seconds == pytest.approx(.1)
    assert detector.update(face(.3),100,100,.3).closure_seconds == 0


def test_tracking_loss():
    detector = EyeDetector()
    detector.update(face(.1),100,100,0)
    detector.update(face(.1),100,100,.2)
    missing = detector.update([],100,100,.3)
    assert missing.state == EyeState.UNKNOWN and missing.ear is None
    assert detector.update(face(.1),100,100,.4).closure_seconds == pytest.approx(.2)
    assert detector.update(face(.1),100,100,.5).closure_seconds == pytest.approx(.3)
    assert detector.update([],100,100,1.1).closure_seconds == 0
    assert detector.update(face(.1),100,100,1.2).closure_seconds == 0


def test_large_gap():
    detector = EyeDetector()
    detector.update(face(.1),100,100,0)
    assert detector.update(face(.1),100,100,5).closure_seconds == 0


def test_hysteresis():
    detector = EyeDetector()
    assert detector.update(face(.21),100,100,0).state == EyeState.UNKNOWN
    assert detector.update(face(.3),100,100,.1).state == EyeState.OPEN
    assert detector.update(face(.21),100,100,.2).state == EyeState.OPEN
    assert detector.update(face(.1),100,100,.3).state == EyeState.CLOSED
    assert detector.update(face(.21),100,100,.4).state == EyeState.CLOSED


def test_reset_invalid_and_time_order():
    detector = EyeDetector()
    detector.update(face(.1),100,100,0)
    detector.update(face(.1),100,100,.2)
    detector.reset()
    assert detector.update(face(.1),100,100,1).closure_seconds == 0
    assert detector.update(face(float('nan')),100,100,1.1).state == EyeState.UNKNOWN
    with pytest.raises(ValueError):
        detector.update([],100,100,0)


def test_per_session_auto_calibration_uses_open_eye_baseline():
    detector = EyeDetector(replace(SETTINGS, ear_calibration_seconds=1.0,
                                   ear_closed_ratio=.68, ear_open_ratio=.78))
    detector.begin_calibration()
    early = detector.update(face(.30), 100, 100, 0)
    assert early.calibrating and early.state == EyeState.UNKNOWN
    done = detector.update(face(.30), 100, 100, 1.0)
    assert not done.calibrating
    assert done.baseline_ear == pytest.approx(.30)
    assert done.closed_threshold == pytest.approx(.204)
    assert done.open_threshold == pytest.approx(.234)
    assert detector.update(face(.20), 100, 100, 1.1).state == EyeState.CLOSED
