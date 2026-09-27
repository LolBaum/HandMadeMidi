# midi_cc.py
from typing import List, Tuple, Dict, Any
import normalize


class MidiCCProcessor:
    """
    Builds MIDI Control Change messages from smoothed feature values.
    Applies per‑feature deadband filtering.
    """

    def __init__(self):
        # Stores the last sent MIDI value for each (hand_id, feature)
        self._last_midi = {}  # key: (hand_id, feature) -> last_sent_value

    def process_hand(self, hand_id: int, preset, smoothed_features: Dict[str, float],
                     hand_offset: int) -> List[Tuple[int, int, int]]:
        """
        Process one hand's smoothed features and return a list of (channel, cc, value) messages.
        """
        messages = []
        for feature in preset.features:
            feature_cfg = preset.feature_configs[feature]
            midi_info = feature_cfg["midi"]
            if midi_info is None:
                continue
            base_ch, cc = midi_info

            if feature not in smoothed_features or smoothed_features[feature] is None:
                continue

            raw = smoothed_features[feature]
            norm_range = feature_cfg["norm_range"]
            norm = normalize.normalize_value(raw, norm_range[0], norm_range[1])

            # Apply invert if configured on the feature
            if feature_cfg.get("invert", False):
                norm = 1.0 - norm

            midi_val = normalize.midi_value(norm)

            key = (hand_id, feature)
            last_val = self._last_midi.get(key, -1)
            if abs(midi_val - last_val) > preset.deadband * 127:
                actual_channel = min(15, max(0, base_ch + hand_offset))
                messages.append((actual_channel, cc, midi_val))
                self._last_midi[key] = midi_val

        return messages

    def reset(self):
        """Clear the last-sent cache (useful when changing presets)."""
        self._last_midi.clear()

    def reset_hand(self, hand_id: int):
        """Clear the last-sent cache for a specific hand."""
        keys_to_remove = [k for k in self._last_midi if k[0] == hand_id]
        for k in keys_to_remove:
            del self._last_midi[k]