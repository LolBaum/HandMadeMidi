# layout.py
import cv2
import numpy as np
from ui import UIRenderer  # we need the constants for panel sizes, or we can duplicate them

def build_canvas(frame, window_name):
    """
    Create the full composited canvas:
    - Resize the camera frame to fit the available space.
    - Apply a dark background with the frame centered.
    Returns the canvas (numpy array) ready for UI overlay.
    """
    h, w = frame.shape[:2]
    try:
        rect = cv2.getWindowImageRect(window_name)
        win_w, win_h = rect[2], rect[3]
    except cv2.error as e:
        win_w, win_h = 1280, 720
        print('error', e, f'defaulting to fallback: ({win_w}, {win_h})')
    win_w = max(win_w, 600)
    win_h = max(win_h, 400)

    # Use UI constants for panel sizes (could also be passed as params)
    right_panel_w = max(UIRenderer.MIN_RIGHT_PANEL_WIDTH,
                        int(win_w * UIRenderer.RIGHT_PANEL_RATIO))
    bottom_panel_h = max(UIRenderer.MIN_BOTTOM_PANEL_HEIGHT,
                         int(win_h * UIRenderer.BOTTOM_PANEL_RATIO))
    camera_w = win_w - right_panel_w
    camera_h = win_h - bottom_panel_h

    # Resize frame to fit camera area while preserving aspect ratio
    aspect = w / h
    if camera_w / camera_h > aspect:
        new_h = camera_h
        new_w = int(new_h * aspect)
    else:
        new_w = camera_w
        new_h = int(new_w / aspect)
    x_offset = (camera_w - new_w) // 2
    y_offset = (camera_h - new_h) // 2
    frame_resized = cv2.resize(frame, (new_w, new_h))

    # Build canvas with dark background
    canvas = np.full((win_h, win_w, 3), 30, dtype=np.uint8)
    canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = frame_resized

    return canvas