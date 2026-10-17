"""Float32 inference for the same V2 weights, crop and internal normalization."""
import numpy as np


class LiteYawnModel:
    def __init__(self, path, threads=1, interpreter_factory=None):
        if interpreter_factory is None:
            import tensorflow as tf
            interpreter_factory = tf.lite.Interpreter
        self.interpreter = interpreter_factory(model_path=str(path), num_threads=threads)
        self.interpreter.allocate_tensors()
        inputs = self.interpreter.get_input_details()
        outputs = self.interpreter.get_output_details()
        if len(inputs) != 1 or len(outputs) != 1:
            raise ValueError("Model ngáp TFLite phải có một đầu vào và một đầu ra")
        self.input = inputs[0]
        self.output = outputs[0]
        if tuple(self.input['shape']) != (1, 96, 96, 3) or self.input['dtype'] != np.float32:
            raise ValueError("Model ngáp TFLite phải nhận float32 RGB 1x96x96x3")
        if tuple(self.output['shape']) != (1, 1) or self.output['dtype'] != np.float32:
            raise ValueError("Model ngáp TFLite phải xuất một score float32")
        self(np.zeros((1, 96, 96, 3), dtype=np.uint8))

    def __call__(self, batch, training=False):
        if training:
            raise ValueError("TFLite chỉ dùng suy luận")
        batch = np.asarray(batch)
        if batch.shape != (1, 96, 96, 3):
            raise ValueError("Sai kích thước ảnh miệng")
        # No divide by 255: original V2 contains Rescaling(1/127.5, offset=-1).
        self.interpreter.set_tensor(self.input['index'], batch.astype(np.float32))
        self.interpreter.invoke()
        return self.interpreter.get_tensor(self.output['index'])
