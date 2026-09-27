# pitch_bend.py
from typing import Dict, Optional, Tuple
import normalize


class PitchBendProcessor:
    """
    Builds 14-bit MIDI pitch bend messages from smoothed feature values.
    Independent of note generation and CC messaging.

    Pitch bend is a dedicated MIDI message (not CC), channel-scoped, and
    centered at 0 (range -8192..8191).
    """

    def __init__(self):
        self._last_bend: Dict[int, int] = {}  # hand_id -> last sent bend

    def process_hand(self, hand_id: int, preset,
                     smoothed_features: Dict[str, float],
                     hand_offset: int) -> Optional[Tuple[int, int]]:
        """
        Process one hand's smoothed features and return (channel, bend_value),
        or None if nothing should be sent.
        """
        config = preset.pitch_bend_config
        if config is None:
            return None

        source = config.get("source")
        if source is None:
            return None

        if source not in smoothed_features or smoothed_features[source] is None:
            return None

        feature_cfg = preset.feature_configs.get(source)
        if feature_cfg is None:
            return None

        norm_range = feature_cfg["norm_range"]
        raw = smoothed_features[source]
        norm = normalize.normalize_value(raw, norm_range[0], norm_range[1])

        if config.get("invert", False):
            norm = 1.0 - norm

        # Center at 0.5 → bend = 0. Full sweep → ±8192.
        bend = int(round((norm - 0.5) * 16384))
        bend = max(-8192, min(8191, bend))

        # Deadband against full 14-bit range
        deadband = config.get("deadband", 0.0005)
        last = self._last_bend.get(hand_id)
        if last is not None and abs(bend - last) <= deadband * 16384:
            return None

        self._last_bend[hand_id] = bend

        base_ch = config.get("channel", 1)
        channel = min(15, max(0, base_ch + hand_offset))
        return (channel, bend)

    @staticmethod
    def get_channel(preset, hand_offset: int) -> Optional[int]:
        """Return the pitch bend channel for a preset (used for reset)."""
        if preset.pitch_bend_config is None:
            return None
        base_ch = preset.pitch_bend_config.get("channel", 1)
        return min(15, max(0, base_ch + hand_offset))

    def reset_hand(self, hand_id: int):
        self._last_bend.pop(hand_id, None)

    def reset(self):
        self._last_bend.clear()