# normalize.py
import config


def normalize_value(raw_value, param_name):
    """
    Clamp raw_value to the configured min/max for that parameter,
    then map to 0.0 - 1.0.
    Returns None if parameter not found.
    """
    if param_name not in config.NORMALIZATION_RANGES:
        return None
    min_val = config.NORMALIZATION_RANGES[param_name]["min"]
    max_val = config.NORMALIZATION_RANGES[param_name]["max"]

    # Clamp
    clamped = max(min_val, min(raw_value, max_val))

    # Map to 0-1
    if max_val - min_val == 0:
        return 0.5  # fallback
    normalized = (clamped - min_val) / (max_val - min_val)
    return normalized


def midi_value(normalized):
    """Convert 0-1 to 0-127 integer"""
    return int(round(max(0, min(1, normalized)) * 127))