import cv2
from vision import Vision
from landmarks import LandmarkExtractor
from hand_features import HandFeatures
from filters import OneEuroFilter
from midi_output import MidiOutput
import config
import normalize

# --- Setup ---
vision = Vision()
extractor = LandmarkExtractor()
features = HandFeatures()

# --- MIDI ---
midi_out = MidiOutput(port_name="Motion Controller")

filters = {}
for param, settings in config.FILTER_SETTINGS.items():
    filters[param] = OneEuroFilter(
        min_cutoff=settings["min_cutoff"] * config.GLOBAL_CUTOFF_MULTIPLIER,
        beta=settings["beta"] * config.GLOBAL_BETA_MULTIPLIER
    )

# Store last valid smoothed values
last_smoothed = {
    "palm_x": 0.5,
    "palm_y": 0.5,
    "palm_z": 0.5,
    "hand_yaw": 0.0,
    "hand_pitch": 0.0,
    "hand_roll": 0.0,
}

# Store last MIDI values for deadband
last_midi = {param: -1 for param in config.MIDI_MAP.keys()}

# Visualization landmarks
PALM_LANDMARKS = [0, 5, 9, 13, 17]
LANDMARK_NAMES = ["0:Wrist", "1:Idx", "2:Mid", "3:Ring", "4:Pinky"]

while True:
    frame, results = vision.read()

    if frame is None:
        break

    h, w = frame.shape[:2]
    hand_detected = False

    # --- Process hand if detected ---
    if results and results.multi_hand_landmarks:
        hand_detected = True
        hand = results.multi_hand_landmarks[0]
        vision.drawer.draw_landmarks(
            frame,
            hand,
            vision.mp_hands.HAND_CONNECTIONS,
        )

        landmarks = extractor.get_landmarks(results)

        # Visualize palm points
        for idx, lm_idx in enumerate(PALM_LANDMARKS):
            x = int(landmarks[lm_idx][0] * w)
            y = int(landmarks[lm_idx][1] * h)
            cv2.circle(frame, (x, y), 8, (0, 255, 255), -1)
            cv2.putText(frame, str(idx), (x - 6, y + 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
            cv2.putText(frame, LANDMARK_NAMES[idx], (x + 10, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

        # --- Get raw features and filter ---
        raw_orient = features.hand_orientation(landmarks)
        for key, raw_value in raw_orient.items():
            if key in filters:
                last_smoothed[key] = filters[key].update(raw_value)
            else:
                last_smoothed[key] = raw_value

    # --- Normalize and prepare MIDI messages ---
    messages_to_send = []
    for param, cc in config.MIDI_MAP.items():
        if param in last_smoothed:
            raw = last_smoothed[param]
            norm = normalize.normalize_value(raw, param)
            if norm is not None:
                midi_val = normalize.midi_value(norm)
                # Deadband check
                if abs(midi_val - last_midi[param]) > config.DEADBAND * 127:
                    messages_to_send.append((cc, midi_val))
                    last_midi[param] = midi_val

    # Send MIDI messages
    if messages_to_send:
        midi_out.send_messages(messages_to_send)

    # --- Display values on screen ---
    y_pos = 30
    for param in config.MIDI_MAP.keys():
        if param in last_smoothed:
            raw = last_smoothed[param]
            norm = normalize.normalize_value(raw, param)
            midi = normalize.midi_value(norm) if norm is not None else 0
            text = f"{param}: raw={raw:.1f}  norm={norm:.2f}  midi={midi}"
            cv2.putText(frame, text, (20, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            y_pos += 22

    # Status messages
    if not hand_detected:
        cv2.putText(frame, "NO HAND - holding last values", (20, h - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    midi_status = "MIDI: Active" if midi_out.port else "MIDI: Not connected"
    cv2.putText(frame, midi_status, (w - 200, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

    cv2.imshow("Motion Controller", frame)

    if cv2.waitKey(1) == 27:
        break

# Cleanup
vision.release()
midi_out.close()
cv2.destroyAllWindows()