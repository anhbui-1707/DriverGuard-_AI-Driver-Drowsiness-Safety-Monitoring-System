"""Avoid CPU thread oversubscription when MediaPipe and two models share a laptop."""
import logging


def configure_tensorflow(tf, settings):
    try:
        tf.config.threading.set_intra_op_parallelism_threads(settings.inference_cpu_threads)
        tf.config.threading.set_inter_op_parallelism_threads(1)
    except RuntimeError:
        logging.getLogger(__name__).info("TensorFlow already initialized; keeping its thread settings")
