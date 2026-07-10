# main.py
import cv2
from vision import Vision
from landmarks import LandmarkExtractor
from hand_features import HandFeatures
from filters import OneEuroFilter
from midi_output import MidiOutput
from presets import PRESETS
import normalize
import config
from ui import HandControllerUI

# Global state
hand_preset = [0, 0]
hand_filters = [{}, {}]
hand_smoothed = [{}, {}]
hand_last_midi = [{}, {}]

midi_out = None

def init_hand(hand_id):
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
    if preset_idx < 0 or preset_idx >= len(PRESETS):
        return
    hand_preset[hand_id] = preset_idx
    init_hand(hand_id)

def process_hand(hand_id, hand_landmarks, frame, vision):
    preset_idx = hand_preset[hand_id]
    if preset_idx == 0:
        return
    preset = PRESETS[preset_idx]
    # Draw skeleton
    vision.drawer.draw_landmarks(frame, hand_landmarks, vision.mp_hands.HAND_CONNECTIONS)
    # Extract landmarks
    landmarks = [(lm.x, lm.y, lm.z) for lm in hand_landmarks.landmark]
    raw_features = preset.features_func(landmarks)
    for feature, raw_value in raw_features.items():
        if feature in hand_filters[hand_id]:
            hand_smoothed[hand_id][feature] = hand_filters[hand_id][feature].update(raw_value)
        else:
            hand_smoothed[hand_id][feature] = raw_value

def main():
    global midi_out
    vision = Vision(camera_index=config.CAMERA_INDEX)
    midi_out = MidiOutput(port_name=config.MIDI_PORT_NAME)
    for hand_id in (0,1):
        init_hand(hand_id)

    ui = HandControllerUI()

    while True:
        frame, results = vision.read()
        if frame is None:
            break

        # Detect hands
        hands = []
        if results and results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                wrist_x = hand_landmarks.landmark[0].x
                hands.append((wrist_x, hand_landmarks))
            hands.sort(key=lambda t: t[0])
            left_hand = hands[0][1] if len(hands) > 0 else None
            right_hand = hands[1][1] if len(hands) > 1 else None
        else:
            left_hand = right_hand = None

        # Process hands
        if left_hand is not None and hand_preset[0] != 0:
            process_hand(0, left_hand, frame, vision)
        if right_hand is not None and hand_preset[1] != 0:
            process_hand(1, right_hand, frame, vision)

        # Draw UI
        canvas = ui.draw(frame, hand_preset, hand_smoothed, midi_out)

        # Handle UI events (mouse clicks)
        switch = ui.get_pending_switch()
        if switch:
            hand_id, preset_idx = switch
            switch_preset(hand_id, preset_idx)

        # Send MIDI
        messages = []
        for hand_id in (0,1):
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
                        messages.append((channel, cc, midi_val))
                        hand_last_midi[hand_id][feature] = midi_val
        if messages:
            midi_out.send_messages(messages)

        cv2.imshow("Motion Controller", canvas)

        # Keyboard input
        key = cv2.waitKey(1) & 0xFF
        if key == 27:
            break
        # Numbers 1-9 -> left hand
        if 49 <= key <= 57:
            idx = key - 48
            if idx < len(PRESETS):
                switch_preset(0, idx)
        # Shift+numbers -> right hand
        shift_map = {33:1, 64:2, 35:3, 36:4, 37:5, 94:6, 38:7, 42:8, 40:9}
        if key in shift_map:
            idx = shift_map[key]
            if idx < len(PRESETS):
                switch_preset(1, idx)

    vision.release()
    midi_out.close()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()