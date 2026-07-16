# ui.py
import cv2
import normalize
from presets import PRESETS
import config

# Global variables for button rectangles (updated each frame)
button_rects_left = []
button_rects_right = []
mapper_rects = []
topmost_button_rect = None

# Layout ratios (fractions of window size)
RIGHT_PANEL_RATIO = 0.25          # width ratio
BOTTOM_PANEL_RATIO = 0.15         # height ratio
MIN_RIGHT_PANEL_WIDTH = 250
MIN_BOTTOM_PANEL_HEIGHT = 120
BUTTON_ROW_RATIO = 0.5            # each row takes half of bottom panel

# Always‑on‑top state
always_on_top = False

def init_ui():
    """Reset UI globals."""
    global button_rects_left, button_rects_right, mapper_rects, topmost_button_rect
    button_rects_left = []
    button_rects_right = []
    mapper_rects = []
    topmost_button_rect = None

def set_window_topmost(window_name, state):
    try:
        cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1 if state else 0)
    except Exception:
        pass

def toggle_topmost(window_name):
    global always_on_top
    always_on_top = not always_on_top
    set_window_topmost(window_name, always_on_top)

def mouse_callback(event, x, y, flags, param):
    if event != cv2.EVENT_LBUTTONDOWN:
        return

    hand_preset = param['hand_preset']
    hand_smoothed = param['hand_smoothed']
    midi_out = param['midi_out']
    mapper_mode = param['mapper_mode']
    window_name = param['window_name']

    # 1. Topmost button
    global topmost_button_rect
    if topmost_button_rect:
        x1, y1, x2, y2 = topmost_button_rect
        if x1 <= x <= x2 and y1 <= y <= y2:
            toggle_topmost(window_name)
            return

    # 2. Mapper buttons
    if mapper_mode and mapper_rects:
        for (x1, y1, x2, y2, hand_id, feature) in mapper_rects:
            if x1 <= x <= x2 and y1 <= y <= y2:
                value = 64
                if feature in hand_smoothed[hand_id] and hand_smoothed[hand_id][feature] is not None:
                    raw = hand_smoothed[hand_id][feature]
                    preset = PRESETS[hand_preset[hand_id]]
                    norm_range = preset.norm_ranges.get(feature)
                    if norm_range:
                        norm = normalize.normalize_value(raw, norm_range["min"], norm_range["max"])
                        value = normalize.midi_value(norm)
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

    # 3. Preset buttons
    for (x1, y1, x2, y2, idx) in button_rects_left:
        if x1 <= x <= x2 and y1 <= y <= y2:
            param['switch_preset'](0, idx)
            return
    for (x1, y1, x2, y2, idx) in button_rects_right:
        if x1 <= x <= x2 and y1 <= y <= y2:
            param['switch_preset'](1, idx)
            return

