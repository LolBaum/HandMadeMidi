import cv2
from vision import Vision
from landmarks import LandmarkExtractor
from hand_features import HandFeatures

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

        # Get both angle types
        flexion_angles = features.finger_orientations(landmarks)
        orientation_angles = features.finger_orientations(landmarks)

        # Display Flexion angles (top left)
        y = 30
        for finger, angle in flexion_angles.items():
            text = f"Flex {finger}: {angle:.1f}"
            cv2.putText(frame, text, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            y += 25

        # Display Orientation angles (top right, or below flexion)
        y = 30
        for name, angle in orientation_angles.items():
            text = f"Orient {name}: {angle:.1f}"
            cv2.putText(frame, text, (frame.shape[1] // 2, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            y += 25

    cv2.imshow("Motion Controller", frame)

    if cv2.waitKey(1) == 27:
        break

vision.release()
cv2.destroyAllWindows()