import cv2
import numpy as np
from PIL import Image
from vision.aligned_crop import warp_aligned_crop

MOUTH_POINTS = (61, 146, 91, 181, 84, 17, 314, 405, 321, 375,
                291, 409, 270, 269, 267, 0, 37, 39, 40, 185)

def crop_mouth_rgb(rgb, landmarks, size=(96, 96)):
    # Input must be RGB. Landmarks use normalized MediaPipe coordinates.
    height, width = rgb.shape[:2]
    if len(landmarks) <= max(MOUTH_POINTS):
        raise ValueError('Not enough face landmarks')
    points = np.array([(landmarks[i].x * width, landmarks[i].y * height)
                       for i in MOUTH_POINTS], dtype=np.float32)
    corners = np.array([(landmarks[i].x * width, landmarks[i].y * height)
                        for i in (61, 291)], dtype=np.float32)
    # Sort by image x so the alignment does not rotate the mouth 180 degrees.
    corners = corners[np.argsort(corners[:, 0])]
    delta = corners[1] - corners[0]
    distance = float(np.linalg.norm(delta))
    if distance < 8 or not np.isfinite(points).all():
        raise ValueError('Mouth too small or invalid')
    angle = float(np.degrees(np.arctan2(delta[1], delta[0])))
    matrix = cv2.getRotationMatrix2D(tuple(corners.mean(axis=0).tolist()), angle, 1.0)
    transformed = cv2.transform(points[None, :, :], matrix)[0]
    low, high = transformed.min(axis=0), transformed.max(axis=0)
    center = (low + high) / 2
    side = max(1.6 * distance, float(max(high - low)) + 0.5 * distance)
    x0, y0 = np.floor(center - side / 2).astype(int)
    x1, y1 = np.ceil(center + side / 2).astype(int)
    if x0 < 0 or y0 < 0 or x1 > width or y1 > height:
        raise ValueError('Mouth crop outside image')
    # Reject crops whose corners would sample beyond the rotated original image.
    inverse = cv2.invertAffineTransform(matrix)
    box = np.array([[[x0, y0], [x1 - 1, y0], [x1 - 1, y1 - 1], [x0, y1 - 1]]], dtype=np.float32)
    original_box = cv2.transform(box, inverse)[0]
    if (original_box[:, 0] < 0).any() or (original_box[:, 0] >= width).any() or \
       (original_box[:, 1] < 0).any() or (original_box[:, 1] >= height).any():
        raise ValueError('Aligned crop outside original image')
    crop = warp_aligned_crop(rgb, matrix, (x0, y0, x1, y1))
    if crop.size == 0:
        raise ValueError('Empty mouth crop')
    return np.asarray(Image.fromarray(crop).resize(size, Image.Resampling.BICUBIC), dtype=np.uint8)
