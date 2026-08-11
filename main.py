# main.py
import cv2
import numpy as np
import time
import mido
from vision import Vision
from filters import OneEuroFilter
from midi_output import MidiOutput
from presets import PRESETS
import normalize
import config
import ui

# ----------------------------------------------------------------------
class MotionControllerApp:
    def __init__(self):
        # ---- State (former globals) ----
        self.hand_preset = [0, 0]
        self.hand_filters = [{}, {}]
        self.hand_smoothed = [{}, {}]
        self.hand_last_midi = [{}, {}]

        self.hand_tracks = []
        self.next_track_id = 0
        self.MAX_AGE = 20
        self.STABILITY_THRESHOLD = 10

        self.hand_note_state = [
            {'active': False, 'note': None, 'start_time': 0.0, 'smoothed_bend': 0.0},
            {'active': False, 'note': None, 'start_time': 0.0, 'smoothed_bend': 0.0}
        ]

        self.mapper_mode = False
        self.midi_out = None
        self.vision = None
        self.window_name = "Motion Controller"

        # ---- Initialisation ----
        self._setup_vision()
        self._setup_midi()
        for hand_id in (0, 1):
            self._init_hand(hand_id)
        ui.init_ui()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------
    def _setup_vision(self):
        self.vision = Vision(camera_index=config.CAMERA_INDEX)

    def _setup_midi(self):
        self.midi_out = MidiOutput(port_name=config.MIDI_PORT_NAME)

    # ------------------------------------------------------------------
    # Hand / Preset management (converted from globals)
    # ------------------------------------------------------------------
    def _update_hand_tracks(self, detected):
        """
        detected: list of (label, wx, wy)
        Returns a list of stable (label, wx, wy)
        """
        matched_indices = set()
        unmatched = []

        for label, wx, wy in detected:
            best_idx = -1
            best_dist = float('inf')
            for i, track in enumerate(self.hand_tracks):
                if i in matched_indices:
                    continue
                dx = wx - track['position'][0]
                dy = wy - track['position'][1]
                dist = dx*dx + dy*dy
                if dist < best_dist:
                    best_dist = dist
                    best_idx = i

            if best_idx != -1 and best_dist < 0.02:
                track = self.hand_tracks[best_idx]
                matched_indices.add(best_idx)
                track['position'] = (wx, wy)
                if track['label'] == label:
                    track['counter'] = 0
                else:
                    track['counter'] += 1
                    if track['counter'] >= self.STABILITY_THRESHOLD:
                        track['label'] = label
                        track['counter'] = 0
                track['age'] = 0
            else:
                unmatched.append((label, wx, wy))

        for label, wx, wy in unmatched:
            new_track = {
                'id': self.next_track_id,
                'label': label,
                'position': (wx, wy),
                'counter': 0,
                'age': 0
            }
            self.hand_tracks.append(new_track)
            self.next_track_id += 1

        self.hand_tracks = [t for t in self.hand_tracks if t['age'] < self.MAX_AGE]
        for t in self.hand_tracks:
            t['age'] += 1

        return [(t['label'], t['position'][0], t['position'][1]) for t in self.hand_tracks]

    def _init_hand(self, hand_id):
        """(Re‑)initialize filters and caches for a hand based on its current preset."""
        preset_idx = self.hand_preset[hand_id]
        preset = PRESETS[preset_idx]
        new_filters = {}
        for feature in preset.features:
            settings = preset.feature_configs[feature]["filter"]
            new_filters[feature] = OneEuroFilter(
                min_cutoff=settings[0] * config.GLOBAL_CUTOFF_MULTIPLIER,
                beta=settings[1] * config.GLOBAL_BETA_MULTIPLIER
            )
        self.hand_filters[hand_id] = new_filters
        self.hand_smoothed[hand_id] = {feature: None for feature in preset.features}
        self.hand_last_midi[hand_id] = {feature: -1 for feature in preset.features}

    def switch_preset(self, hand_id, preset_idx):
        """Change preset for a specific hand, turning off notes and resetting pitch bend."""
        old_preset = PRESETS[self.hand_preset[hand_id]]
        if old_preset.note_config is not None and self.hand_note_state[hand_id]['active']:
            self._send_note_off(hand_id, self.hand_note_state[hand_id]['note'])
            self._send_pitch_bend(hand_id, 0)
            self.hand_note_state[hand_id]['active'] = False
            self.hand_note_state[hand_id]['note'] = None
            self.hand_note_state[hand_id]['start_time'] = 0.0
            self.hand_note_state[hand_id]['smoothed_bend'] = 0.0

        if preset_idx < 0 or preset_idx >= len(PRESETS):
            return
        self.hand_preset[hand_id] = preset_idx
        self._init_hand(hand_id)

    # ------------------------------------------------------------------
    # MIDI output helpers
    # ------------------------------------------------------------------
    def _send_note_on(self, hand_id, note, velocity=100):
        if self.midi_out is None or not self.midi_out.port:
            return
        preset = PRESETS[self.hand_preset[hand_id]]
        if preset.note_config is None:
            return
        base_ch = preset.note_config['channel']
        hand_offset = config.LEFT_HAND_CHANNEL_OFFSET if hand_id == 0 else config.RIGHT_HAND_CHANNEL_OFFSET
        channel = min(15, max(0, base_ch + hand_offset))
        msg = mido.Message('note_on', channel=channel, note=note, velocity=velocity)
        self.midi_out.port.send(msg)
        print(f"Note ON: hand{hand_id} ch{channel+1} note{note}")

    def _send_note_off(self, hand_id, note):
        if self.midi_out is None or not self.midi_out.port:
            return
        preset = PRESETS[self.hand_preset[hand_id]]
        if preset.note_config is None:
            return
        base_ch = preset.note_config['channel']
        hand_offset = config.LEFT_HAND_CHANNEL_OFFSET if hand_id == 0 else config.RIGHT_HAND_CHANNEL_OFFSET
        channel = min(15, max(0, base_ch + hand_offset))
        msg = mido.Message('note_off', channel=channel, note=note, velocity=0)
        self.midi_out.port.send(msg)
        print(f"Note OFF: hand{hand_id} ch{channel+1} note{note}")

    def _send_pitch_bend(self, hand_id, bend_value):
        if self.midi_out is None or not self.midi_out.port:
            return
        preset = PRESETS[self.hand_preset[hand_id]]
        if preset.note_config is None:
            return
        base_ch = preset.note_config['channel']
        hand_offset = config.LEFT_HAND_CHANNEL_OFFSET if hand_id == 0 else config.RIGHT_HAND_CHANNEL_OFFSET
        channel = min(15, max(0, base_ch + hand_offset))
        bend_value = int(round(bend_value))
        bend_value = max(-8192, min(8191, bend_value))
        msg = mido.Message('pitchwheel', channel=channel, pitch=bend_value)
        self.midi_out.port.send(msg)

    def _note_cleanup(self):
        for hand_id in (0, 1):
            if self.hand_note_state[hand_id]['active']:
                note = self.hand_note_state[hand_id]['note']
                self._send_note_off(hand_id, note)
                self._send_pitch_bend(hand_id, 0)
                self.hand_note_state[hand_id]['active'] = False
                self.hand_note_state[hand_id]['note'] = None
                self.hand_note_state[hand_id]['start_time'] = 0.0
                self.hand_note_state[hand_id]['smoothed_bend'] = 0.0

    # ------------------------------------------------------------------
    # Per‑hand processing (drawing & filtering)
    # ------------------------------------------------------------------
    def _process_hand(self, hand_id, hand_landmarks, frame, w, h):
        """Extract features, update filters, draw hand skeleton with color."""
        preset_idx = self.hand_preset[hand_id]
        if preset_idx == 0:
            return
        preset = PRESETS[preset_idx]

        # ---- Draw hand skeleton ----
        if hand_id == 0:  # left hand → light blue
            connection_spec = self.vision.drawer.DrawingSpec(
                color=(255, 200, 150),
                thickness=2,
                circle_radius=2
            )
            landmark_spec = self.vision.drawer.DrawingSpec(
                color=(255, 200, 150),
                thickness=2,
                circle_radius=2
            )
            self.vision.drawer.draw_landmarks(
                frame,
                hand_landmarks,
                self.vision.mp_hands.HAND_CONNECTIONS,
                connection_drawing_spec=connection_spec,
                landmark_drawing_spec=landmark_spec
            )
            wrist = hand_landmarks.landmark[0]
            x, y = int(wrist.x * w), int(wrist.y * h)
            cv2.putText(frame, "Left", (x - 20, y - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 150), 2)
        else:  # right hand → default MediaPipe colors
            self.vision.drawer.draw_landmarks(
                frame,
                hand_landmarks,
                self.vision.mp_hands.HAND_CONNECTIONS,
            )
            wrist = hand_landmarks.landmark[0]
            x, y = int(wrist.x * w), int(wrist.y * h)
            cv2.putText(frame, "Right", (x - 20, y - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # ---- Get landmarks ----
        landmarks = []
        for lm in hand_landmarks.landmark:
            landmarks.append((lm.x, lm.y, lm.z))

        # ---- Mirror left hand if preset allows ----
        if hand_id == 0 and preset.mirror_left_hand:
            landmarks = [(1.0 - x, y, z) for (x, y, z) in landmarks]

        # ---- Extract all features defined in this preset ----
        raw_features = preset.get_features(landmarks)

        # ---- Update filters for each feature ----
        for feature, raw_value in raw_features.items():
            if feature in self.hand_filters[hand_id]:
                self.hand_smoothed[hand_id][feature] = self.hand_filters[hand_id][feature].update(raw_value)
            else:
                self.hand_smoothed[hand_id][feature] = raw_value

    # ------------------------------------------------------------------
    # Main loop helpers
    # ------------------------------------------------------------------
    def _process_frame(self, frame, results):
        """
        Handles one frame: tracking, filtering, MIDI CC, note generation.
        Returns the (possibly drawn) frame.
        """
        h, w = frame.shape[:2]

        # ---- 1. Detect hands with labels ----
        detected_hands = []
        if results and results.multi_hand_landmarks:
            if results.multi_handedness:
                labels = [results.multi_handedness[i].classification[0].label
                          for i in range(len(results.multi_hand_landmarks))]
                if len(labels) == 2 and labels[0] == labels[1]:
                    print(f"⚠️ Handedness conflict: both detected as {labels[0]}. Falling back to spatial sorting.")
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

        # ---- 2. Update tracker ----
        detected_positions = [(label, lm.landmark[0].x, lm.landmark[0].y) for label, lm in detected_hands]
        stable_hands = self._update_hand_tracks(detected_positions)

        # ---- 3. Process each hand (draws on frame) ----
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
                    self._process_hand(hand_id, lm, frame, w, h)
                    processed_ids.add(hand_id)

        # ---- 4. Send MIDI CC messages ----
        messages_to_send = []
        for hand_id in (0, 1):
            preset_idx = self.hand_preset[hand_id]
            if preset_idx == 0:
                continue
            preset = PRESETS[preset_idx]
            hand_offset = config.LEFT_HAND_CHANNEL_OFFSET if hand_id == 0 else config.RIGHT_HAND_CHANNEL_OFFSET
            for feature in preset.features:
                midi_info = preset.feature_configs[feature]["midi"]
                if midi_info is None:
                    continue
                base_ch, cc = midi_info
                if feature in self.hand_smoothed[hand_id] and self.hand_smoothed[hand_id][feature] is not None:
                    raw = self.hand_smoothed[hand_id][feature]
                    norm_range = preset.feature_configs[feature]["norm_range"]
                    norm = normalize.normalize_value(raw, norm_range[0], norm_range[1])
                    midi_val = normalize.midi_value(norm)
                    if abs(midi_val - self.hand_last_midi[hand_id].get(feature, -1)) > preset.deadband * 127:
                        actual_channel = min(15, max(0, base_ch + hand_offset))
                        messages_to_send.append((actual_channel, cc, midi_val))
                        self.hand_last_midi[hand_id][feature] = midi_val

        if messages_to_send:
            self.midi_out.send_messages(messages_to_send)

        # ---- 5. Note generation ----
        current_time = time.time()
        for hand_id in (0, 1):
            preset_idx = self.hand_preset[hand_id]
            if preset_idx == 0:
                continue
            preset = PRESETS[preset_idx]
            if preset.note_config is None:
                continue

            note_cfg = preset.note_config
            note_source = note_cfg["note_source"]
            bend_source = note_cfg["bend_source"]
            gate_source = note_cfg["gate_source"]

            # Ensure we have smoothed values for all required sources
            if any(f not in self.hand_smoothed[hand_id] or self.hand_smoothed[hand_id][f] is None
                   for f in (note_source, bend_source, gate_source)):
                continue

            # Get raw smoothed values
            note_raw = self.hand_smoothed[hand_id][note_source]
            bend_raw = self.hand_smoothed[hand_id][bend_source]
            gate_raw = self.hand_smoothed[hand_id][gate_source]

            # Normalise using each feature's own range
            norm_range_note = preset.feature_configs[note_source]["norm_range"]
            norm_y = normalize.normalize_value(note_raw, norm_range_note[0], norm_range_note[1])

            norm_range_bend = preset.feature_configs[bend_source]["norm_range"]
            norm_x = normalize.normalize_value(bend_raw, norm_range_bend[0], norm_range_bend[1])

            # dist (gate) – threshold is compared to raw gate value
            dist = gate_raw

            note_min = note_cfg["note_min"]
            note_max = note_cfg["note_max"]
            candidate_note = int(round((1 - norm_y) * (note_max - note_min) + note_min))
            candidate_note = max(0, min(127, candidate_note))

            raw_bend = (norm_x - 0.5) * 16384
            raw_bend = max(-8192, min(8191, raw_bend))

            threshold = note_cfg["threshold"]
            timeout = note_cfg["timeout"]
            state = self.hand_note_state[hand_id]

            if not state['active'] and dist < threshold:
                self._send_note_on(hand_id, candidate_note)
                state['active'] = True
                state['note'] = candidate_note
                state['start_time'] = current_time
                state['smoothed_bend'] = raw_bend
                self._send_pitch_bend(hand_id, int(round(state['smoothed_bend'])))
            elif state['active'] and dist >= threshold:
                self._send_note_off(hand_id, state['note'])
                self._send_pitch_bend(hand_id, 0)
                state['active'] = False
                state['note'] = None
                state['start_time'] = 0.0
                state['smoothed_bend'] = 0.0
            elif state['active']:
                alpha = 0.2
                state['smoothed_bend'] = alpha * raw_bend + (1 - alpha) * state['smoothed_bend']
                bend_smoothed = int(round(state['smoothed_bend']))
                bend_smoothed = max(-8192, min(8191, bend_smoothed))
                self._send_pitch_bend(hand_id, bend_smoothed)
                if (current_time - state['start_time']) > timeout:
                    self._send_note_off(hand_id, state['note'])
                    self._send_pitch_bend(hand_id, 0)
                    state['active'] = False
                    state['note'] = None
                    state['start_time'] = 0.0
                    state['smoothed_bend'] = 0.0

        return frame

    def _handle_key(self, key):
        """Handle all keyboard shortcuts. Returns False to quit, True to continue."""
        if key == 27:  # ESC
            return False
        if key == ord('m'):
            self.mapper_mode = not self.mapper_mode
            if not self.mapper_mode:
                ui.mapper_rects = []
            return True
        # Left hand: number keys 0-9
        if 48 <= key <= 57:
            idx = key - 48
            if idx < len(PRESETS):
                self.switch_preset(0, idx)
            return True
        # Right hand: Shift+number
        shift_map = {
            33: 1,  # !
            34: 2,  # "
            167: 3, # §
            36: 4,  # $
            37: 5,  # %
            38: 6,  # &
            47: 7,  # /
            40: 8,  # (
            41: 9,  # )
            61: 0,  # =
        }
        if key in shift_map:
            idx = shift_map[key]
            if idx < len(PRESETS):
                self.switch_preset(1, idx)
            return True
        return True

    # ------------------------------------------------------------------
    # Main run loop
    # ------------------------------------------------------------------
    def run(self):
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, 1280, 720)

        # Mouse callback (still uses ui.py, we pass the needed references)
        callback_params = {
            'hand_preset': self.hand_preset,
            'hand_smoothed': self.hand_smoothed,
            'midi_out': self.midi_out,
            'mapper_mode': lambda: self.mapper_mode,
            'switch_preset': self.switch_preset,
            'window_name': self.window_name
        }
        cv2.setMouseCallback(self.window_name, ui.mouse_callback, param=callback_params)

        try:
            while True:
                frame, results = self.vision.read()
                if frame is None:
                    break

                # ---- Process frame (tracking, MIDI, notes) ----
                frame = self._process_frame(frame, results)

                # ---- Build the combined canvas (UI overlay) ----
                h, w = frame.shape[:2]
                try:
                    rect = cv2.getWindowImageRect(self.window_name)
                    win_w, win_h = rect[2], rect[3]
                except Exception:
                    win_w, win_h = 1280, 720
                win_w = max(win_w, 600)
                win_h = max(win_h, 400)

                right_panel_w = max(ui.MIN_RIGHT_PANEL_WIDTH, int(win_w * ui.RIGHT_PANEL_RATIO))
                bottom_panel_h = max(ui.MIN_BOTTOM_PANEL_HEIGHT, int(win_h * ui.BOTTOM_PANEL_RATIO))
                camera_w = win_w - right_panel_w
                camera_h = win_h - bottom_panel_h

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

                canvas = np.full((win_h, win_w, 3), 30, dtype=np.uint8)
                canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = frame_resized

                font_scale = min(win_w, win_h) / 1200.0
                midi_status = "MIDI: Active" if self.midi_out.port else "MIDI: Not connected"
                ui.draw_right_panel(canvas, camera_w, 0, right_panel_w, camera_h,
                                    self.hand_preset, self.hand_smoothed, midi_status, font_scale,
                                    note_state=self.hand_note_state)
                ui.draw_bottom_panel(canvas, 0, camera_h, win_w, bottom_panel_h,
                                     self.hand_preset, font_scale)

                if self.mapper_mode:
                    ui.draw_mapper_overlay(canvas, win_w, win_h, self.hand_preset, self.hand_smoothed, font_scale)

                # Shortcut hints
                cv2.putText(canvas, "Press 'm' for MIDI Mapper Mode", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, font_scale * 0.8, (200, 200, 200), 1)
                cv2.putText(canvas, "0-9: LEFT preset | Shift+0-9: RIGHT preset",
                            (10, win_h - 10), cv2.FONT_HERSHEY_SIMPLEX, font_scale * 0.8, (200, 200, 200), 1)

                cv2.imshow(self.window_name, canvas)

                # ---- Keyboard handling ----
                key = cv2.waitKey(1) & 0xFF
                if not self._handle_key(key):
                    break

        finally:
            self._note_cleanup()
            self.vision.release()
            self.midi_out.close()
            cv2.destroyAllWindows()

# ----------------------------------------------------------------------
if __name__ == "__main__":
    app = MotionControllerApp()
    app.run()