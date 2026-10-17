"""Warp only a requested rectangle in the aligned coordinate system."""
import cv2


def warp_aligned_crop(image, matrix, box, interpolation=cv2.INTER_LINEAR):
    x0, y0, x1, y1 = box
    local = matrix.copy()
    # Translate the aligned image origin to the crop's top-left corner.
    local[0, 2] -= x0
    local[1, 2] -= y0
    return cv2.warpAffine(image, local, (int(x1-x0), int(y1-y0)),
                          flags=interpolation, borderMode=cv2.BORDER_CONSTANT)
