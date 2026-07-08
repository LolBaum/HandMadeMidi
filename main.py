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

        angles = features.finger_angles(landmarks)

        y = 30

        for finger, angle in angles.items():

            text = f"{finger}: {angle:.1f}"

            cv2.putText(
                frame,
                text,
                (20, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )

            y += 30

    cv2.imshow("Motion Controller", frame)

    if cv2.waitKey(1) == 27:
        break

vision.release()
cv2.destroyAllWindows()