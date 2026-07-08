import cv2
from vision import Vision
from landmarks import LandmarkExtractor
from hand_features import HandFeatures
from filters import OneEuroFilter
import config
import normalize

# --- Setup ---
vision = Vision()
extractor = LandmarkExtractor()
features = HandFeatures()

# Create filters using settings from config
filters = {}
for param, settings in config.FILTER_SETTINGS.items():
    filters[param] = OneEuroFilter(
        min_cutoff=settings["min_cutoff"],
        beta=settings["beta"]
    )

# Store the last valid smoothed values (to hold when hand lost)
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

    # Get frame dimensions (always available)
    h, w = frame.shape[:2]

    # --- Process hand if detected ---
    hand_detected = False
    if results and results.multi_hand_landmarks:
        hand_detected = True
        hand = results.multi_hand_landmarks[0]
        vision.drawer.draw_landmarks(
            frame,
            hand,
            vision.mp_hands.HAND_CONNECTIONS,
        )

        landmarks = extractor.get_landmarks(results)

        # Visualize the 5 palm points
        for idx, lm_idx in enumerate(PALM_LANDMARKS):
            x = int(landmarks[lm_idx][0] * w)
            y = int(landmarks[lm_idx][1] * h)
            cv2.circle(frame, (x, y), 8, (0, 255, 255), -1)
            cv2.putText(frame, str(idx), (x - 6, y + 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
            cv2.putText(frame, LANDMARK_NAMES[idx], (x + 10, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

        # --- Get raw features ---
        raw_orient = features.hand_orientation(landmarks)

        # --- Apply filters ---
        for key, raw_value in raw_orient.items():
            if key in filters:
                last_smoothed[key] = filters[key].update(raw_value)
            else:
                last_smoothed[key] = raw_value

    # If hand is lost, last_smoothed retains previous values (no change)

    # --- Normalize and prepare MIDI (just display for now) ---
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

    # Show status if hand lost
    if not hand_detected:
        cv2.putText(frame, "NO HAND - holding last values", (20, h - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    cv2.imshow("Motion Controller", frame)

    if cv2.waitKey(1) == 27:
        break

vision.release()
cv2.destroyAllWindows()