import cv2
import mediapipe as mp


class Vision:

    def __init__(self, camera_index=0):
        self.cap = cv2.VideoCapture(camera_index)

        self.mp_hands = mp.solutions.hands

        self.hands = self.mp_hands.Hands(
            max_num_hands=1,
            model_complexity=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7,
        )

        self.drawer = mp.solutions.drawing_utils

    def read(self):
        success, frame = self.cap.read()

        if not success:
            return None, None

        frame = cv2.flip(frame, 1)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        results = self.hands.process(rgb)

        return frame, results

    def release(self):
        self.cap.release()