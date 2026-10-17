"""CEW eye classifier. Crop contract matches the final Colab test cell."""
import logging
import cv2
import numpy as np
from PIL import Image
from vision.aligned_crop import warp_aligned_crop
from config import SETTINGS
from vision.eye_tracker import EyeState

logger = logging.getLogger(__name__)
LEFT_CONTOUR = (33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246)
RIGHT_CONTOUR = (362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398)


def prepare_eye_image(rgb, landmarks):
    """Rotate by eye-center roll, retain both contours and CEW-sized padding."""
    height, width = rgb.shape[:2]
    if len(landmarks) <= max(LEFT_CONTOUR + RIGHT_CONTOUR):
        raise ValueError("Không đủ điểm mắt.")
    points = np.array([[p.x*width, p.y*height] for p in landmarks], dtype=np.float32)
    if not np.isfinite(points).all():
        raise ValueError("Tọa độ mắt không hợp lệ.")
    left, right = sorted([(points[33]+points[133])/2,
                          (points[362]+points[263])/2], key=lambda p: p[0])
    distance = float(np.linalg.norm(right-left))
    if distance < 10:
        raise ValueError("Mặt quá nhỏ; hãy đến gần camera.")
    angle = float(np.degrees(np.arctan2(right[1]-left[1], right[0]-left[0])))
    center = (left+right)/2
    rotation = cv2.getRotationMatrix2D(tuple(map(float, center)), angle, 1.0)
    contour = cv2.transform(points[list(LEFT_CONTOUR+RIGHT_CONTOUR)][None, ...], rotation)[0]
    low, high = contour.min(axis=0), contour.max(axis=0)
    padding = .10*distance
    x1 = int(np.floor(min(center[0]-.95*distance, low[0]-padding)))
    x2 = int(np.ceil(max(center[0]+.95*distance, high[0]+padding)))
    y1 = int(np.floor(min(center[1]-.35*distance, low[1]-padding)))
    y2 = int(np.ceil(max(center[1]+.35*distance, high[1]+padding)))
    if x1 < 0 or y1 < 0 or x2 > width or y2 > height or x2 <= x1 or y2 <= y1:
        raise ValueError("Mắt sát mép ảnh; hãy đưa mặt vào giữa camera.")
    box = (x1, y1, x2, y2)
    valid = warp_aligned_crop(np.full((height, width), 255, dtype=np.uint8),
                              rotation, box, cv2.INTER_NEAREST)
    if not np.all(valid == 255):
        raise ValueError("Khung mắt vượt vùng ảnh thật sau khi xoay.")
    crop = warp_aligned_crop(rgb, rotation, box)
    # RGB uint8 0–255: the model already contains Rescaling(1/255).
    return np.asarray(Image.fromarray(crop).resize((128, 48)), dtype=np.uint8)


class EyeClassifier:
    def __init__(self, settings=SETTINGS, model=None):
        self.settings = settings
        self.backend = "INJECTED"
        if model is None:
            lite_path = settings.eye_model_path.with_name(settings.eye_model_path.stem + "_float32.tflite")
            if lite_path.is_file():
                from vision.lite_eye import LiteEyeModel
                model = LiteEyeModel(lite_path, threads=settings.eye_lite_threads)
                self.backend = "TFLITE_FLOAT32"
        if model is None:
            self.backend = "KERAS_GRAPH"
            if not settings.eye_model_path.is_file():
                raise FileNotFoundError(f"Thiếu model mắt: {settings.eye_model_path}")
            try:
                import tensorflow as tf
                from vision.model_runtime import configure_tensorflow
                configure_tensorflow(tf, settings)
                model = tf.keras.models.load_model(settings.eye_model_path, compile=False)
                if tuple(model.input_shape[1:]) != (48, 128, 3) or tuple(model.output_shape[1:]) != (1,):
                    raise ValueError("Model phải nhận RGB 48×128 và xuất một Open score.")
                # Warm up outside the monitoring loop; no predict() dataset overhead.
                raw_model = model
                @tf.function(input_signature=[tf.TensorSpec((1, 48, 128, 3), tf.uint8)])
                def infer(batch):
                    return raw_model(batch, training=False)
                infer(tf.zeros((1, 48, 128, 3), dtype=tf.uint8))
                model = lambda batch, training=False: infer(tf.convert_to_tensor(batch, dtype=tf.uint8))
            except (ImportError, ValueError, OSError) as exc:
                raise RuntimeError(f"Không nạp được model mắt. Chạy START_DRIVERGUARD.bat. Chi tiết: {exc}") from exc
        self.model = model

    def update(self, rgb, landmarks, timer, now):
        if not landmarks:
            return timer.update_state(EyeState.UNKNOWN, now)
        try:
            crop = prepare_eye_image(rgb, landmarks)
        except (ValueError, cv2.error) as exc:
            return timer.update_state(EyeState.UNKNOWN, now, model_message=str(exc))
        # Runtime failures propagate to the existing worker error handler, never become SAFE.
        score = float(np.asarray(self.model(crop[None, ...], training=False)).reshape(-1)[0])
        if not np.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("Model mắt trả về Open score không hợp lệ.")
        return timer.update_score(score, now)
