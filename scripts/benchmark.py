"""Measure CPU inference, not webcam/display FPS. Optional local test image."""
import argparse
import statistics
import sys
import time
from pathlib import Path
import cv2
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import SETTINGS
from core.pipeline import VisionPipeline
from vision.face_mesh import FaceMesh


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", help="Optional local face photo; never sent anywhere")
    parser.add_argument("--frames", type=int, default=100)
    args = parser.parse_args()
    frame = cv2.imread(args.image) if args.image else np.zeros((480,640,3),np.uint8)
    if frame is None:
        raise ValueError("Cannot read the supplied image")
    height, width = frame.shape[:2]
    frame = cv2.resize(frame,(640,round(height*640/width)))
    pipeline = VisionPipeline()
    detector = FaceMesh(SETTINGS)
    times = []
    try:
        for index in range(args.frames+5):
            tick = time.monotonic()
            display, count, eyes, yawn, head = pipeline.analyze(frame,detector,index*.05,tick)
            cv2.imencode('.jpg',cv2.cvtColor(display,cv2.COLOR_RGB2BGR),[cv2.IMWRITE_JPEG_QUALITY,75])
            if index >= 5:
                times.append((time.monotonic()-tick)*1000)
        print(f"landmarks={count}, EAR={eyes.ear}, MAR={yawn.mar}, head={head.direction}")
        print(f"Processing median={statistics.median(times):.1f}ms p95={np.percentile(times,95):.1f}ms")
        print("CPU/model benchmark only; webcam, Windows and browser must be tested separately.")
    finally:
        detector.close()


if __name__ == '__main__':
    main()
