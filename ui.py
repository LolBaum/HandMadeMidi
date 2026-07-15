# ui.py
import cv2
import normalize
from presets import PRESETS
import config

# Global variables for button rectangles
button_rects_left = []
button_rects_right = []
mapper_rects = []   # (x1, y1, x2, y2, hand_id, feature)

# UI layout constants
RIGHT_PANEL_WIDTH = 320
BOTTOM_PANEL_HEIGHT = 140
BUTTON_ROW_HEIGHT = 60

def init_ui():
    global button_rects_left, button_rects_right, mapper_rects
    button_rects_left = []
    button_rects_right = []
    mapper_rects = []

def mouse_callback(event, x, y, flags, param):
    """Handle mouse clicks: mapper buttons first, then preset buttons."""
    if event != cv2.EVENT_LBUTTONDOWN:
        return

    # Unpack parameters
    hand_preset = param['hand_preset']
    hand_smoothed = param['hand_smoothed']
    midi_out = param['midi_out']
    mapper_mode = param['mapper_mode']

    # 1. Check Mapper Mode buttons (if active)
    if mapper_mode and mapper_rects:
        for (x1, y1, x2, y2, hand_id, feature) in mapper_rects:
            if x1 <= x <= x2 and y1 <= y <= y2:
                # Send current value or default 64
                value = 64
                if feature in hand_smoothed[hand_id] and hand_smoothed[hand_id][feature] is not None:
                    raw = hand_smoothed[hand_id][feature]
                    preset = PRESETS[hand_preset[hand_id]]
                    norm_range = preset.norm_ranges.get(feature)
                    if norm_range:
                        norm = normalize.normalize_value(raw, norm_range["min"], norm_range["max"])
                        value = normalize.midi_value(norm)
                # Get channel and CC from preset
                preset_idx = hand_preset[hand_id]
                if preset_idx == 0:
                    return
                preset = PRESETS[preset_idx]
                base_ch, cc = preset.midi_map[feature]
                hand_offset = config.LEFT_HAND_CHANNEL_OFFSET if hand_id == 0 else config.RIGHT_HAND_CHANNEL_OFFSET
                actual_ch = min(15, max(0, base_ch + hand_offset))
                midi_out.send_cc(actual_ch, cc, value)
                print(f"Mapper: hand{hand_id} {feature} -> ch{actual_ch+1} cc{cc} val{value}")
                return

    # 2. Fallback: preset buttons
    for (x1, y1, x2, y2, idx) in button_rects_left:
        if x1 <= x <= x2 and y1 <= y <= y2:
            # Switch left hand preset
            switch_preset_func = param['switch_preset']
            switch_preset_func(0, idx)
            return
    for (x1, y1, x2, y2, idx) in button_rects_right:
        if x1 <= x <= x2 and y1 <= y <= y2:
            switch_preset_func = param['switch_preset']
            switch_preset_func(1, idx)
            return

