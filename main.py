# main.py
import cv2
import numpy as np
from vision import Vision
from landmarks import LandmarkExtractor
from hand_features import HandFeatures
from filters import OneEuroFilter
from midi_output import MidiOutput
from presets import PRESETS
import normalize
import config

# ----------------------------------------------------------------------
# Global state for two hands
# Each hand is identified by index: 0 = left, 1 = right
# We'll store per‑hand preset index, filters, smoothed values, and MIDI cache.
hand_preset = [0, 0]          # start with Off for both
hand_filters = [{}, {}]       # filters for each hand
hand_smoothed = [{}, {}]      # last smoothed raw values
hand_last_midi = [{}, {}]     # last MIDI values for deadband

midi_out = None

def init_hand(hand_id):
    """(Re‑)initialize filters and caches for a hand based on its current preset."""
    preset_idx = hand_preset[hand_id]
    preset = PRESETS[preset_idx]
    # Create new filter instances for each feature in the preset
    new_filters = {}
    for feature, settings in preset.filter_settings.items():
        new_filters[feature] = OneEuroFilter(
            min_cutoff=settings["min_cutoff"] * config.GLOBAL_CUTOFF_MULTIPLIER,
            beta=settings["beta"] * config.GLOBAL_BETA_MULTIPLIER
        )
    hand_filters[hand_id] = new_filters
    # Reset smoothed values to None (will be set on first update)
    hand_smoothed[hand_id] = {feature: None for feature in preset.filter_settings.keys()}
    # Reset MIDI deadband cache
    hand_last_midi[hand_id] = {feature: -1 for feature in preset.midi_map.keys()}

def switch_preset(hand_id, preset_idx):
    """Change preset for a specific hand and re‑initialise its state."""
    if preset_idx < 0 or preset_idx >= len(PRESETS):
        return
    hand_preset[hand_id] = preset_idx
    init_hand(hand_id)
    # Optionally send current values immediately? We'll let the next frame handle it.

# ----------------------------------------------------------------------
# UI button handling
button_rects_left = []   # (x1, y1, x2, y2, preset_idx)
button_rects_right = []

def mouse_callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        # Check left hand buttons (upper row)
        for (x1, y1, x2, y2, idx) in button_rects_left:
            if x1 <= x <= x2 and y1 <= y <= y2:
                switch_preset(0, idx)
                return
        # Check right hand buttons (lower row)
        for (x1, y1, x2, y2, idx) in button_rects_right:
            if x1 <= x <= x2 and y1 <= y <= y2:
                switch_preset(1, idx)
                return

