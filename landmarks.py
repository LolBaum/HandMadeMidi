class LandmarkExtractor:

    def get_landmarks(self, results):

        if not results.multi_hand_landmarks:
            return None

        hand = results.multi_hand_landmarks[0]

        landmarks = []

        for lm in hand.landmark:
            landmarks.append((lm.x, lm.y, lm.z))

        return landmarks