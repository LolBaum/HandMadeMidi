# default_presets.py
DEFAULT_PRESETS_DATA = [
    {"name": "Off", "features": {}, "note_config": None, "pitch_bend": None,
     "deadband": 0.01, "mirror_left_hand": False, "apply_channel_offset": True},

    {"name": "Pitch/Roll", "features": {
        "hand_pitch": {"midi": [1, 20], "norm_range": [-70, 50], "filter": [0.5, 0.2]},
        "hand_roll":  {"midi": [1, 21], "norm_range": [-100, 180], "filter": [0.5, 0.2]},
     }, "note_config": None, "pitch_bend": None,
     "deadband": 0.01, "mirror_left_hand": True, "apply_channel_offset": True},

    {"name": "Position", "features": {
        "palm_x": {"midi": [2, 22], "norm_range": [0.1, 0.9], "filter": [0.3, 0.1]},
        "palm_y": {"midi": [2, 23], "norm_range": [0.1, 0.9], "filter": [0.3, 0.1]},
     }, "note_config": None, "pitch_bend": None,
     "deadband": 0.015, "mirror_left_hand": False, "apply_channel_offset": True},

    {"name": "Finger Spread", "features": {
        "thumb_index_dist": {"midi": [3, 30], "norm_range": [0.0, 1.2], "filter": [0.4, 0.15]},
     }, "note_config": None, "pitch_bend": None,
     "deadband": 0.01, "mirror_left_hand": True, "apply_channel_offset": True},

    {"name": "Fist", "features": {
        "fist": {"midi": [4, 40], "norm_range": [0.0, 1.0], "filter": [0.3, 0.1]},
     }, "note_config": None, "pitch_bend": None,
     "deadband": 0.01, "mirror_left_hand": True, "apply_channel_offset": True},

    {"name": "Multi", "features": {
        "hand_scale":       {"midi": [1, 1],  "norm_range": [0.1, 0.4],  "filter": [0.3, 0.1]},
        "hand_pitch":       {"midi": [1, 20], "norm_range": [-20, 20],   "filter": [0.01, 0.01]},
        "hand_roll":        {"midi": [1, 21], "norm_range": [-90, 90],   "filter": [0.01, 0.01]},
        "palm_x":           {"midi": [2, 22], "norm_range": [0.2, 0.8],  "filter": [0.3, 0.1]},
        "palm_y":           {"midi": [2, 23], "norm_range": [0.2, 0.8],  "filter": [0.3, 0.1]},
        "thumb_index_dist":{"midi": [2, 24], "norm_range": [0.15, 1.4], "filter": [0.5, 0.5]},
        "fist":             {"midi": [4, 40], "norm_range": [0.05, 0.7], "filter": [0.3, 0.1]},
     }, "note_config": None, "pitch_bend": None,
     "deadband": 0.015, "mirror_left_hand": False, "apply_channel_offset": True},

    {"name": "Note Gen", "features": {
        "hand_scale":       {"midi": [1, 1],  "norm_range": [0.1, 0.25], "filter": [0.2, 0.05]},
        "hand_pitch":       {"midi": [1, 20], "norm_range": [-20, 20],   "filter": [0.01, 0.01]},
        "hand_roll":        {"midi": [1, 21], "norm_range": [-90, 90],   "filter": [0.01, 0.01]},
        "palm_x":           {"midi": [2, 22], "norm_range": [0.2, 0.8],  "filter": [0.3, 0.1]},
        "palm_y":           {"midi": [2, 23], "norm_range": [0.2, 0.8],  "filter": [0.3, 0.1]},
        "thumb_index_dist":{"midi": [2, 24], "norm_range": [0.0, 0.4],  "filter": [0.5, 0.5]},
        "fist":             {"midi": [4, 40], "norm_range": [0.05, 0.7], "filter": [0.3, 0.1]},
     },
     "note_config": {
        "channel": 1, "note_min": 12, "note_max": 103,
        "threshold": 0.5, "timeout": 20.0,
        "note_source": "palm_y", "gate_source": "thumb_index_dist",
     },
     "pitch_bend": {"source": "palm_x", "channel": 1, "deadband": 0.0005, "invert": False},
     "deadband": 0.015, "mirror_left_hand": False, "apply_channel_offset": True},

    {"name": "Theremin Volume", "features": {
        "palm_y": {"midi": [1, 11], "norm_range": [0.3, 0.8], "filter": [0.5, 0.2], "invert": True},
    }, "note_config": None, "pitch_bend": None,
     "deadband": 0.005, "mirror_left_hand": True, "apply_channel_offset": False},

    {"name": "Theremin Pitch", "features": {
        "palm_y": {"midi": None, "norm_range": [0.3, 0.8], "filter": [0.5, 0.2], "invert": True},
    }, "note_config": None,
     "pitch_bend": {"source": "palm_y", "channel": 1, "deadband": 0.0005, "invert": False},
     "deadband": 0.005, "mirror_left_hand": True, "apply_channel_offset": False}
]