# ----------------------------------------------------------------------
def _draw_hand_values(canvas, x_offset, y_offset, hand_id, hand_preset,
                       hand_smoothed, font_scale, note_state):
    """
    Draw value lines for one hand (hand_id = 0 or 1).
    Returns the next Y position after drawing.
    """
    preset_idx = hand_preset[hand_id]
    if preset_idx == 0:
        cv2.putText(canvas, "Off", (x_offset + 10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (100, 100, 100), 1)
        return y_offset + int(25 * font_scale * 2)

    preset = PRESETS[preset_idx]
    y_pos = y_offset
    anything_drawn = False

    # Helper to get normalized value
    def get_norm(feature):
        if feature in hand_smoothed[hand_id] and hand_smoothed[hand_id][feature] is not None:
            rng = preset.norm_ranges.get(feature)
            if rng:
                return normalize.normalize_value(hand_smoothed[hand_id][feature],
                                                 rng["min"], rng["max"])
        return None

    # 1. Show mapped CC values (for non-note presets)
    for feature in preset.midi_map.keys():
        if feature in hand_smoothed[hand_id] and hand_smoothed[hand_id][feature] is not None:
            raw = hand_smoothed[hand_id][feature]
            norm = get_norm(feature)
            if norm is None:
                continue
            midi_val = normalize.midi_value(norm)
            text = f"{feature}: {raw:.2f} -> {midi_val}"
            cv2.putText(canvas, text, (x_offset + 10, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, font_scale, (200, 200, 200), 1)
            y_pos += int(20 * font_scale * 2)
            anything_drawn = True

    # 2. Additional info for note presets
    if preset.note_config is not None:
        # palm_x → pitch bend
        norm_x = get_norm('palm_x')
        if norm_x is not None:
            bend = int(round((norm_x - 0.5) * 16384))
            bend = max(-8192, min(8191, bend))
            text = f"palm_x: {hand_smoothed[hand_id]['palm_x']:.2f} -> bend={bend}"
            cv2.putText(canvas, text, (x_offset + 10, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, font_scale, (200, 200, 200), 1)
            y_pos += int(20 * font_scale * 2)
            anything_drawn = True

        # palm_y → note (inverted)
        norm_y = get_norm('palm_y')
        if norm_y is not None:
            note_min = preset.note_config['note_min']
            note_max = preset.note_config['note_max']
            note = int(round((1 - norm_y) * (note_max - note_min) + note_min))
            note = max(0, min(127, note))
            text = f"palm_y: {hand_smoothed[hand_id]['palm_y']:.2f} -> note={note}"
            cv2.putText(canvas, text, (x_offset + 10, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, font_scale, (200, 200, 200), 1)
            y_pos += int(20 * font_scale * 2)
            anything_drawn = True

        # thumb_index_dist → gate
        if 'thumb_index_dist' in hand_smoothed[hand_id] and hand_smoothed[hand_id]['thumb_index_dist'] is not None:
            raw_dist = hand_smoothed[hand_id]['thumb_index_dist']
            norm_dist = get_norm('thumb_index_dist')
            if norm_dist is not None:
                threshold = preset.note_config['threshold']
                status = "ON" if raw_dist < threshold else "OFF"
                text = f"spread: {raw_dist:.2f} -> {status} (thr={threshold:.2f})"
                cv2.putText(canvas, text, (x_offset + 10, y_pos),
                            cv2.FONT_HERSHEY_SIMPLEX, font_scale, (200, 200, 200), 1)
                y_pos += int(20 * font_scale * 2)
                anything_drawn = True

        # Note state (ON/OFF) and current bend value
        if note_state is not None and len(note_state) > hand_id:
            state = note_state[hand_id]
            if state['active']:
                # Get current note and bend (recompute from smoothed)
                norm_x_now = get_norm('palm_x')
                bend_now = int(round((norm_x_now - 0.5) * 16384)) if norm_x_now is not None else 0
                bend_now = max(-8192, min(8191, bend_now))
                note_now = state['note'] if state['note'] is not None else '?'
                text = f"Note ON  note={note_now}  bend={bend_now}"
                cv2.putText(canvas, text, (x_offset + 10, y_pos),
                            cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), 1)
            else:
                text = "Note OFF"
                cv2.putText(canvas, text, (x_offset + 10, y_pos),
                            cv2.FONT_HERSHEY_SIMPLEX, font_scale, (100, 100, 100), 1)
            y_pos += int(20 * font_scale * 2)
            anything_drawn = True

    if not anything_drawn:
        cv2.putText(canvas, "(waiting for hand)", (x_offset + 10, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (150, 150, 150), 1)
        y_pos += int(25 * font_scale * 2)

    return y_pos


def draw_right_panel(canvas, x_offset, y_offset, panel_width, height,
                     hand_preset, hand_smoothed, midi_status, font_scale=0.5,
                     note_state=None):
    """Draw the value panel with dynamic sizes, and optional note info."""
    global topmost_button_rect, always_on_top

    # Background
    cv2.rectangle(canvas, (x_offset, y_offset), (x_offset + panel_width, y_offset + height),
                  (50, 50, 50), -1)

    # MIDI status
    cv2.putText(canvas, midi_status, (x_offset + 10, y_offset + 25),
                cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 0), 1)

    # Topmost toggle button (top‑right corner)
    btn_size = int(panel_width * 0.1)   # 10% of panel width
    btn_size = max(20, min(40, btn_size))  # clamp
    btn_x = x_offset + panel_width - btn_size - 10
    btn_y = y_offset + 10
    color = (0, 255, 0) if always_on_top else (100, 100, 100)
    cv2.circle(canvas, (btn_x + btn_size//2, btn_y + btn_size//2), btn_size//2 - 2, color, -1)
    cv2.circle(canvas, (btn_x + btn_size//2, btn_y + btn_size//2), btn_size//2 - 2, (255, 255, 255), 1)
    # Simple lock icon
    if always_on_top:
        cv2.line(canvas, (btn_x + btn_size//2, btn_y + 8), (btn_x + btn_size//2, btn_y + btn_size//2), (255,255,255), 2)
        cv2.circle(canvas, (btn_x + btn_size//2, btn_y + btn_size//2 + 4), 3, (255,255,255), -1)
    else:
        cv2.line(canvas, (btn_x + btn_size//2, btn_y + btn_size//2 - 2), (btn_x + btn_size//2, btn_y + btn_size//2 + 6), (255,255,255), 2)
        cv2.circle(canvas, (btn_x + btn_size//2, btn_y + btn_size//2 + 8), 3, (255,255,255), -1)
    topmost_button_rect = (btn_x, btn_y, btn_x + btn_size, btn_y + btn_size)

    # ---- Left hand values ----
    header_y = y_offset + 50
    cv2.putText(canvas, "Left Hand", (x_offset + 10, header_y),
                cv2.FONT_HERSHEY_SIMPLEX, font_scale * 1.2, (0, 255, 255), 1)
    next_y = _draw_hand_values(canvas, x_offset, header_y + 25, 0,
                               hand_preset, hand_smoothed, font_scale, note_state)

    # ---- Right hand values (bottom half) ----
    mid_y = y_offset + height // 2
    cv2.putText(canvas, "Right Hand", (x_offset + 10, mid_y + 20),
                cv2.FONT_HERSHEY_SIMPLEX, font_scale * 1.2, (0, 255, 255), 1)
    _draw_hand_values(canvas, x_offset, mid_y + 45, 1,
                      hand_preset, hand_smoothed, font_scale, note_state)

# ----------------------------------------------------------------------
def draw_bottom_panel(canvas, x_offset, y_offset, width, height, hand_preset, font_scale=0.5):
    """Draw preset buttons scaled to fit the bottom panel."""
    global button_rects_left, button_rects_right
    button_rects_left = []
    button_rects_right = []

    num_presets = len(PRESETS)
    margin = int(10 * font_scale * 2)
    available_width = width - 2 * margin
    button_width = available_width // num_presets
    x_start = x_offset + margin

    # Row 1: Left hand
    row_height = height // 2
    row_y1 = y_offset
    row_y2 = y_offset + row_height
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
        fs = font_scale * 1.2
        (tw, th), _ = cv2.getTextSize(text, font, fs, 1)
        tx = x1 + (button_width - tw) // 2
        ty = row_y1 + (row_height + th) // 2 - 3
        cv2.putText(canvas, text, (tx, ty), font, fs, (0, 0, 0), 1)
        button_rects_left.append((x1, row_y1, x2, row_y2, i))

    # Row 2: Right hand
    row_y1 = y_offset + row_height
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
        fs = font_scale * 1.2
        (tw, th), _ = cv2.getTextSize(text, font, fs, 1)
        tx = x1 + (button_width - tw) // 2
        ty = row_y1 + (row_height + th) // 2 - 3
        cv2.putText(canvas, text, (tx, ty), font, fs, (0, 0, 0), 1)
        button_rects_right.append((x1, row_y1, x2, row_y2, i))

    # Row labels
    cv2.putText(canvas, "Left hand", (x_offset + 10, y_offset - 5),
                cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 255), 1)
    cv2.putText(canvas, "Right hand", (x_offset + 10, y_offset + row_height - 5),
                cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 255), 1)

# ----------------------------------------------------------------------
def draw_mapper_overlay(canvas, w, h, hand_preset, hand_smoothed, font_scale=0.6):
    """Draw mapper overlay with dynamically scaled buttons."""
    global mapper_rects
    mapper_rects = []

    # Dim background
    overlay = canvas.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.4, canvas, 0.6, 0, canvas)

    # Title
    cv2.putText(canvas, "MIDI MAPPER MODE - Click a button to send MIDI", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, font_scale * 1.2, (0, 255, 255), 2)

    # Columns
    margin = 30
    col_width = (w - 3 * margin) // 2
    col_x_left = margin
    col_x_right = margin + col_width + margin
    y_start = 80
    button_height = int(40 * font_scale * 1.5)
    spacing = int(10 * font_scale * 1.5)

    for hand_id, (label, col_x) in enumerate([("Left", col_x_left), ("Right", col_x_right)]):
        preset_idx = hand_preset[hand_id]
        if preset_idx == 0:
            continue
        preset = PRESETS[preset_idx]

        cv2.putText(canvas, f"{label} Hand (Preset: {preset.name})", (col_x, y_start - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 255), 1)

        y = y_start
        for feature in preset.midi_map.keys():
            base_ch, cc = preset.midi_map[feature]
            hand_offset = config.LEFT_HAND_CHANNEL_OFFSET if hand_id == 0 else config.RIGHT_HAND_CHANNEL_OFFSET
            actual_ch = min(15, max(0, base_ch + hand_offset))
            text = f"{feature} (ch{actual_ch+1} cc{cc})"

            x1 = col_x
            x2 = x1 + col_width
            y1 = y
            y2 = y + button_height
            cv2.rectangle(canvas, (x1, y1), (x2, y2), (100, 100, 100), -1)
            cv2.rectangle(canvas, (x1, y1), (x2, y2), (255, 255, 255), 2)
            cv2.putText(canvas, text, (x1 + 10, y1 + button_height//2 + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 1)
            mapper_rects.append((x1, y1, x2, y2, hand_id, feature))
            y += button_height + spacing

    # Exit hint
    cv2.putText(canvas, "Press 'm' to exit Mapper Mode", (20, h - 20),
                cv2.FONT_HERSHEY_SIMPLEX, font_scale, (200, 200, 200), 1)