def draw_right_panel(canvas, x_offset, y_offset, panel_width, height,
                     hand_preset, hand_smoothed, midi_status):
    """
    Draw the value display panel on the right side of the canvas.
    midi_status is a string (e.g., "MIDI: Active" or "MIDI: Not connected").
    """
    # Background
    cv2.rectangle(canvas, (x_offset, y_offset), (x_offset + panel_width, y_offset + height),
                  (50, 50, 50), -1)

    # MIDI status at the top
    cv2.putText(canvas, midi_status, (x_offset + 10, y_offset + 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

    # ----- Left hand section -----
    header_y = y_offset + 50
    cv2.putText(canvas, "Left Hand", (x_offset + 10, header_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)

    y_pos = header_y + 25
    preset_idx = hand_preset[0]
    if preset_idx != 0:
        preset = PRESETS[preset_idx]
        for feature in preset.midi_map.keys():
            if feature in hand_smoothed[0] and hand_smoothed[0][feature] is not None:
                raw = hand_smoothed[0][feature]
                norm_range = preset.norm_ranges.get(feature)
                if norm_range is None:
                    continue
                norm = normalize.normalize_value(raw, norm_range["min"], norm_range["max"])
                midi_val = normalize.midi_value(norm)
                text = f"{feature}: {raw:.2f} -> {midi_val}"
                cv2.putText(canvas, text, (x_offset + 10, y_pos),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
                y_pos += 20
            else:
                # Feature not yet available – skip silently
                pass
        # If no values were drawn (e.g., all None), show a placeholder
        if y_pos == header_y + 25:
            cv2.putText(canvas, "(waiting for hand)", (x_offset + 10, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1)
    else:
        cv2.putText(canvas, "Off", (x_offset + 10, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)

    # ----- Right hand section (starts at half of the panel height) -----
    mid_y = y_offset + height // 2
    cv2.putText(canvas, "Right Hand", (x_offset + 10, mid_y + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)

    y_pos = mid_y + 45
    preset_idx = hand_preset[1]
    if preset_idx != 0:
        preset = PRESETS[preset_idx]
        for feature in preset.midi_map.keys():
            if feature in hand_smoothed[1] and hand_smoothed[1][feature] is not None:
                raw = hand_smoothed[1][feature]
                norm_range = preset.norm_ranges.get(feature)
                if norm_range is None:
                    continue
                norm = normalize.normalize_value(raw, norm_range["min"], norm_range["max"])
                midi_val = normalize.midi_value(norm)
                text = f"{feature}: {raw:.2f} -> {midi_val}"
                cv2.putText(canvas, text, (x_offset + 10, y_pos),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
                y_pos += 20
            else:
                pass
        if y_pos == mid_y + 45:
            cv2.putText(canvas, "(waiting for hand)", (x_offset + 10, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1)
    else:
        cv2.putText(canvas, "Off", (x_offset + 10, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)

def draw_bottom_panel(canvas, x_offset, y_offset, width, height, hand_preset):
    """Draw two rows of preset buttons at the bottom of the canvas."""
    global button_rects_left, button_rects_right
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

# ----------------------------------------------------------------------
def draw_mapper_overlay(canvas, w, h, hand_preset, hand_smoothed):
    """Draw overlay with clickable buttons for each feature of each hand."""
    global mapper_rects
    mapper_rects = []

    # Dim the background (camera feed area)
    overlay = canvas.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.4, canvas, 0.6, 0, canvas)

    # Title
    cv2.putText(canvas, "MIDI MAPPER MODE - Click a button to send MIDI", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

    # Layout: two columns (left hand, right hand)
    col_x_left = 50
    col_x_right = w // 2 + 50
    y_start = 80
    button_height = 40
    button_width = 220
    spacing = 10

    for hand_id, (label, col_x) in enumerate([("Left", col_x_left), ("Right", col_x_right)]):
        preset_idx = hand_preset[hand_id]
        if preset_idx == 0:
            continue
        preset = PRESETS[preset_idx]

        # Hand label
        cv2.putText(canvas, f"{label} Hand (Preset: {preset.name})", (col_x, y_start - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        y = y_start
        for feature in preset.midi_map.keys():
            base_ch, cc = preset.midi_map[feature]
            hand_offset = config.LEFT_HAND_CHANNEL_OFFSET if hand_id == 0 else config.RIGHT_HAND_CHANNEL_OFFSET
            actual_ch = min(15, max(0, base_ch + hand_offset))
            text = f"{feature} (ch{actual_ch + 1} cc{cc})"

            x1 = col_x
            x2 = x1 + button_width
            y1 = y
            y2 = y + button_height
            cv2.rectangle(canvas, (x1, y1), (x2, y2), (100, 100, 100), -1)
            cv2.rectangle(canvas, (x1, y1), (x2, y2), (255, 255, 255), 2)
            cv2.putText(canvas, text, (x1 + 10, y1 + 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            mapper_rects.append((x1, y1, x2, y2, hand_id, feature))
            y += button_height + spacing

    # Exit hint
    cv2.putText(canvas, "Press 'm' to exit Mapper Mode", (20, h - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
