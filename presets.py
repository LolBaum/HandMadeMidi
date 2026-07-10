# presets.py
from hand_features import HandFeatures

class Preset:
    """
    A preset bundles everything needed for one mapping:
    - name: display name
    - features_func: callable(landmarks) -> dict of raw feature values
    - midi_map: {feature_name: (channel, cc)}
    - norm_ranges: {feature_name: {"min": float, "max": float}}
    - filter_settings: {feature_name: {"min_cutoff": float, "beta": float}}
    - deadband: float (optional, per‑preset deadband)
    """
    def __init__(self, name, features_func, midi_map, norm_ranges,
                 filter_settings, deadband=0.01):
        self.name = name
        self.features_func = features_func
        self.midi_map = midi_map
        self.norm_ranges = norm_ranges
        self.filter_settings = filter_settings
        self.deadband = deadband

# Helper to create a preset using a specific method of HandFeatures
def make_preset(name, method_name, midi_map, norm_ranges, filter_settings, deadband=0.01):
    """Creates a preset that calls HandFeatures.method_name(landmarks)."""
    method = getattr(HandFeatures, method_name)
    return Preset(name, method, midi_map, norm_ranges, filter_settings, deadband)

# ---- Define all available presets ----
PRESETS = [
    # Preset 1: Pitch and Roll (original behaviour)
    make_preset(
        name="Pitch/Roll",
        method_name="hand_orientation",
        midi_map={
            "hand_pitch": (1, 20),   # channel 1, CC 20
            "hand_roll":  (1, 21),
        },
        norm_ranges={
            "hand_pitch": {"min": -70.0, "max": 50.0},
            "hand_roll":  {"min": -100.0, "max": 180.0},
            # palm values are also returned but not mapped here
        },
        filter_settings={
            "hand_pitch": {"min_cutoff": 0.5, "beta": 0.2},
            "hand_roll":  {"min_cutoff": 0.5, "beta": 0.2},
        },
        deadband=0.01,
    ),

    # Preset 2: Hand Position (palm center X and Y)
    make_preset(
        name="Position",
        method_name="palm_position",   # we'll add this method later
        midi_map={
            "palm_x": (2, 22),         # channel 2, CC 22
            "palm_y": (2, 23),
        },
        norm_ranges={
            "palm_x": {"min": 0.1, "max": 0.9},
            "palm_y": {"min": 0.1, "max": 0.9},
        },
        filter_settings={
            "palm_x": {"min_cutoff": 0.3, "beta": 0.1},
            "palm_y": {"min_cutoff": 0.3, "beta": 0.1},
        },
        deadband=0.015,
    ),

    # Preset 3: Finger Spread (distance between thumb and index)
    make_preset(
        name="Finger Spread",
        method_name="finger_spread",
        midi_map={
            "thumb_index_dist": (3, 30),
        },
        norm_ranges={
            "thumb_index_dist": {"min": 0.0, "max": 0.3},  # raw distance in normalized coords
        },
        filter_settings={
            "thumb_index_dist": {"min_cutoff": 0.4, "beta": 0.15},
        },
        deadband=0.01,
    ),

    # Preset 4: Fist (percentage of curled fingers)
    make_preset(
        name="Fist",
        method_name="hand_fist",
        midi_map={
            "fist": (4, 40),
        },
        norm_ranges={
            "fist": {"min": 0.0, "max": 1.0},
        },
        filter_settings={
            "fist": {"min_cutoff": 0.3, "beta": 0.1},
        },
        deadband=0.01,
    ),
]