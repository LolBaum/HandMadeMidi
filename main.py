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
import ui

# ----------------------------------------------------------------------
# Global state for two hands
hand_preset = [0, 0]          # start with Off for both
hand_filters = [{}, {}]       # filters for each hand
hand_smoothed = [{}, {}]      # last smoothed raw values
hand_last_midi = [{}, {}]     # last MIDI values for deadband

midi_out = None

def init_hand(hand_id):
    """(Re‑)initialize filters and caches for a hand based on its current preset."""
    preset_idx = hand_preset[hand_id]
    preset = PRESETS[preset_idx]
    new_filters = {}
    for feature, settings in preset.filter_settings.items():
        new_filters[feature] = OneEuroFilter(
            min_cutoff=settings["min_cutoff"] * config.GLOBAL_CUTOFF_MULTIPLIER,
            beta=settings["beta"] * config.GLOBAL_BETA_MULTIPLIER
        )
    hand_filters[hand_id] = new_filters
    hand_smoothed[hand_id] = {feature: None for feature in preset.filter_settings.keys()}
    hand_last_midi[hand_id] = {feature: -1 for feature in preset.midi_map.keys()}

def switch_preset(hand_id, preset_idx):
    """Change preset for a specific hand and re‑initialise its state."""
    if preset_idx < 0 or preset_idx >= len(PRESETS):
        return
    hand_preset[hand_id] = preset_idx
    init_hand(hand_id)

def process_hand(hand_id, hand_landmarks, frame, w, h, vision):
    """Extract features, update filters, draw hand skeleton."""
    preset_idx = hand_preset[hand_id]
    if preset_idx == 0:
        return
    preset = PRESETS[preset_idx]

    # Draw hand skeleton on the camera frame
    vision.drawer.draw_landmarks(
        frame,
        hand_landmarks,
        vision.mp_hands.HAND_CONNECTIONS,
    )

    # Get landmarks as list of (x, y, z) tuples
    landmarks = []
    for lm in hand_landmarks.landmark:
        landmarks.append((lm.x, lm.y, lm.z))

    # --- Mirror landmarks for the left hand (symmetry) ---
    # Reflect across the vertical axis (x → 1 - x) so the left hand behaves like a right hand.
    # This ensures yaw, roll, and position all have the same directional sense.
    if hand_id == 0:  # left hand
        landmarks = [(1.0 - x, y, z) for (x, y, z) in landmarks]

    # Extract features using the preset's method
    raw_features = preset.features_func(landmarks)

    # Update filters for each feature
    for feature, raw_value in raw_features.items():
        if feature in hand_filters[hand_id]:
            hand_smoothed[hand_id][feature] = hand_filters[hand_id][feature].update(raw_value)
        else:
            hand_smoothed[hand_id][feature] = raw_value

# ----------------------------------------------------------------------
def main():
    global midi_out, hand_preset, hand_filters, hand_smoothed, hand_last_midi

    # Setup vision
    vision = Vision(camera_index=config.CAMERA_INDEX)
    extractor = LandmarkExtractor()

    # MIDI output
    midi_out = MidiOutput(port_name=config.MIDI_PORT_NAME)

    # Initialise both hands with preset 0 (Off)
    for hand_id in (0, 1):
        init_hand(hand_id)

    # Set up mouse callback with parameters
    callback_params = {
        'hand_preset': hand_preset,
        'switch_preset': switch_preset
    }
    cv2.namedWindow("Motion Controller")
    cv2.setMouseCallback("Motion Controller", ui.mouse_callback, param=callback_params)

    # Main loop
    while True:
        frame, results = vision.read()
        if frame is None:
            break

        h, w = frame.shape[:2]

        midi_status =  "MIDI: Active" if midi_out.port else "MIDI: Not connected"

        # --- Process hands and draw landmarks on the original frame ---
        # Determine left/right hands based on wrist x-coordinate
        hands = []
        if results and results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                wrist_x = hand_landmarks.landmark[0].x
                hands.append((wrist_x, hand_landmarks))
            hands.sort(key=lambda t: t[0])  # left to right
            left_hand = hands[0][1] if len(hands) > 0 else None
            right_hand = hands[1][1] if len(hands) > 1 else None
        else:
            left_hand = right_hand = None

        # Process left hand
        if left_hand is not None and hand_preset[0] != 0:
            process_hand(0, left_hand, frame, w, h, vision)
        # Process right hand
        if right_hand is not None and hand_preset[1] != 0:
            process_hand(1, right_hand, frame, w, h, vision)

        # --- Build the combined canvas ---
        canvas_h = h + ui.BOTTOM_PANEL_HEIGHT
        canvas_w = w + ui.RIGHT_PANEL_WIDTH
        canvas = np.full((canvas_h, canvas_w, 3), 30, dtype=np.uint8)

        # Place the camera frame (with drawings) in top-left corner
        canvas[0:h, 0:w] = frame

        # Draw right panel (values)
        ui.draw_right_panel(canvas, w, 0, ui.RIGHT_PANEL_WIDTH, h, hand_preset, hand_smoothed, midi_status=midi_status)

        # Draw bottom panel (buttons)
        ui.draw_bottom_panel(canvas, 0, h, canvas_w, ui.BOTTOM_PANEL_HEIGHT, hand_preset)

        # --- Send MIDI messages (both hands) ---
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

        # --- Add status and shortcut hints on canvas ---
        midi_status =  "MIDI: Active" if midi_out.port else "MIDI: Not connected"
        cv2.putText(canvas, "0-9: change LEFT preset | Shift+0-9: change RIGHT preset",
                    (10, canvas_h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        cv2.imshow("Motion Controller", canvas)

        # --- Keyboard handling ---
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            break

        # Left hand: number keys 0-9
        if 48 <= key <= 57:  # '0' to '9'
            idx = key - 48   # 0-9
            if idx < len(PRESETS):
                switch_preset(0, idx)

        # Right hand: Shift+number (symbols)
        # Map shifted symbols for common layouts
        shift_map = {
            # US layout (Shift+1..9,0)
            33: 1,  # !
            64: 2,  # @
            35: 3,  # #
            36: 4,  # $
            37: 5,  # %
            94: 6,  # ^
            38: 7,  # &
            42: 8,  # *
            40: 9,  # (
            41: 0,  # )   <- Shift+0 on US
            # German layout (Shift+1..9,0)
            34: 2,  # "
            167: 3, # §
            47: 7,  # /
            41: 0,  # )   also used on some layouts
            61: 0,  # =   Shift+0 on German
        }
        if key in shift_map:
            idx = shift_map[key]
            if idx < len(PRESETS):
                switch_preset(1, idx)

    # Cleanup
    vision.release()
    midi_out.close()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()