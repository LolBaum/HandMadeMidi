# presets.py
import yaml
from hand_features import HandFeatures
from default_presets import DEFAULT_PRESETS_DATA

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
    def __init__(self, name, feature_configs, note_config=None,
                 pitch_bend_config=None, deadband=0.01,
                 mirror_left_hand=True, apply_channel_offset=True):
        self.name = name
        self.feature_configs = feature_configs
        self.features = list(feature_configs.keys())
        self.note_config = note_config
        self.pitch_bend_config = pitch_bend_config
        self.deadband = deadband
        self.mirror_left_hand = mirror_left_hand
        self.apply_channel_offset = apply_channel_offset

    def get_features(self, landmarks):
        result = {}
        for feature in self.features:
            func = FEATURE_FUNCS[feature]
            result.update(func(landmarks))
        return result


def _preset_from_dict(item):
    item.setdefault('deadband', 0.01)
    item.setdefault('mirror_left_hand', True)
    item.setdefault('features', {})
    item.setdefault('note_config', None)
    item.setdefault('pitch_bend', None)
    item.setdefault('apply_channel_offset', True)
    if not isinstance(item['features'], dict):
        item['features'] = {}
    return Preset(
        name=item['name'],
        feature_configs=item['features'],
        note_config=item['note_config'],
        pitch_bend_config=item['pitch_bend'],
        deadband=item['deadband'],
        mirror_left_hand=item['mirror_left_hand'],
        apply_channel_offset=item['apply_channel_offset'],
    )


def load_presets_from_yaml(filepath="presets.yaml"):
    with open(filepath, 'r') as f:
        data = yaml.safe_load(f)
    return [_preset_from_dict(item) for item in data]


def _presets_from_data(data):
    return [_preset_from_dict(item) for item in data]


try:
    PRESETS = load_presets_from_yaml()
    print(f"Loaded {len(PRESETS)} presets from presets.yaml")
except FileNotFoundError:
    print("presets.yaml not found – using fallback default presets.")
    PRESETS = _presets_from_data(DEFAULT_PRESETS_DATA)
except Exception as e:
    print(f"Error loading presets.yaml: {e}. Using fallback default presets.")
    PRESETS = _presets_from_data(DEFAULT_PRESETS_DATA)