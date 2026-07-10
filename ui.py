# ui.py
import cv2
import normalize
from presets import PRESETS

# Global variables for button rectangles (will be updated by draw functions)
button_rects_left = []
button_rects_right = []

# UI layout constants (can be adjusted)
RIGHT_PANEL_WIDTH = 300
BOTTOM_PANEL_HEIGHT = 140
BUTTON_ROW_HEIGHT = 60
LEFT_MARGIN = 10
TOP_MARGIN = 10

def init_ui():
    """Initialize any UI-related globals."""
    global button_rects_left, button_rects_right
    button_rects_left = []
    button_rects_right = []

def mouse_callback(event, x, y, flags, param):
    """Global mouse callback – switches presets when clicking a button."""
    if event == cv2.EVENT_LBUTTONDOWN:
        # Get the hand preset arrays from the main module (passed as param)
        hand_preset = param['hand_preset']
        switch_preset_func = param['switch_preset']

        # Check left hand buttons (upper row)
        for (x1, y1, x2, y2, idx) in button_rects_left:
            if x1 <= x <= x2 and y1 <= y <= y2:
                switch_preset_func(0, idx)
                return
        # Check right hand buttons (lower row)
        for (x1, y1, x2, y2, idx) in button_rects_right:
            if x1 <= x <= x2 and y1 <= y <= y2:
                switch_preset_func(1, idx)
                return

def draw_right_panel(canvas, x_offset, y_offset, panel_width, height, hand_preset, hand_smoothed):
    """Draw the value display panel on the right side of the canvas."""
    # Background
    cv2.rectangle(canvas, (x_offset, y_offset), (x_offset + panel_width, y_offset + height),
                  (50, 50, 50), -1)
    # Headers
    cv2.putText(canvas, "Left Hand", (x_offset + 10, y_offset + 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
    cv2.putText(canvas, "Right Hand", (x_offset + 10, y_offset + height//2 + 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)

    # Display values for left hand (index 0)
    y_pos = y_offset + 60
    preset_idx = hand_preset[0]
    if preset_idx != 0:
        preset = PRESETS[preset_idx]
        for feature in preset.midi_map.keys():
            if feature in hand_smoothed[0] and hand_smoothed[0][feature] is not None:
                raw = hand_smoothed[0][feature]
                norm_range = preset.norm_ranges.get(feature)
                if norm_range:
                    norm = normalize.normalize_value(raw, norm_range["min"], norm_range["max"])
                    midi = normalize.midi_value(norm)
                else:
                    norm = 0.0
                    midi = 0
                text = f"{feature}: {raw:.2f} → {norm:.2f} → {midi}"
                cv2.putText(canvas, text, (x_offset + 10, y_pos),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                y_pos += 22
    else:
        cv2.putText(canvas, "Off", (x_offset + 10, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)

    # Display values for right hand (index 1)
    y_pos = y_offset + height//2 + 60
    preset_idx = hand_preset[1]
    if preset_idx != 0:
        preset = PRESETS[preset_idx]
        for feature in preset.midi_map.keys():
            if feature in hand_smoothed[1] and hand_smoothed[1][feature] is not None:
                raw = hand_smoothed[1][feature]
                norm_range = preset.norm_ranges.get(feature)
                if norm_range:
                    norm = normalize.normalize_value(raw, norm_range["min"], norm_range["max"])
                    midi = normalize.midi_value(norm)
                else:
                    norm = 0.0
                    midi = 0
                text = f"{feature}: {raw:.2f} → {norm:.2f} → {midi}"
                cv2.putText(canvas, text, (x_offset + 10, y_pos),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                y_pos += 22
    else:
        cv2.putText(canvas, "Off", (x_offset + 10, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)

def draw_bottom_panel(canvas, x_offset, y_offset, width, height, hand_preset):
    """Draw two rows of preset buttons at the bottom of the canvas."""
    global button_rects_left, button_rects_right
    # We don't clear the lists, we rebuild them in place
    button_rects_left = []
    button_rects_right = []

    num_presets = len(PRESETS)
    margin = 10
    available_width = width - 2 * margin
    button_width = available_width // num_presets
    x_start = x_offset + margin

    # Row 1: Left hand (top half)
    row_y1 = y_offset
    row_y2 = y_offset + height // 2
    for i in range(num_presets):
        x1 = x_start + i * button_width
        x2 = x1 + button_width
        color = (0, 255, 0) if hand_preset[0] == i else (100, 100, 100)
        cv2.rectangle(canvas, (x1, row_y1), (x2, row_y2), color, -1)
        cv2.rectangle(canvas, (x1, row_y1), (x2, row_y2), (0, 0, 0), 2)
        text = f"{i}: {PRESETS[i].name}"
        if len(text) > 12:
            text = text[:10] + ".."
        font = cv2.FONT_HERSHEY_SIMPLEX
        (tw, th), _ = cv2.getTextSize(text, font, 0.5, 1)
        tx = x1 + (button_width - tw) // 2
        ty = row_y1 + (row_y2 - row_y1 + th) // 2 - 3
        cv2.putText(canvas, text, (tx, ty), font, 0.5, (0, 0, 0), 1)
        button_rects_left.append((x1, row_y1, x2, row_y2, i))

    # Row 2: Right hand (bottom half)
    row_y1 = y_offset + height // 2
    row_y2 = y_offset + height
    for i in range(num_presets):
        x1 = x_start + i * button_width
        x2 = x1 + button_width
        color = (0, 255, 0) if hand_preset[1] == i else (100, 100, 100)
        cv2.rectangle(canvas, (x1, row_y1), (x2, row_y2), color, -1)
        cv2.rectangle(canvas, (x1, row_y1), (x2, row_y2), (0, 0, 0), 2)
        text = f"{i}: {PRESETS[i].name}"
        if len(text) > 12:
            text = text[:10] + ".."
        font = cv2.FONT_HERSHEY_SIMPLEX
        (tw, th), _ = cv2.getTextSize(text, font, 0.5, 1)
        tx = x1 + (button_width - tw) // 2
        ty = row_y1 + (row_y2 - row_y1 + th) // 2 - 3
        cv2.putText(canvas, text, (tx, ty), font, 0.5, (0, 0, 0), 1)
        button_rects_right.append((x1, row_y1, x2, row_y2, i))

    # Labels for the rows
    cv2.putText(canvas, "Left hand", (x_offset + 10, y_offset - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    cv2.putText(canvas, "Right hand", (x_offset + 10, y_offset + height//2 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)