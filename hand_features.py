import numpy as np


class HandFeatures:

    def angle(self, a, b, c):

        a = np.array(a)
        b = np.array(b)
        c = np.array(c)

        ba = a - b
        bc = c - b

        cosine = np.dot(ba, bc)

        cosine /= (
            np.linalg.norm(ba)
            * np.linalg.norm(bc)
        )

        cosine = np.clip(cosine, -1.0, 1.0)

        return np.degrees(np.arccos(cosine))

    def finger_angles(self, landmarks):

        fingers = {}

        fingers["thumb"] = self.angle(
            landmarks[1],
            landmarks[2],
            landmarks[3],
        )

        fingers["index"] = self.angle(
            landmarks[5],
            landmarks[6],
            landmarks[7],
        )

        fingers["middle"] = self.angle(
            landmarks[9],
            landmarks[10],
            landmarks[11],
        )

        fingers["ring"] = self.angle(
            landmarks[13],
            landmarks[14],
            landmarks[15],
        )

        fingers["pinky"] = self.angle(
            landmarks[17],
            landmarks[18],
            landmarks[19],
        )

        return fingers