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

# --- Hand tracking state ---
hand_tracks = []          # list of dicts: {id, label, position, counter, age}
next_track_id = 0
MAX_AGE = 20              # frames before a track is removed
STABILITY_THRESHOLD = 10   # frames before switching label

# Mapper mode
mapper_mode = False

# ----------------------------------------------------------------------
def update_hand_tracks(detected):
    """
    detected: list of (label, wx, wy)
    Returns a dict mapping track_id -> label (or list of (label, wx, wy) for stable positions)
    """
    global hand_tracks, next_track_id

    # Step 1: Match detected hands to existing tracks
    matched_indices = set()
    unmatched = []

    for label, wx, wy in detected:
        best_idx = -1
        best_dist = float('inf')
        for i, track in enumerate(hand_tracks):
            if i in matched_indices:
                continue
            dx = wx - track['position'][0]
            dy = wy - track['position'][1]
            dist = dx*dx + dy*dy
            if dist < best_dist:
                best_dist = dist
                best_idx = i

        if best_idx != -1 and best_dist < 0.02:  # threshold ~2% of screen
            # Match found
            track = hand_tracks[best_idx]
            matched_indices.add(best_idx)
            track['position'] = (wx, wy)
            # Label stability
            if track['label'] == label:
                track['counter'] = 0
            else:
                track['counter'] += 1
                if track['counter'] >= STABILITY_THRESHOLD:
                    track['label'] = label
                    track['counter'] = 0
            track['age'] = 0
        else:
            # No match → new track
            unmatched.append((label, wx, wy))

    # Step 2: Create new tracks for unmatched detections
    for label, wx, wy in unmatched:
        new_track = {
            'id': next_track_id,
            'label': label,
            'position': (wx, wy),
            'counter': 0,
            'age': 0
        }
        hand_tracks.append(new_track)
        next_track_id += 1

    # Step 3: Increment age and remove old tracks
    hand_tracks = [t for t in hand_tracks if t['age'] < MAX_AGE]
    for t in hand_tracks:
        t['age'] += 1

    # Step 4: Return stable labels and positions
    return [(t['label'], t['position'][0], t['position'][1]) for t in hand_tracks]

# ----------------------------------------------------------------------
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

