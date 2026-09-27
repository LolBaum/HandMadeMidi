# main.py
import cv2
import numpy as np
import time
import mido

from layout import build_canvas
from midi_cc import MidiCCProcessor
from note_engine import NoteEngine
from pitch_bend import PitchBendProcessor
from tracker import HandTracker
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
        # ---- State ----
        self.hand_preset = [0, 0]
        self.hand_filters = [{}, {}]
        self.hand_smoothed = [{}, {}]

        self.tracker = HandTracker(
            match_distance=0.02,
            max_age=20,
            stability_threshold=10
        )

        self.hand_note_state = [
            {'active': False, 'note': None, 'start_time': 0.0},
            {'active': False, 'note': None, 'start_time': 0.0}
        ]
        self.note_engine = NoteEngine(state=self.hand_note_state)

        self.midi_cc = MidiCCProcessor()
        self.pitch_bend = PitchBendProcessor()

        self.mapper_mode = False
        self.midi_out = None
        self.vision = None
        self.window_name = "Motion Controller"

        self.ui = ui.UIRenderer(
            window_name=self.window_name,
            on_preset_switch=self.switch_preset,
            on_toggle_topmost=self._toggle_topmost,
            on_mapper_send=self._send_mapper_cc
        )

        # ---- Initialisation (after UI) ----
        self._setup_vision()
        self._setup_midi()
        for hand_id in (0, 1):
            self._init_hand(hand_id)

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------
    # Add a method for topmost toggle
    def _toggle_topmost(self):
        """Callback from UI to toggle topmost window property."""
        try:
            cv2.setWindowProperty(self.window_name, cv2.WND_PROP_TOPMOST,
                                  1 if self.ui._topmost else 0)
        except cv2.error as e:
            print('error', e)

    # Add a method for mapper send
    def _send_mapper_cc(self, hand_id, feature):
        """Callback from UI: send the current MIDI value for a feature."""
        preset_idx = self.hand_preset[hand_id]
        if preset_idx == 0:
            return
        preset = PRESETS[preset_idx]
        midi_info = preset.feature_configs[feature]["midi"]
        if midi_info is None:
            return
        base_ch, cc = midi_info
        hand_offset = config.LEFT_HAND_CHANNEL_OFFSET if hand_id == 0 else config.RIGHT_HAND_CHANNEL_OFFSET
        actual_ch = min(15, max(0, base_ch + hand_offset))

        # Get current value
        if feature in self.hand_smoothed[hand_id] and self.hand_smoothed[hand_id][feature] is not None:
            raw = self.hand_smoothed[hand_id][feature]
            norm_range = preset.feature_configs[feature]["norm_range"]
            norm = normalize.normalize_value(raw, norm_range[0], norm_range[1])
            value = normalize.midi_value(norm)
        else:
            value = 64  # fallback

        self.midi_out.send_cc(actual_ch, cc, value)
        print(f"Mapper: hand{hand_id} {feature} -> ch{actual_ch + 1} cc{cc} val{value}")

    def _setup_vision(self):
        self.vision = Vision(camera_index=config.CAMERA_INDEX)

    def _setup_midi(self):
        self.midi_out = MidiOutput(port_name=config.MIDI_PORT_NAME)

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
        self.midi_cc.reset_hand(hand_id)
        self.hand_filters[hand_id] = new_filters
        self.hand_smoothed[hand_id] = {feature: None for feature in preset.features}
        self.pitch_bend.reset_hand(hand_id)

    # ------------------------------------------------------------------
    # Hand detection and processing (extracted from _process_frame)
    # ------------------------------------------------------------------
    def _detect_hands(self, results):
        """
        Extract hand landmarks and labels from MediaPipe results.
        Returns a list of (label, hand_landmarks) with robust fallback logic.
        """
        detected_hands = []
        if not results or not results.multi_hand_landmarks:
            return detected_hands

        if results.multi_handedness:
            labels = [results.multi_handedness[i].classification[0].label
                      for i in range(len(results.multi_hand_landmarks))]
            # Handle conflict where both hands claim same label
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
            # No handedness data – fallback to spatial sorting
            hands = []
            for hand_landmarks in results.multi_hand_landmarks:
                wrist_x = hand_landmarks.landmark[0].x
                hands.append((wrist_x, hand_landmarks))
            hands.sort(key=lambda t: t[0])
            if len(hands) > 0:
                detected_hands.append(('Left', hands[0][1]))
            if len(hands) > 1:
                detected_hands.append(('Right', hands[1][1]))

        return detected_hands

    def _process_detected_hands(self, detected_hands, frame, w, h):
        """
        Match detected hands to stable tracks and run feature extraction/drawing.
        """
        # Update tracker with current positions
        detected_positions = [(label, lm.landmark[0].x, lm.landmark[0].y)
                              for label, lm in detected_hands]
        stable_hands = self.tracker.update(detected_positions)

        # Match each detection to a stable track and process
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

    # ------------------------------------------------------------------
    # Note processing
    # ------------------------------------------------------------------
    def _process_notes(self):
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
            gate_source = note_cfg["gate_source"]

            if any(f not in self.hand_smoothed[hand_id] or self.hand_smoothed[hand_id][f] is None
                   for f in (note_source, gate_source)):
                continue

            note_raw = self.hand_smoothed[hand_id][note_source]
            gate_raw = self.hand_smoothed[hand_id][gate_source]

            norm_range_note = preset.feature_configs[note_source]["norm_range"]
            norm_note = normalize.normalize_value(note_raw, norm_range_note[0], norm_range_note[1])

            note_config = {
                'note_min': note_cfg['note_min'],
                'note_max': note_cfg['note_max'],
                'threshold': note_cfg['threshold'],
                'timeout': note_cfg['timeout'],
            }

            actions = self.note_engine.update(
                hand_id, norm_note, gate_raw,
                current_time, note_config
            )

            for action in actions:
                if action[0] == 'note_on':
                    _, hand, note, vel = action
                    self._send_note_on(hand, note, vel)
                elif action[0] == 'note_off':
                    _, hand, note = action
                    self._send_note_off(hand, note)

    def _process_pitch_bend(self):
        for hand_id in (0, 1):
            preset_idx = self.hand_preset[hand_id]
            if preset_idx == 0:
                continue
            preset = PRESETS[preset_idx]
            if preset.pitch_bend_config is None:
                continue
            hand_offset = self._get_hand_offset(hand_id)
            result = self.pitch_bend.process_hand(
                hand_id, preset, self.hand_smoothed[hand_id], hand_offset
            )
            if result is not None:
                channel, bend = result
                self._send_pitch_bend_raw(channel, bend)

    # ------------------------------------------------------------------
    # Preset switching
    # ------------------------------------------------------------------
    def switch_preset(self, hand_id, preset_idx):
        """
        Change preset for a specific hand.
        Turns off any active note, resets pitch bend, re-initialises filters.
        """
        # 1. Stop any active note
        actions = self.note_engine.stop(hand_id)
        for action in actions:
            if action[0] == 'note_off':
                _, hand, note = action
                self._send_note_off(hand, note)

        # 2. Reset pitch bend on the OLD preset's channel
        old_preset = PRESETS[self.hand_preset[hand_id]]
        hand_offset = self._get_hand_offset(hand_id)
        old_channel = self.pitch_bend.get_channel(old_preset, hand_offset)
        if old_channel is not None:
            self._send_pitch_bend_raw(old_channel, 0)
        self.pitch_bend.reset_hand(hand_id)

        # 3. Apply the new preset
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
        hand_offset = self._get_hand_offset(hand_id)
        channel = min(15, max(0, base_ch + hand_offset))
        msg = mido.Message('note_on', channel=channel, note=note, velocity=velocity)
        self.midi_out.port.send(msg)
        print(f"Note ON: hand{hand_id} ch{channel + 1} note{note}")

    def _send_note_off(self, hand_id, note):
        if self.midi_out is None or not self.midi_out.port:
            return
        preset = PRESETS[self.hand_preset[hand_id]]
        if preset.note_config is None:
            return
        base_ch = preset.note_config['channel']
        hand_offset = self._get_hand_offset(hand_id)
        channel = min(15, max(0, base_ch + hand_offset))
        msg = mido.Message('note_off', channel=channel, note=note, velocity=0)
        self.midi_out.port.send(msg)
        print(f"Note OFF: hand{hand_id} ch{channel + 1} note{note}")

    def _send_pitch_bend_raw(self, channel, bend_value):
        if self.midi_out is None or not self.midi_out.port:
            return
        bend_value = int(round(bend_value))
        bend_value = max(-8192, min(8191, bend_value))
        msg = mido.Message('pitchwheel', channel=channel, pitch=bend_value)
        self.midi_out.port.send(msg)

    def _note_cleanup(self):
        # 1. Turn off any active notes
        actions = self.note_engine.cleanup()
        for action in actions:
            if action[0] == 'note_off':
                _, hand, note = action
                self._send_note_off(hand, note)

        # 2. Reset pitch bend to center on every active preset's bend channel
        for hand_id in (0, 1):
            preset = PRESETS[self.hand_preset[hand_id]]
            if preset.pitch_bend_config is None:
                continue
            hand_offset = self._get_hand_offset(hand_id)
            channel = self.pitch_bend.get_channel(preset, hand_offset)
            if channel is not None:
                self._send_pitch_bend_raw(channel, 0)
        self.pitch_bend.reset()

    def _get_hand_offset(self, hand_id):
        """Return 0 if the preset ignores hand offsets; otherwise the standard offset."""
        preset = PRESETS[self.hand_preset[hand_id]]
        if not preset.apply_channel_offset:
            return 0
        return config.LEFT_HAND_CHANNEL_OFFSET if hand_id == 0 else config.RIGHT_HAND_CHANNEL_OFFSET

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
        h, w = frame.shape[:2]

        # 1. Detect hands
        detected_hands = self._detect_hands(results)

        # 2. Match to tracks + filter + draw
        self._process_detected_hands(detected_hands, frame, w, h)

        # 3. MIDI CC
        messages_to_send = []
        for hand_id in (0, 1):
            preset_idx = self.hand_preset[hand_id]
            if preset_idx == 0:
                continue
            preset = PRESETS[preset_idx]
            hand_offset = self._get_hand_offset(hand_id)
            messages = self.midi_cc.process_hand(
                hand_id, preset, self.hand_smoothed[hand_id], hand_offset
            )
            messages_to_send.extend(messages)
        if messages_to_send:
            self.midi_out.send_messages(messages_to_send)

        # 4. Notes
        self._process_notes()

        # 5. Pitch bend
        self._process_pitch_bend()

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
        cv2.setMouseCallback(self.window_name, self.ui.handle_click)

        try:
            while True:
                frame, results = self.vision.read()
                if frame is None:
                    break

                # Process frame (tracking, MIDI, notes)
                frame = self._process_frame(frame, results)

                # Build the canvas (camera + layout)
                canvas = build_canvas(frame, self.window_name)

                # Build UI state and draw overlays
                midi_status = "MIDI: Active" if self.midi_out.port else "MIDI: Not connected"
                ui_state = {
                    'hand_preset': self.hand_preset,
                    'hand_smoothed': self.hand_smoothed,
                    'hand_note_state': self.hand_note_state,
                    'midi_status': midi_status,
                    'mapper_mode': self.mapper_mode,
                }
                self.ui.draw(canvas, ui_state)

                cv2.imshow(self.window_name, canvas)

                # Keyboard handling
                key = cv2.waitKey(1) & 0xFF
                if key == 27:
                    break
                if key == ord('m'):
                    self.mapper_mode = not self.mapper_mode
                    continue

                # ---- Left hand: number keys 0-9 ----
                if 48 <= key <= 57:
                    idx = key - 48
                    if idx < len(PRESETS):
                        self.switch_preset(0, idx)
                    continue

                # ---- Right hand: Shift+number (symbols) ----
                shift_map = {
                    33: 1,  # !
                    34: 2,  # "
                    167: 3,  # §
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

        finally:
            self._note_cleanup()
            self.vision.release()
            self.midi_out.close()
            cv2.destroyAllWindows()

# ----------------------------------------------------------------------
if __name__ == "__main__":
    app = MotionControllerApp()
    app.run()