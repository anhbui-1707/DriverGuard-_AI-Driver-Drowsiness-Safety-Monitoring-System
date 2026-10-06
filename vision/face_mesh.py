"""MediaPipe returns geometry. It does not classify drowsiness here."""
import cv2
import mediapipe as mp

from config import Settings


class FaceMesh:
    def __init__(self, settings: Settings):
        if not settings.model_path.is_file():
            raise FileNotFoundError(
                f"Thiếu model: {settings.model_path}. Chạy python scripts/download_model.py."
            )
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(settings.model_path)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=settings.detection_confidence,
            min_face_presence_confidence=settings.detection_confidence,
            min_tracking_confidence=settings.tracking_confidence,
        )
        self.landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)
        self.last_timestamp_ms = -1

    def detect(self, frame_bgr, elapsed_seconds: float):
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        # VIDEO requires strictly increasing timestamps, including very fast calls.
        timestamp_ms = max(self.last_timestamp_ms + 1, int(elapsed_seconds * 1000))
        self.last_timestamp_ms = timestamp_ms
        result = self.landmarker.detect_for_video(image, timestamp_ms)
        landmarks = result.face_landmarks[0] if result.face_landmarks else []
        return rgb, landmarks

    def close(self) -> None:
        self.landmarker.close()
