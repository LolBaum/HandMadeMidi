import numpy as np

class HandFeatures:

    # ... keep your existing angle() and finger_angles() methods ...

    def finger_orientations(self, landmarks):
        """
        Returns the 3D orientation (elevation and azimuth) of each finger.
        Elevation: angle between the finger vector and the XY plane.
                   Positive = pointing towards the camera (Z increases).
                   Negative = pointing away from the camera (Z decreases).
        Azimuth: rotation in the XY plane (like a compass bearing).
        """
        # Define the (MCP, TIP) landmark indices for each finger
        fingers = {
            "thumb": (1, 4),
            "index": (5, 8),
            "middle": (9, 12),
            "ring": (13, 16),
            "pinky": (17, 20),
        }

        orientations = {}

        for name, (mcp_idx, tip_idx) in fingers.items():
            mcp = np.array(landmarks[mcp_idx])
            tip = np.array(landmarks[tip_idx])

            # Vector from MCP to TIP
            vec = tip - mcp
            norm = np.linalg.norm(vec)

            if norm < 1e-6:
                orientations[f"{name}_elevation"] = 0.0
                orientations[f"{name}_azimuth"] = 0.0
                continue

            # Normalize the vector
            vec = vec / norm

            # Elevation (tilt towards/away from camera)
            # arcsin of the Z component gives the angle relative to the XY plane
            elevation = np.degrees(np.arcsin(vec[2]))

            # Azimuth (rotation in the XY plane)
            azimuth = np.degrees(np.arctan2(vec[1], vec[0]))

            orientations[f"{name}_elevation"] = elevation
            orientations[f"{name}_azimuth"] = azimuth

        return orientations