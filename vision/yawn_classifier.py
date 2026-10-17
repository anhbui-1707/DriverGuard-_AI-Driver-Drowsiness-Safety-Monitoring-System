"""MobileNetV2 mouth classification; normalization is inside the model."""
from dataclasses import replace
import cv2
import numpy as np
from config import SETTINGS
from vision.mouth_crop import crop_mouth_rgb


class YawnClassifier:
    def __init__(self, settings=SETTINGS, model=None):
        self.backend = "INJECTED"
        if model is None:
            lite_path = settings.yawn_model_path.with_name(settings.yawn_model_path.stem + "_float32.tflite")
            if lite_path.is_file():
                from vision.lite_yawn import LiteYawnModel
                model = LiteYawnModel(lite_path, threads=settings.yawn_lite_threads)
                self.backend = "TFLITE_FLOAT32"
        if model is None:
            self.backend = "KERAS_GRAPH"
            if not settings.yawn_model_path.is_file():
                raise FileNotFoundError(f"Thiếu model ngáp: {settings.yawn_model_path}")
            import tensorflow as tf
            from vision.model_runtime import configure_tensorflow
            configure_tensorflow(tf, settings)
            model = tf.keras.models.load_model(settings.yawn_model_path, compile=False)
            if tuple(model.input_shape[1:]) != (96, 96, 3) or tuple(model.output_shape[1:]) != (1,):
                raise ValueError("Model ngáp phải nhận RGB 96x96 và xuất một score")
            # Compile inference once: avoid dispatching each MobileNet layer in Python per frame.
            raw_model = model
            @tf.function(input_signature=[tf.TensorSpec((1, 96, 96, 3), tf.uint8)])
            def infer(batch):
                return raw_model(batch, training=False)
            infer(tf.zeros((1, 96, 96, 3), dtype=tf.uint8))
            model = lambda batch, training=False: infer(tf.convert_to_tensor(batch, dtype=tf.uint8))
        self.model = model
        self.settings = settings
        self.last_inference = None
        self.last_result = None

    def update(self, rgb, landmarks, timer, now):
        if not landmarks:
            self.last_inference = None
            self.last_result = None
            return timer.update_score(None, now)
        try:
            crop = crop_mouth_rgb(rgb, landmarks)
        except (ValueError, cv2.error):
            self.last_inference = None
            self.last_result = None
            return timer.update_score(None, now)
        if (self.last_inference is not None and self.last_result is not None
                and 0 <= now - self.last_inference < self.settings.yawn_inference_interval_seconds):
            # Reuse display only. Never add timer time or repeat an event on cached frames.
            return replace(self.last_result, event=False)
        score = float(np.asarray(self.model(crop[None], training=False)).reshape(-1)[0])
        self.last_inference = now
        self.last_result = timer.update_score(score, now)
        return self.last_result
