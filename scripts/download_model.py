"""Download the official model once. Monitoring itself then works offline."""
from pathlib import Path
import urllib.request

URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
TARGET = Path(__file__).resolve().parents[1] / "models" / "face_landmarker.task"


def main() -> None:
    if TARGET.is_file():
        print(f"Model đã có: {TARGET}")
        return
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    temporary = TARGET.with_suffix(".download")
    try:
        with urllib.request.urlopen(URL, timeout=60) as response, temporary.open("wb") as output:
            import shutil
            shutil.copyfileobj(response, output)
        if temporary.stat().st_size < 1000000:
            raise RuntimeError("File model tải về quá nhỏ; hãy kiểm tra kết nối.")
        temporary.replace(TARGET)
        print(f"Đã tải model: {TARGET}")
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        raise SystemExit(f"Không tải được model: {exc}") from exc


if __name__ == "__main__":
    main()
