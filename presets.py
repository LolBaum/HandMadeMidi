# presets.py
import yaml
from hand_features import HandFeatures
from default_presets import DEFAULT_PRESETS_DATA

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


# ----------------------------------------------------------------------
# YAML loader
# ----------------------------------------------------------------------
def load_presets_from_yaml(filepath="presets.yaml"):
    """
    Load presets from a YAML file.
    Returns a list of Preset objects.
    """
    with open(filepath, 'r') as f:
        data = yaml.safe_load(f)

    presets = []
    for item in data:
        # Apply defaults for optional fields
        item.setdefault('deadband', 0.01)
        item.setdefault('mirror_left_hand', True)
        item.setdefault('features', {})
        item.setdefault('note_config', None)

        # Ensure features is a dict
        if not isinstance(item['features'], dict):
            item['features'] = {}

        presets.append(Preset(
            name=item['name'],
            feature_configs=item['features'],
            note_config=item['note_config'],
            deadband=item['deadband'],
            mirror_left_hand=item['mirror_left_hand']
        ))
    return presets

def _presets_from_data(data):
    """Convert a list of dicts (like the YAML structure) into Preset objects."""
    presets = []
    for item in data:
        item.setdefault('deadband', 0.01)
        item.setdefault('mirror_left_hand', True)
        item.setdefault('features', {})
        item.setdefault('note_config', None)
        if not isinstance(item['features'], dict):
            item['features'] = {}
        presets.append(Preset(
            name=item['name'],
            feature_configs=item['features'],
            note_config=item['note_config'],
            deadband=item['deadband'],
            mirror_left_hand=item['mirror_left_hand']
        ))
    return presets

# ----------------------------------------------------------------------
# Load presets – try YAML first, fallback to default data
# ----------------------------------------------------------------------
try:
    PRESETS = load_presets_from_yaml()
    print(f"Loaded {len(PRESETS)} presets from presets.yaml")
except FileNotFoundError:
    print("presets.yaml not found – using fallback default presets.")
    PRESETS = _presets_from_data(DEFAULT_PRESETS_DATA)
except Exception as e:
    print(f"Error loading presets.yaml: {e}. Using fallback default presets.")
    PRESETS = _presets_from_data(DEFAULT_PRESETS_DATA)