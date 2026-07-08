# config.py
# All adjustable parameters for the hand controller

# ---- One Euro Filter settings ----
# For each tracked parameter, you can set min_cutoff and beta individually
FILTER_SETTINGS = {
    "palm_x":   {"min_cutoff": 0.5, "beta": 0.2},
    "palm_y":   {"min_cutoff": 0.5, "beta": 0.2},
    "palm_z":   {"min_cutoff": 0.5, "beta": 0.2},
    "hand_yaw": {"min_cutoff": 0.5, "beta": 0.2},
    "hand_pitch": {"min_cutoff": 0.5, "beta": 0.2},
    "hand_roll": {"min_cutoff": 0.5, "beta": 0.2},
}

# ---- Normalization ranges (raw min, raw max) ----
# These are the measured useful ranges you provided
NORMALIZATION_RANGES = {
    "hand_pitch": {"min": -70.0, "max": 50.0},   # flat hand fingers to camera → palm facing camera
    "hand_roll":  {"min": -100.0, "max": 180.0}, # ignore values below -100
    # For position parameters, you can set your own ranges later
    "palm_x":     {"min": 0.0, "max": 1.0},      # placeholder – you can measure later
    "palm_y":     {"min": 0.0, "max": 1.0},
    "palm_z":     {"min": 0.0, "max": 1.0},
    "hand_yaw":   {"min": -180.0, "max": 180.0}, # if you ever use it
}

# ---- MIDI mapping ----
# Assign each parameter to a MIDI CC number (0-127)
MIDI_MAP = {
    "hand_pitch": 20,   # e.g., Filter Cutoff
    "hand_roll":  21,   # e.g., Resonance
    "palm_x":     22,   # e.g., Pan
    "palm_y":     23,   # e.g., Reverb Mix
    "palm_z":     24,   # e.g., Volume
    "hand_yaw":   25,   # (optional)
}

# ---- Deadband threshold ----
# Only send MIDI if the normalized value changes by more than this
# (reduces MIDI traffic and zipper noise)
DEADBAND = 0.01  # 1% of the 0-1 range