# ----------------------------------------------------------------------
def process_hand(hand_id, hand_landmarks, frame, w, h, vision):
    """Extract features, update filters, draw hand skeleton with color."""
    preset_idx = hand_preset[hand_id]
    if preset_idx == 0:
        return
    preset = PRESETS[preset_idx]

    # ---- Draw hand skeleton ----
    if hand_id == 0:  # left hand → light blue
        connection_spec = vision.drawer.DrawingSpec(
            color=(255, 200, 150),   # light blue (BGR)
            thickness=2,
            circle_radius=2
        )
        landmark_spec = vision.drawer.DrawingSpec(
            color=(255, 200, 150),
            thickness=2,
            circle_radius=2
        )
        vision.drawer.draw_landmarks(
            frame,
            hand_landmarks,
            vision.mp_hands.HAND_CONNECTIONS,
            connection_drawing_spec=connection_spec,
            landmark_drawing_spec=landmark_spec
        )
        wrist = hand_landmarks.landmark[0]
        x, y = int(wrist.x * w), int(wrist.y * h)
        cv2.putText(frame, "Left", (x - 20, y - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 150), 2)
    else:  # right hand → default MediaPipe colors
        vision.drawer.draw_landmarks(
            frame,
            hand_landmarks,
            vision.mp_hands.HAND_CONNECTIONS,
        )
        wrist = hand_landmarks.landmark[0]
        x, y = int(wrist.x * w), int(wrist.y * h)
        cv2.putText(frame, "Right", (x - 20, y - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    # ---- Get landmarks ----
    landmarks = []
    for lm in hand_landmarks.landmark:
        landmarks.append((lm.x, lm.y, lm.z))

    # ---- Mirror left hand only if the preset allows it ----
    if hand_id == 0 and preset.mirror_left_hand:
        landmarks = [(1.0 - x, y, z) for (x, y, z) in landmarks]

    # ---- Feature extraction ----
    raw_features = preset.features_func(landmarks)

    # Update filters
    for feature, raw_value in raw_features.items():
        if feature in hand_filters[hand_id]:
            hand_smoothed[hand_id][feature] = hand_filters[hand_id][feature].update(raw_value)
        else:
            hand_smoothed[hand_id][feature] = raw_value

# ----------------------------------------------------------------------
def main():
    global midi_out, hand_preset, hand_filters, hand_smoothed, hand_last_midi
    global hand_tracks, next_track_id, mapper_mode

    # Setup vision
    vision = Vision(camera_index=config.CAMERA_INDEX)
    extractor = LandmarkExtractor()

    # MIDI output
    midi_out = MidiOutput(port_name=config.MIDI_PORT_NAME)

    # Initialise both hands with preset 0 (Off)
    for hand_id in (0, 1):
        init_hand(hand_id)

    window_name = "Motion Controller"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 720)

    callback_params = {
        'hand_preset': hand_preset,
        'hand_smoothed': hand_smoothed,
        'midi_out': midi_out,
        'mapper_mode': lambda: mapper_mode,
        'switch_preset': switch_preset,
        'window_name': window_name
    }
    cv2.setMouseCallback(window_name, ui.mouse_callback, param=callback_params)

    # Main loop
    while True:
        frame, results = vision.read()
        if frame is None:
            break

        h, w = frame.shape[:2]

        # ---- Hand detection (unchanged) ----
        detected_hands = []
        if results and results.multi_hand_landmarks:
            if results.multi_handedness:
                labels = [results.multi_handedness[i].classification[0].label
                          for i in range(len(results.multi_hand_landmarks))]
                if len(labels) == 2 and labels[0] == labels[1]:
                    #print(f"⚠️ Handedness conflict: both detected as {labels[0]}. Falling back to spatial sorting.")
                    hands_with_x = []
                    for hand_landmarks in results.multi_hand_landmarks:
                        wrist_x = hand_landmarks.landmark[0].x
                        hands_with_x.append((wrist_x, hand_landmarks))
                    hands_with_x.sort(key=lambda t: t[0])
                    if len(hands_with_x) > 0:
                        detected_hands.append(('Left', hands_with_x[0][1]))
                    if len(hands_with_x) > 1:
                        detected_hands.append(('Right', hands_with_x[1][1]))
                else:
                    for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                        label = results.multi_handedness[idx].classification[0].label
                        detected_hands.append((label, hand_landmarks))
            else:
                # No handedness data – fallback to spatial
                hands = []
                for hand_landmarks in results.multi_hand_landmarks:
                    wrist_x = hand_landmarks.landmark[0].x
                    hands.append((wrist_x, hand_landmarks))
                hands.sort(key=lambda t: t[0])
                if len(hands) > 0:
                    detected_hands.append(('Left', hands[0][1]))
                if len(hands) > 1:
                    detected_hands.append(('Right', hands[1][1]))

        # ---- Update tracker ----
        detected_positions = [(label, lm.landmark[0].x, lm.landmark[0].y) for label, lm in detected_hands]
        stable_hands = update_hand_tracks(detected_positions)

        # ---- Process each detected hand (draws on the original frame) ----
        processed_ids = set()
        for label, lm in detected_hands:
            wrist = lm.landmark[0]
            best_stable_label = None
            best_dist = float('inf')
            for s_label, sx, sy in stable_hands:
                dx = sx - wrist.x
                dy = sy - wrist.y
                dist = dx*dx + dy*dy
                if dist < best_dist:
                    best_dist = dist
                    best_stable_label = s_label

            if best_stable_label is not None and best_dist < 0.02:
                hand_id = 0 if best_stable_label == 'Left' else 1
                if hand_id not in processed_ids:
                    process_hand(hand_id, lm, frame, w, h, vision)
                    processed_ids.add(hand_id)

        # ---- Now the frame has all drawings ----
        # ---- Get window size and compute layout ----
        try:
            rect = cv2.getWindowImageRect(window_name)
            win_w, win_h = rect[2], rect[3]
        except Exception:
            win_w, win_h = 1280, 720
        win_w = max(win_w, 600)
        win_h = max(win_h, 400)

        right_panel_w = max(ui.MIN_RIGHT_PANEL_WIDTH, int(win_w * ui.RIGHT_PANEL_RATIO))
        bottom_panel_h = max(ui.MIN_BOTTOM_PANEL_HEIGHT, int(win_h * ui.BOTTOM_PANEL_RATIO))
        camera_w = win_w - right_panel_w
        camera_h = win_h - bottom_panel_h

        # ---- Resize the drawn frame to fit camera area (preserve aspect) ----
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

        # ---- Create final canvas ----
        canvas = np.full((win_h, win_w, 3), 30, dtype=np.uint8)
        canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = frame_resized

        # ---- Draw UI panels (dynamic sizing) ----
        font_scale = min(win_w, win_h) / 1200.0
        midi_status = "MIDI: Active" if midi_out.port else "MIDI: Not connected"
        ui.draw_right_panel(canvas, camera_w, 0, right_panel_w, camera_h,
                            hand_preset, hand_smoothed, midi_status, font_scale)
        ui.draw_bottom_panel(canvas, 0, camera_h, win_w, bottom_panel_h,
                             hand_preset, font_scale)

        if mapper_mode:
            ui.draw_mapper_overlay(canvas, win_w, win_h, hand_preset, hand_smoothed, font_scale)

        # ---- Shortcut hints ----
        cv2.putText(canvas, "Press 'm' for MIDI Mapper Mode", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale * 0.8, (200, 200, 200), 1)
        cv2.putText(canvas, "0-9: LEFT preset | Shift+0-9: RIGHT preset",
                    (10, win_h - 10), cv2.FONT_HERSHEY_SIMPLEX, font_scale * 0.8, (200, 200, 200), 1)

        # ---- Send MIDI (unchanged) ----
        messages_to_send = []
        for hand_id in (0, 1):
            preset_idx = hand_preset[hand_id]
            if preset_idx == 0:
                continue
            preset = PRESETS[preset_idx]
            hand_offset = config.LEFT_HAND_CHANNEL_OFFSET if hand_id == 0 else config.RIGHT_HAND_CHANNEL_OFFSET
            for feature, (base_channel, cc) in preset.midi_map.items():
                if feature in hand_smoothed[hand_id] and hand_smoothed[hand_id][feature] is not None:
                    raw = hand_smoothed[hand_id][feature]
                    norm_range = preset.norm_ranges.get(feature)
                    if norm_range is None:
                        continue
                    norm = normalize.normalize_value(raw, norm_range["min"], norm_range["max"])
                    midi_val = normalize.midi_value(norm)
                    if abs(midi_val - hand_last_midi[hand_id].get(feature, -1)) > preset.deadband * 127:
                        actual_channel = min(15, max(0, base_channel + hand_offset))
                        messages_to_send.append((actual_channel, cc, midi_val))
                        hand_last_midi[hand_id][feature] = midi_val

        if messages_to_send:
            midi_out.send_messages(messages_to_send)

        # ---- Show ----
        cv2.imshow(window_name, canvas)

        # ---- Keyboard ----
        key = cv2.waitKey(1) & 0xFF
        if key == 27:
            break
        if key == ord('m'):
            mapper_mode = not mapper_mode
            if not mapper_mode:
                ui.mapper_rects = []
            continue
        if 48 <= key <= 57:
            idx = key - 48
            if idx < len(PRESETS):
                switch_preset(0, idx)
        shift_map = {
            33: 1, 64: 2, 35: 3, 36: 4, 37: 5, 94: 6, 38: 7, 42: 8, 40: 9,
            41: 0, 34: 2, 167: 3, 47: 7, 61: 0
        }
        if key in shift_map:
            idx = shift_map[key]
            if idx < len(PRESETS):
                switch_preset(1, idx)

    vision.release()
    midi_out.close()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()