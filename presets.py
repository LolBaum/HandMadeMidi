# presets.py
from hand_features import HandFeatures

class Preset:
    def __init__(self, name, features_func, midi_map, norm_ranges,
                 filter_settings, deadband=0.01, mirror_left_hand=True):
        self.name = name
        self.features_func = features_func
        self.midi_map = midi_map
        self.norm_ranges = norm_ranges
        self.filter_settings = filter_settings
        self.deadband = deadband
        self.mirror_left_hand = mirror_left_hand   # <-- new flag

def make_preset(name, method_name, midi_map, norm_ranges, filter_settings,
                deadband=0.01, mirror_left_hand=True):
    method = getattr(HandFeatures, method_name)
    return Preset(name, method, midi_map, norm_ranges, filter_settings,
                  deadband, mirror_left_hand)

PRESETS = [
    # 0: Off
    Preset("Off", lambda lm: {}, {}, {}, {}, deadband=0.01, mirror_left_hand=False),

    # 1: Pitch/Roll (mirror enabled)
    make_preset(
        name="Pitch/Roll",
        method_name="hand_orientation",
        midi_map={"hand_pitch": (1, 20), "hand_roll": (1, 21)},
        norm_ranges={"hand_pitch": {"min": -70.0, "max": 50.0},
                     "hand_roll": {"min": -100.0, "max": 180.0}},
        filter_settings={"hand_pitch": {"min_cutoff": 0.5, "beta": 0.2},
                         "hand_roll": {"min_cutoff": 0.5, "beta": 0.2}},
        deadband=0.01,
        mirror_left_hand=True,   # mirror for symmetry
    ),

    # 2: Position (mirror disabled – absolute screen position)
    make_preset(
        name="Position",
        method_name="palm_position",
        midi_map={"palm_x": (2, 22), "palm_y": (2, 23)},
        norm_ranges={"palm_x": {"min": 0.1, "max": 0.9},
                     "palm_y": {"min": 0.1, "max": 0.9}},
        filter_settings={"palm_x": {"min_cutoff": 0.3, "beta": 0.1},
                         "palm_y": {"min_cutoff": 0.3, "beta": 0.1}},
        deadband=0.015,
        mirror_left_hand=False,   # do NOT mirror – keep absolute position
    ),

    # Preset 3: Finger Spread (normalised)
    make_preset(
        name="Finger Spread",
        method_name="finger_spread",
        midi_map={"thumb_index_dist": (3, 30)},
        norm_ranges={"thumb_index_dist": {"min": 0.2, "max": 1.2}},
        filter_settings={"thumb_index_dist": {"min_cutoff": 0.4, "beta": 0.15}},
        deadband=0.01,
        mirror_left_hand=True,
    ),
    # 4: Fist (mirror enabled)
    make_preset(
        name="Fist",
        method_name="hand_fist",
        midi_map={"fist": (4, 40)},
        norm_ranges={"fist": {"min": 0.0, "max": 1.0}},
        filter_settings={"fist": {"min_cutoff": 0.3, "beta": 0.1}},
        deadband=0.01,
        mirror_left_hand=True,
    ),
]