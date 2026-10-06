import logging
from datetime import datetime
from pathlib import Path
from uuid import uuid4
import cv2
from config import ROOT


def save_snapshot(frame_bgr, root: Path = ROOT):
    if frame_bgr is None:
        return "", "Không có khung hình webcam để lưu (Demo hoặc camera mất hình)."
    relative = Path("assets/screenshots") / f"emergency_{datetime.now():%Y%m%d_%H%M%S}_{uuid4().hex[:8]}.jpg"
    try:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(destination), frame_bgr):
            raise OSError("OpenCV không ghi được ảnh")
        return relative.as_posix(), ""
    except (OSError, cv2.error) as exc:
        logging.getLogger(__name__).exception("Snapshot save failed")
        return "", f"Không lưu được snapshot: {exc}"
