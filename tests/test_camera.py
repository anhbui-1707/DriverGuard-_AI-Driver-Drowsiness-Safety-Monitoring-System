from unittest.mock import Mock

import pytest

from config import SETTINGS
from vision.camera import Camera, CameraError


def test_failed_open_releases_capture(monkeypatch):
    capture = Mock()
    capture.isOpened.return_value = False
    monkeypatch.setattr("vision.camera.cv2.VideoCapture", lambda *args: capture)
    camera = Camera(SETTINGS)
    with pytest.raises(CameraError):
        camera.open()
    assert capture.release.called


def test_read_failure_and_close_are_safe():
    capture = Mock()
    capture.read.return_value = (False, None)
    camera = Camera(SETTINGS)
    camera.capture = capture
    with pytest.raises(CameraError):
        camera.read()
    camera.close()
    camera.close()
    capture.release.assert_called_once()
