import cv2
from vision import Vision
from landmarks import LandmarkExtractor
from hand_features import HandFeatures

# Define the 5 landmarks we care about (for visualization)
PALM_LANDMARKS = [0, 5, 9, 13, 17]  # Wrist, Index MCP, Middle MCP, Ring MCP, Pinky MCP
LANDMARK_NAMES = ["0:Wrist", "1:Idx", "2:Mid", "3:Ring", "4:Pinky"]

vision = Vision()
extractor = LandmarkExtractor()
features = HandFeatures()

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

        # --- Draw the 5 palm landmarks with numbers ---
        for idx, lm_idx in enumerate(PALM_LANDMARKS):
            x = int(landmarks[lm_idx][0] * w)
            y = int(landmarks[lm_idx][1] * h)

            # Draw a bright circle
            cv2.circle(frame, (x, y), 8, (0, 255, 255), -1)

            # Put the number (0, 1, 2, 3, 4) inside the circle
            cv2.putText(frame, str(idx), (x - 6, y + 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

            # Put the name slightly above/right
            cv2.putText(frame, LANDMARK_NAMES[idx], (x + 10, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

        # --- Calculate and display Hand Orientation ---
        orient = features.hand_orientation(landmarks)

        # Display the values on the top-left corner
        y_pos = 30
        for key, value in orient.items():
            text = f"{key}: {value:.2f}"
            cv2.putText(frame, text, (20, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            y_pos += 25

    cv2.imshow("Motion Controller", frame)

    if cv2.waitKey(1) == 27:
        break

vision.release()
cv2.destroyAllWindows()