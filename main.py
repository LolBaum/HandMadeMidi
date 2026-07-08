import cv2
from vision import Vision
from landmarks import LandmarkExtractor
from hand_features import HandFeatures
from filters import OneEuroFilter  # You can swap to ExponentialSmoothing if you prefer

# --- Setup ---
vision = Vision()
extractor = LandmarkExtractor()
features = HandFeatures()

# Create a filter for each tracked parameter
# Tune these parameters to your liking:
# - min_cutoff: 0.5 = smooth, 2.0 = responsive
# - beta: 0.0 = stable, 0.5 = follows fast motion better
filters = {
    "palm_x": OneEuroFilter(min_cutoff=0.5, beta=0.2),
    "palm_y": OneEuroFilter(min_cutoff=0.5, beta=0.2),
    "palm_z": OneEuroFilter(min_cutoff=0.5, beta=0.2),
    "hand_yaw": OneEuroFilter(min_cutoff=0.5, beta=0.2),
    "hand_pitch": OneEuroFilter(min_cutoff=0.5, beta=0.2),
    "hand_roll": OneEuroFilter(min_cutoff=0.5, beta=0.2),
}

# The 5 landmarks we visualize
PALM_LANDMARKS = [0, 5, 9, 13, 17]
LANDMARK_NAMES = ["0:Wrist", "1:Idx", "2:Mid", "3:Ring", "4:Pinky"]

while True:
    frame, results = vision.read()

    if frame is None:
        break

    if results.multi_hand_landmarks:
        hand = results.multi_hand_landmarks[0]
        vision.drawer.draw_landmarks(
            frame,
            hand,
            vision.mp_hands.HAND_CONNECTIONS,
        )

        landmarks = extractor.get_landmarks(results)
        h, w, _ = frame.shape

        # --- Visualize the 5 palm points with numbers ---
        for idx, lm_idx in enumerate(PALM_LANDMARKS):
            x = int(landmarks[lm_idx][0] * w)
            y = int(landmarks[lm_idx][1] * h)
            cv2.circle(frame, (x, y), 8, (0, 255, 255), -1)
            cv2.putText(frame, str(idx), (x - 6, y + 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
            cv2.putText(frame, LANDMARK_NAMES[idx], (x + 10, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

        # --- Calculate raw features ---
        raw_orient = features.hand_orientation(landmarks)

        # --- Apply filters to every parameter ---
        smoothed_orient = {}
        for key, raw_value in raw_orient.items():
            if key in filters:
                smoothed_orient[key] = filters[key].update(raw_value)
            else:
                smoothed_orient[key] = raw_value  # fallback

        # --- Display the smoothed values ---
        y_pos = 30
        for key, value in smoothed_orient.items():
            # Show both raw and smoothed? Let's just show smoothed with a marker
            raw_val = raw_orient.get(key, 0)
            text = f"{key}: {value:.2f} (raw: {raw_val:.2f})"
            cv2.putText(frame, text, (20, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            y_pos += 22

        # Optional: Display filter info
        cv2.putText(frame, "One Euro Filter active", (20, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

    cv2.imshow("Motion Controller", frame)

    if cv2.waitKey(1) == 27:  # ESC key
        break

vision.release()
cv2.destroyAllWindows()