"""Exercise the real model in the worker without physical camera hardware."""
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from dataclasses import replace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from core.runtime import MonitorRuntime
from config import SETTINGS


class BlankCamera:
    def __init__(self, settings):
        self.frame = np.zeros((480, 640, 3), dtype=np.uint8)

    def open(self):
        pass

    def read(self):
        return self.frame.copy()

    def close(self):
        pass


def main():
    temp = TemporaryDirectory(prefix="driverguard-smoke-")
    runtime = MonitorRuntime(replace(SETTINGS, database_path=Path(temp.name)/'test.db'), camera_factory=BlankCamera)
    runtime.start()
    deadline = time.monotonic() + 10
    try:
        while runtime.latest().frame_rgb is None and runtime.is_active() and time.monotonic() < deadline:
            runtime.heartbeat()
            time.sleep(0.05)
        assert runtime.latest().frame_rgb is not None, runtime.latest().message
    finally:
        runtime.stop()
    assert not runtime.is_active(), runtime.latest().message
    temp.cleanup()
    print("PASS: real model processes frames in worker and closes on Stop.")


if __name__ == "__main__":
    main()
