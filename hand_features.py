
# hand_features.py
import numpy as np

class HandFeatures:

    @staticmethod
    def palm_x(landmarks):
        middle_mcp = np.array(landmarks[9])
        return {"palm_x": middle_mcp[0]}

    @staticmethod
    def palm_y(landmarks):
        middle_mcp = np.array(landmarks[9])
        # MediaPipe y increases downward (0=top, 1=bottom).
        # Flip it so that moving the hand UP gives a HIGHER value.
        return {"palm_y": 1.0 - middle_mcp[1]}

    @staticmethod
    def index_tip_y(landmarks):
        index_tip = np.array(landmarks[8])
        # Flip y so that moving up gives a HIGHER value (consistent with palm_y)
        return {"index_tip_y": 1.0 - index_tip[1]}

    @staticmethod
    def index_tip_x(landmarks):
        index_tip = np.array(landmarks[8])
        return {"index_tip_x": index_tip[0]}

    @staticmethod
    def hand_pitch(landmarks):
        wrist = np.array(landmarks[0])
        middle_mcp = np.array(landmarks[9])
        forward_vec = middle_mcp - wrist
        norm = np.linalg.norm(forward_vec)
        pitch = np.degrees(np.arcsin(forward_vec[2] / norm)) if norm > 1e-6 else 0.0
        return {"hand_pitch": pitch}

    @staticmethod
    def hand_roll(landmarks):
        index_mcp = np.array(landmarks[5])
        pinky_mcp = np.array(landmarks[17])
        width_vec = pinky_mcp - index_mcp
        roll = np.degrees(np.arctan2(width_vec[1], width_vec[0]))
        return {"hand_roll": roll}

    @staticmethod
    def finger_spread(landmarks):
        wrist = np.array(landmarks[0])
        thumb_tip = np.array(landmarks[4])
        index_tip = np.array(landmarks[8])
        middle_mcp = np.array(landmarks[9])
        hand_scale = np.linalg.norm(middle_mcp - wrist)
        if hand_scale < 1e-6:
            return {"thumb_index_dist": 0.0}
        raw_dist = np.linalg.norm(thumb_tip - index_tip)
        norm_dist = raw_dist / hand_scale
        return {"thumb_index_dist": norm_dist}

    @staticmethod
    def hand_fist(landmarks):
        fingers = [
            (8, 6, 5),
            (12, 10, 9),
            (16, 14, 13),
            (20, 18, 17)
        ]
        total_curl = 0.0
        for tip_idx, pip_idx, mcp_idx in fingers:
            tip = np.array(landmarks[tip_idx])
            pip = np.array(landmarks[pip_idx])
            mcp = np.array(landmarks[mcp_idx])
            v1 = pip - mcp
            v2 = tip - pip
            angle = np.arccos(np.clip(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6), -1.0, 1.0))
            curl = np.clip(angle / np.pi, 0.0, 1.0)
            total_curl += curl
        return {"fist": total_curl / 4.0}

    @staticmethod
    def hand_scale(landmarks):
        wrist = np.array(landmarks[0])
        middle_mcp = np.array(landmarks[9])
        scale = np.linalg.norm(middle_mcp - wrist)
        return {"hand_scale": scale}

    @staticmethod
    def hand_orientation(landmarks):
        """Original method: returns palm xyz, yaw, pitch, roll."""
        wrist = np.array(landmarks[0])
        index_mcp = np.array(landmarks[5])
        middle_mcp = np.array(landmarks[9])
        ring_mcp = np.array(landmarks[13])
        pinky_mcp = np.array(landmarks[17])

        palm_center = (index_mcp + middle_mcp + ring_mcp + pinky_mcp) / 4.0

        forward_vec = middle_mcp - wrist
        yaw = np.degrees(np.arctan2(forward_vec[0], forward_vec[1]))
        norm = np.linalg.norm(forward_vec)
        pitch = np.degrees(np.arcsin(forward_vec[2] / norm)) if norm > 1e-6 else 0.0

        width_vec = pinky_mcp - index_mcp
        roll = np.degrees(np.arctan2(width_vec[1], width_vec[0]))

        return {
            "palm_x": palm_center[0],
            "palm_y": palm_center[1],
            "palm_z": palm_center[2],
            "hand_yaw": yaw,
            "hand_pitch": pitch,
            "hand_roll": roll,
        }

    @staticmethod
    def palm_position(landmarks):
        """Returns only palm x and y (z optional)."""
        # Use middle MCP as palm center (or average of four MCPs)
        middle_mcp = np.array(landmarks[9])
        return {
            "palm_x": middle_mcp[0],
            "palm_y": middle_mcp[1],
        }

    @staticmethod
    def position_and_spread(landmarks):
        """Returns palm_x, palm_y and thumb_index_dist in one dict."""
        pos = HandFeatures.palm_position(landmarks)
        spread = HandFeatures.finger_spread(landmarks)
        return {**pos, **spread}

    @staticmethod
    def position_spread_scale(landmarks):
        """Combine position, spread, and scale for note presets."""
        pos = HandFeatures.palm_position(landmarks)
        spread = HandFeatures.finger_spread(landmarks)
        scale = HandFeatures.hand_scale(landmarks)
        return {**pos, **spread, **scale}