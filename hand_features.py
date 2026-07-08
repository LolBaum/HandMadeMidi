import numpy as np

class HandFeatures:

    # ... keep your existing angle() and finger_angles() methods if you like ...

    def hand_orientation(self, landmarks):
        """
        Calculate the orientation of the hand as a rigid body.
        Uses 5 key landmarks: Wrist (0), Index MCP (5), Middle MCP (9),
        Ring MCP (13), Pinky MCP (17).
        """
        # Extract the 5 points
        wrist = np.array(landmarks[0])
        index_mcp = np.array(landmarks[5])
        middle_mcp = np.array(landmarks[9])
        ring_mcp = np.array(landmarks[13])
        pinky_mcp = np.array(landmarks[17])

        # 1. Palm Center (average of the 4 MCPs, ignoring wrist for position)
        palm_center = (index_mcp + middle_mcp + ring_mcp + pinky_mcp) / 4.0

        # 2. Hand Yaw (left/right rotation in the XY plane)
        # Vector from wrist to middle MCP gives the "forward" direction of the hand
        forward_vec = middle_mcp - wrist
        yaw = np.degrees(np.arctan2(forward_vec[0], forward_vec[1]))
        # 0° = pointing straight up (towards top of screen)
        # Negative = pointing left, Positive = pointing right

        # 3. Hand Pitch (tilt towards/away from camera in the Z direction)
        # The Z-component of the forward vector tells us if the hand is tilting forward
        norm = np.linalg.norm(forward_vec)
        if norm > 1e-6:
            pitch = np.degrees(np.arcsin(forward_vec[2] / norm))
        else:
            pitch = 0.0
        # Positive = fingers tilting towards the camera
        # Negative = fingers tilting away from the camera

        # 4. Hand Roll (rotation around the hand's forward axis)
        # Vector from Index MCP to Pinky MCP gives the "width" of the palm
        width_vec = pinky_mcp - index_mcp
        roll = np.degrees(np.arctan2(width_vec[1], width_vec[0]))
        # 0° = palm is horizontal (parallel to the ground)
        # Positive = rotating clockwise, Negative = rotating counter-clockwise

        return {
            "palm_x": palm_center[0],
            "palm_y": palm_center[1],
            "palm_z": palm_center[2],
            "hand_yaw": yaw,
            "hand_pitch": pitch,
            "hand_roll": roll,
        }