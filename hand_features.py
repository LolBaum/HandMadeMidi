# hand_features.py
import numpy as np

class HandFeatures:

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
    def finger_spread(landmarks):
        """Returns distance between thumb tip (4) and index tip (8)."""
        thumb_tip = np.array(landmarks[4])
        index_tip = np.array(landmarks[8])
        dist = np.linalg.norm(thumb_tip - index_tip)
        return {"thumb_index_dist": dist}

    @staticmethod
    def hand_fist(landmarks):
        """
        Computes a 'fist' value: average curl of four fingers (index, middle, ring, pinky).
        Uses the angle at the PIP joint (landmark 6,10,14,18) between MCP and TIP.
        Returns value 0..1 where 0 = open, 1 = fully closed.
        """
        # Finger tip and PIP indices
        fingers = [
            (8, 6, 5),   # index: tip, pip, mcp
            (12, 10, 9), # middle
            (16, 14, 13),# ring
            (20, 18, 17) # pinky
        ]
        total_curl = 0.0
        for tip_idx, pip_idx, mcp_idx in fingers:
            tip = np.array(landmarks[tip_idx])
            pip = np.array(landmarks[pip_idx])
            mcp = np.array(landmarks[mcp_idx])
            # Vector from MCP to PIP and from PIP to TIP
            v1 = pip - mcp
            v2 = tip - pip
            # Angle between these two vectors (0 = straight, 180 = fully bent)
            angle = np.arccos(np.clip(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6), -1.0, 1.0))
            # Convert to 0-1: 0 = open (angle ~0), 1 = closed (angle ~π)
            curl = np.clip(angle / np.pi, 0.0, 1.0)
            total_curl += curl
        fist_value = total_curl / 4.0
        return {"fist": fist_value}