# ----------------------------------------------------------------------
def main():
    global midi_out, hand_preset, hand_filters, hand_smoothed, hand_last_midi
    global button_rects_left, button_rects_right

    # Setup vision
    vision = Vision(camera_index=config.CAMERA_INDEX)
    extractor = LandmarkExtractor()

    # MIDI output
    midi_out = MidiOutput(port_name=config.MIDI_PORT_NAME)

    # Initialise both hands with preset 0 (Off)
    for hand_id in (0, 1):
        init_hand(hand_id)

    # Set up mouse callback
    cv2.namedWindow("Motion Controller")
    cv2.setMouseCallback("Motion Controller", mouse_callback)

    # Main loop
    while True:
        frame, results = vision.read()
        if frame is None:
            break

        h, w = frame.shape[:2]
        ui_height = 120          # two rows of buttons, each 60px
        frame_ui = frame.copy()

        # --- Process detected hands ---
        # Determine which hand is left/right by x-coordinate of wrist (landmark 0)
        hands = []
        if results and results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                wrist_x = hand_landmarks.landmark[0].x
                hands.append((wrist_x, hand_landmarks))
            # Sort by x (left to right)
            hands.sort(key=lambda t: t[0])
            # The first is left, second is right (if present)
            left_hand = hands[0][1] if len(hands) > 0 else None
            right_hand = hands[1][1] if len(hands) > 1 else None
        else:
            left_hand = right_hand = None

        # Process left hand if present and preset is not Off (index != 0)
        if left_hand is not None and hand_preset[0] != 0:
            process_hand(0, left_hand, frame_ui, w, h, vision)
        else:
            # If hand not detected or off, we keep last smoothed values (no update)
            pass

        # Process right hand similarly
        if right_hand is not None and hand_preset[1] != 0:
            process_hand(1, right_hand, frame_ui, w, h, vision)
        else:
            pass

        # --- Send MIDI messages (both hands) ---
        # We'll combine messages from both hands
        messages_to_send = []
        for hand_id in (0, 1):
            preset_idx = hand_preset[hand_id]
            if preset_idx == 0:
                continue
            preset = PRESETS[preset_idx]
            for feature, (channel, cc) in preset.midi_map.items():
                if feature in hand_smoothed[hand_id] and hand_smoothed[hand_id][feature] is not None:
                    raw = hand_smoothed[hand_id][feature]
                    norm_range = preset.norm_ranges.get(feature)
                    if norm_range is None:
                        continue
                    norm = normalize.normalize_value(raw, norm_range["min"], norm_range["max"])
                    midi_val = normalize.midi_value(norm)
                    if abs(midi_val - hand_last_midi[hand_id].get(feature, -1)) > preset.deadband * 127:
                        messages_to_send.append((channel, cc, midi_val))
                        hand_last_midi[hand_id][feature] = midi_val

        if messages_to_send:
            midi_out.send_messages(messages_to_send)

        # --- Draw UI: two rows of preset buttons ---
        button_rects_left.clear()
        button_rects_right.clear()
        num_presets = len(PRESETS)
        # We'll use 2/3 of the width for buttons, and show labels on the left
        button_width = (w - 40) // num_presets  # 20px margin on each side

        # Left hand row (y from h - ui_height to h - ui_height//2)
        row_y1 = h - ui_height
        row_y2 = h - ui_height//2
        draw_button_row(frame_ui, 0, row_y1, row_y2, button_width, num_presets, "L")
        # Right hand row (y from h - ui_height//2 to h)
        row_y1 = h - ui_height//2
        row_y2 = h
        draw_button_row(frame_ui, 1, row_y1, row_y2, button_width, num_presets, "R")

        # Draw status text
        cv2.putText(frame_ui, f"Left: {PRESETS[hand_preset[0]].name}", (10, h - ui_height - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
        cv2.putText(frame_ui, f"Right: {PRESETS[hand_preset[1]].name}", (10, h - ui_height//2 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)

        # Show shortcut hints
        cv2.putText(frame_ui, "Keys 1-9: change LEFT preset | Shift+1-9: change RIGHT preset",
                    (w - 400, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # Show MIDI status
        midi_status = "MIDI: Active" if midi_out.port else "MIDI: Not connected"
        cv2.putText(frame_ui, midi_status, (w - 200, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

        cv2.imshow("Motion Controller", frame_ui)

        # --- Keyboard handling ---
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            break
        # Check for number keys (1-9) without shift -> left hand
        if 49 <= key <= 57:  # '1' to '9'
            idx = key - 48  # 1-based index
            if idx < len(PRESETS):
                switch_preset(0, idx)
        # Check for shift+number (symbols) -> right hand
        # Map symbols: '!'=33, '@'=64, '#'=35, '$'=36, '%'=37, '^'=94, '&'=38, '*'=42, '('=40
        shift_map = {33:1, 64:2, 35:3, 36:4, 37:5, 94:6, 38:7, 42:8, 40:9}
        if key in shift_map:
            idx = shift_map[key]
            if idx < len(PRESETS):
                switch_preset(1, idx)

    # Cleanup
    vision.release()
    midi_out.close()
    cv2.destroyAllWindows()

# ----------------------------------------------------------------------
def process_hand(hand_id, hand_landmarks, frame, w, h, vision):
    """Extract features, update filters, draw landmarks and palm points."""
    preset_idx = hand_preset[hand_id]
    if preset_idx == 0:
        return
    preset = PRESETS[preset_idx]

    # Draw hand skeleton
    vision.drawer.draw_landmarks(
        frame,
        hand_landmarks,
        vision.mp_hands.HAND_CONNECTIONS,
    )

    # Get landmarks as list of tuples
    landmarks = []
    for lm in hand_landmarks.landmark:
        landmarks.append((lm.x, lm.y, lm.z))

    # Extract features using the preset's method
    raw_features = preset.features_func(landmarks)  # returns dict

    # Update filters for each feature
    for feature, raw_value in raw_features.items():
        if feature in hand_filters[hand_id]:
            # Update filter and store smoothed value
            hand_smoothed[hand_id][feature] = hand_filters[hand_id][feature].update(raw_value)
        else:
            # If not filtered, just store raw (should not happen if preset defines filter_settings)
            hand_smoothed[hand_id][feature] = raw_value

    # Optionally draw palm points (e.g., for debugging)
    # (you can add visualization code here if needed)

# ----------------------------------------------------------------------
def draw_button_row(frame, hand_id, y1, y2, button_width, num_presets, label):
    """Draw a row of preset buttons for a specific hand (left=0, right=1)."""
    rects = []
    x_start = 20  # left margin
    for i in range(num_presets):
        x1 = x_start + i * button_width
        x2 = x1 + button_width
        # Highlight if this is the active preset for that hand
        color = (0, 255, 0) if hand_preset[hand_id] == i else (100, 100, 100)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, -1)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 0), 2)
        # Text: preset name (shortened)
        text = f"{i}: {PRESETS[i].name}"
        if len(text) > 12:
            text = text[:10] + ".."
        font = cv2.FONT_HERSHEY_SIMPLEX
        (tw, th), _ = cv2.getTextSize(text, font, 0.5, 1)
        tx = x1 + (button_width - tw) // 2
        ty = y1 + (y2 - y1 + th) // 2 - 3
        cv2.putText(frame, text, (tx, ty), font, 0.5, (0, 0, 0), 1)
        # Store rectangle for mouse callback
        if hand_id == 0:
            button_rects_left.append((x1, y1, x2, y2, i))
        else:
            button_rects_right.append((x1, y1, x2, y2, i))

# ----------------------------------------------------------------------
if __name__ == "__main__":
    main()