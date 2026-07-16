# presets.py
from hand_features import HandFeatures

class Preset:
    def __init__(self, name, features_func, midi_map, norm_ranges,
                 filter_settings, deadband=0.01, mirror_left_hand=True,
                 note_config=None):
        self.name = name
        self.features_func = features_func
        self.midi_map = midi_map
        self.norm_ranges = norm_ranges
        self.filter_settings = filter_settings
        self.deadband = deadband
        self.mirror_left_hand = mirror_left_hand
        self.note_config = note_config  # dict: {channel, note_min, note_max, threshold, timeout}

def make_preset(name, method_name, midi_map, norm_ranges, filter_settings,
                deadband=0.01, mirror_left_hand=True, note_config=None):
    method = getattr(HandFeatures, method_name)
    return Preset(name, method, midi_map, norm_ranges, filter_settings,
                  deadband, mirror_left_hand, note_config)

PRESETS = [
    # 0: Off
    Preset("Off", lambda lm: {}, {}, {}, {}, deadband=0.01, mirror_left_hand=False),

    # 1: Pitch/Roll
    make_preset(
        name="Pitch/Roll",
        method_name="hand_orientation",
        midi_map={"hand_pitch": (1, 20), "hand_roll": (1, 21)},
        norm_ranges={"hand_pitch": {"min": -70.0, "max": 50.0},
                     "hand_roll": {"min": -100.0, "max": 180.0}},
        filter_settings={"hand_pitch": {"min_cutoff": 0.5, "beta": 0.2},
                         "hand_roll": {"min_cutoff": 0.5, "beta": 0.2}},
        deadband=0.01,
        mirror_left_hand=True,
    ),

    # 2: Position
    make_preset(
        name="Position",
        method_name="palm_position",
        midi_map={"palm_x": (2, 22), "palm_y": (2, 23)},
        norm_ranges={"palm_x": {"min": 0.1, "max": 0.9},
                     "palm_y": {"min": 0.1, "max": 0.9}},
        filter_settings={"palm_x": {"min_cutoff": 0.3, "beta": 0.1},
                         "palm_y": {"min_cutoff": 0.3, "beta": 0.1}},
        deadband=0.015,
        mirror_left_hand=False,
    ),

    # 3: Finger Spread
    make_preset(
        name="Finger Spread",
        method_name="finger_spread",
        midi_map={"thumb_index_dist": (3, 30)},
        norm_ranges={"thumb_index_dist": {"min": 0.0, "max": 1.2}},
        filter_settings={"thumb_index_dist": {"min_cutoff": 0.4, "beta": 0.15}},
        deadband=0.01,
        mirror_left_hand=True,
    ),

    # 4: Fist
    make_preset(
        name="Fist",
        method_name="hand_fist",
        midi_map={"fist": (4, 40)},
        norm_ranges={"fist": {"min": 0.0, "max": 1.0}},
        filter_settings={"fist": {"min_cutoff": 0.3, "beta": 0.1}},
        deadband=0.01,
        mirror_left_hand=True,
    ),

    # 5: Position + Spread
    make_preset(
        name="Pos+Spread",
        method_name="position_and_spread",
        midi_map={"palm_x": (2, 22), "palm_y": (2, 23), "thumb_index_dist": (3, 30)},
        norm_ranges={"palm_x": {"min": 0.1, "max": 0.9},
                     "palm_y": {"min": 0.1, "max": 0.9},
                     "thumb_index_dist": {"min": 0.0, "max": 1.2}},
        filter_settings={"palm_x": {"min_cutoff": 0.3, "beta": 0.1},
                         "palm_y": {"min_cutoff": 0.3, "beta": 0.1},
                         "thumb_index_dist": {"min_cutoff": 0.4, "beta": 0.15}},
        deadband=0.015,
        mirror_left_hand=False,
    ),

    # 6: Note Generator (NEW)
    make_preset(
        name="Note Gen",
        method_name="position_and_spread",
        midi_map={"palm_x": (1, 1)},  # CC for effect (e.g., modulation)
        norm_ranges={"palm_x": {"min": 0.1, "max": 0.9},
                     "palm_y": {"min": 0.1, "max": 0.9},
                     "thumb_index_dist": {"min": 0.0, "max": 1.2}},
        filter_settings={"palm_x": {"min_cutoff": 0.3, "beta": 0.1},
                         "palm_y": {"min_cutoff": 0.3, "beta": 0.1},
                         "thumb_index_dist": {"min_cutoff": 0.4, "beta": 0.15}},
        deadband=0.015,
        mirror_left_hand=False,
        note_config={
            "channel": 1,           # base channel (will add hand offset)
            "note_min": 12,         #
            "note_max": 103,         #
            "threshold": 0.3,       # distance < threshold => note on
            "timeout": 20.0         # seconds before auto note-off
        }
    ),
]