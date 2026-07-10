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

# --- Global state for UI ---
active_preset_idx = 0
# The mouse callback will update this variable
def set_active_preset(idx):
    global active_preset_idx
    if idx != active_preset_idx:
        active_preset_idx = idx
        switch_preset(idx)

# --- Functions to manage preset switching ---
filters = {}          # will be re-created per preset
last_smoothed = {}    # per preset
last_midi = {}        # per preset
midi_out = None

def switch_preset(idx):
    """Re-initialize filters and caches for the new preset."""
    global filters, last_smoothed, last_midi
    preset = PRESETS[idx]
    # Create new filter instances for each feature in the preset
    filters.clear()
    for feature, settings in preset.filter_settings.items():
        filters[feature] = OneEuroFilter(
            min_cutoff=settings["min_cutoff"] * config.GLOBAL_CUTOFF_MULTIPLIER,
            beta=settings["beta"] * config.GLOBAL_BETA_MULTIPLIER
        )
    # Reset smoothed values to None (first update will set them)
    last_smoothed = {feature: None for feature in preset.filter_settings.keys()}
    # Reset MIDI deadband cache
    last_midi = {feature: -1 for feature in preset.midi_map.keys()}
    # Optionally send the current (neutral) values? We'll let first frame handle it.

# --- Main ---
def main():
    global active_preset_idx, filters, last_smoothed, last_midi, midi_out

    # Setup vision
    vision = Vision(camera_index=config.CAMERA_INDEX)
    extractor = LandmarkExtractor()

    # MIDI output
    midi_out = MidiOutput(port_name=config.MIDI_PORT_NAME)

    # Initialize first preset
    switch_preset(0)

    # --- Mouse callback for buttons ---
    button_rects = []  # will store (x1, y1, x2, y2, preset_index)

    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            for (x1, y1, x2, y2, idx) in button_rects:
                if x1 <= x <= x2 and y1 <= y <= y2:
                    set_active_preset(idx)
                    break

    cv2.namedWindow("Motion Controller")
    cv2.setMouseCallback("Motion Controller", mouse_callback)

    # --- Main loop ---
    while True:
        frame, results = vision.read()
        if frame is None:
            break

        h, w = frame.shape[:2]
        hand_detected = False

        # Reserve bottom 60 pixels for UI
        ui_height = 60
        frame_ui = frame.copy()
        # Draw the main content on frame_ui, we'll add buttons at bottom

        # --- Process hand if detected ---
        if results and results.multi_hand_landmarks:
            hand_detected = True
            hand = results.multi_hand_landmarks[0]
            vision.drawer.draw_landmarks(
                frame_ui,
                hand,
                vision.mp_hands.HAND_CONNECTIONS,
            )

            landmarks = extractor.get_landmarks(results)
            if landmarks is None:
                # If no landmarks, skip (should not happen if hand detected)
                pass
            else:
                # --- Extract features using the active preset ---
                preset = PRESETS[active_preset_idx]
                raw_features = preset.features_func(landmarks)  # call the method

                # --- Update filters and get smoothed values ---
                for feature, raw_value in raw_features.items():
                    if feature in filters:
                        # Update filter and store smoothed
                        last_smoothed[feature] = filters[feature].update(raw_value)
                    else:
                        # If feature is not filtered, keep raw (shouldn't happen)
                        last_smoothed[feature] = raw_value

        # --- Prepare MIDI messages using the active preset ---
        preset = PRESETS[active_preset_idx]
        messages_to_send = []
        for feature, (channel, cc) in preset.midi_map.items():
            if feature in last_smoothed and last_smoothed[feature] is not None:
                raw = last_smoothed[feature]
                # Normalize using the preset's ranges
                norm_range = preset.norm_ranges.get(feature)
                if norm_range is None:
                    continue
                norm = normalize.normalize_value(raw, norm_range["min"], norm_range["max"])
                midi_val = normalize.midi_value(norm)
                # Deadband check (per preset)
                if abs(midi_val - last_midi[feature]) > preset.deadband * 127:
                    messages_to_send.append((channel, cc, midi_val))
                    last_midi[feature] = midi_val

        # Send MIDI
        if messages_to_send:
            midi_out.send_messages(messages_to_send)

        # --- Draw UI buttons at the bottom ---
        button_rects.clear()
        num_presets = len(PRESETS)
        button_width = w // num_presets
        y_start = h - ui_height
        for i, p in enumerate(PRESETS):
            x1 = i * button_width
            x2 = (i + 1) * button_width
            y1 = y_start
            y2 = h
            # Highlight active preset
            color = (0, 255, 0) if i == active_preset_idx else (100, 100, 100)
            cv2.rectangle(frame_ui, (x1, y1), (x2, y2), color, -1)
            cv2.rectangle(frame_ui, (x1, y1), (x2, y2), (0, 0, 0), 2)
            # Text centered
            text = f"{i+1}: {p.name}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            (tw, th), _ = cv2.getTextSize(text, font, 0.6, 1)
            tx = x1 + (button_width - tw) // 2
            ty = y1 + (ui_height + th) // 2 - 5
            cv2.putText(frame_ui, text, (tx, ty), font, 0.6, (0, 0, 0), 1)
            button_rects.append((x1, y1, x2, y2, i))

        # --- Display info on screen (features, active preset name) ---
        # Show active preset name top-left
        cv2.putText(frame_ui, f"Active: {PRESETS[active_preset_idx].name}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        # Show raw and MIDI values for mapped features (optional)
        y_pos = 60
        for feature in preset.midi_map.keys():
            if feature in last_smoothed and last_smoothed[feature] is not None:
                raw = last_smoothed[feature]
                norm_range = preset.norm_ranges.get(feature)
                if norm_range:
                    norm = normalize.normalize_value(raw, norm_range["min"], norm_range["max"])
                    midi = normalize.midi_value(norm)
                else:
                    norm = 0.0
                    midi = 0
                text = f"{feature}: raw={raw:.2f}  norm={norm:.2f}  midi={midi}"
                cv2.putText(frame_ui, text, (10, y_pos),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                y_pos += 22

        # Status messages
        if not hand_detected:
            cv2.putText(frame_ui, "NO HAND - holding last values", (20, h - ui_height - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        midi_status = "MIDI: Active" if midi_out.port else "MIDI: Not connected"
        cv2.putText(frame_ui, midi_status, (w - 200, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

        # Show shortcut keys hint
        cv2.putText(frame_ui, "Press 1-9 to switch presets", (w - 250, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        cv2.imshow("Motion Controller", frame_ui)

        # --- Keyboard input ---
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            break
        elif 49 <= key <= 57:  # '1' to '9'
            idx = key - 49  # 0-based
            if idx < len(PRESETS):
                set_active_preset(idx)

    # Cleanup
    vision.release()
    midi_out.close()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()