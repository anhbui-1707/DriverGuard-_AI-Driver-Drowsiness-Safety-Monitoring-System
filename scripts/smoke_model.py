"""Load the real model and process two blank frames, without a webcam."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from config import SETTINGS
from vision.face_mesh import FaceMesh


def main():
    detector = FaceMesh(SETTINGS)
    try:
        blank = np.zeros((480, 640, 3), dtype=np.uint8)
        for timestamp in (0.0, 0.1):
            rgb, landmarks = detector.detect(blank, timestamp)
            assert rgb.shape == blank.shape
            assert not landmarks
        print("PASS: model loaded, VIDEO timestamps accepted, blank frames return no face.")
    finally:
        detector.close()


if __name__ == "__main__":
    main()
