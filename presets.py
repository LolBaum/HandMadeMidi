# presets.py
from hand_features import HandFeatures

# Mapping from feature name to its extracting function
FEATURE_FUNCS = {
    "palm_x": HandFeatures.palm_x,
    "palm_y": HandFeatures.palm_y,
    "hand_pitch": HandFeatures.hand_pitch,
    "hand_roll": HandFeatures.hand_roll,
    "thumb_index_dist": HandFeatures.finger_spread,
    "fist": HandFeatures.hand_fist,
    "hand_scale": HandFeatures.hand_scale,
}

class Preset:
    def __init__(self, name, feature_configs, note_config=None, deadband=0.01, mirror_left_hand=True):
        """
        feature_configs: dict { feature_name: { "midi": (channel, cc) or None,
                                                 "norm_range": (min, max),
                                                 "filter": (min_cutoff, beta) } }
        note_config: dict with keys: channel, note_min, note_max, threshold, timeout,
                                     note_source, bend_source, gate_source
        """
        self.name = name
        self.feature_configs = feature_configs
        self.features = list(feature_configs.keys())
        self.note_config = note_config
        self.deadband = deadband
        self.mirror_left_hand = mirror_left_hand

    def get_features(self, landmarks):
        """Return a dict of raw feature values for all features in this preset."""
        result = {}
        for feature in self.features:
            func = FEATURE_FUNCS[feature]
            result.update(func(landmarks))
        return result


def feature_config(midi=None, norm_range=(0.0, 1.0), filter=(0.3, 0.1)):
    """Helper to build a feature configuration dict."""
    return {"midi": midi, "norm_range": norm_range, "filter": filter}


# The preset list – now fully modular
PRESETS = [
    # 0: Off
    Preset("Off", {}, note_config=None, deadband=0.01, mirror_left_hand=False),

    # 1: Pitch/Roll
    Preset("Pitch/Roll", {
        "hand_pitch": feature_config(midi=(1, 20), norm_range=(-70, 50), filter=(0.5, 0.2)),
        "hand_roll": feature_config(midi=(1, 21), norm_range=(-100, 180), filter=(0.5, 0.2)),
    }, note_config=None, deadband=0.01, mirror_left_hand=True),

    # 2: Position
    Preset("Position", {
        "palm_x": feature_config(midi=(2, 22), norm_range=(0.1, 0.9), filter=(0.3, 0.1)),
        "palm_y": feature_config(midi=(2, 23), norm_range=(0.1, 0.9), filter=(0.3, 0.1)),
    }, note_config=None, deadband=0.015, mirror_left_hand=False),

    # 3: Finger Spread
    Preset("Finger Spread", {
        "thumb_index_dist": feature_config(midi=(3, 30), norm_range=(0.0, 1.2), filter=(0.4, 0.15)),
    }, note_config=None, deadband=0.01, mirror_left_hand=True),

    # 4: Fist
    Preset("Fist", {
        "fist": feature_config(midi=(4, 40), norm_range=(0.0, 1.0), filter=(0.3, 0.1)),
    }, note_config=None, deadband=0.01, mirror_left_hand=True),

    # 5: Position + Spread
    Preset("Pos+Spread", {
        "palm_x": feature_config(midi=(2, 22), norm_range=(0.1, 0.9), filter=(0.3, 0.1)),
        "palm_y": feature_config(midi=(2, 23), norm_range=(0.1, 0.9), filter=(0.3, 0.1)),
        "thumb_index_dist": feature_config(midi=(3, 30), norm_range=(0.0, 1.2), filter=(0.4, 0.15)),
    }, note_config=None, deadband=0.015, mirror_left_hand=False),

    # 6: Note Generator (modular)
    Preset("Note Gen", {
        # hand_scale is mapped to CC1 (mod wheel)
        "hand_scale": feature_config(midi=(1, 1), norm_range=(0.1, 0.25), filter=(0.2, 0.05)),
        # these features are used only for note generation – no direct MIDI CC
        "palm_x": feature_config(midi=(2, 22), norm_range=(0.2, 0.8), filter=(0.3, 0.1)),
        "palm_y": feature_config(midi=(2, 23), norm_range=(0.2, 0.8), filter=(0.3, 0.1)),
        "thumb_index_dist": feature_config(midi=(2,24), norm_range=(0.0, 0.3), filter=(0.4, 0.15)),
    }, note_config={
        "channel": 1,
        "note_min": 12,
        "note_max": 103,
        "threshold": 0.3,
        "timeout": 20.0,
        "note_source": "palm_y",
        "bend_source": "palm_x",
        "gate_source": "thumb_index_dist",
    }, deadband=0.015, mirror_left_hand=False),
]