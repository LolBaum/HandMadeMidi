# normalize.py
def normalize_value(raw_value, min_val, max_val):
    """Clamp raw to [min, max] and map to 0.0-1.0."""
    clamped = max(min_val, min(raw_value, max_val))
    if max_val - min_val == 0:
        return 0.5
    return (clamped - min_val) / (max_val - min_val)

def midi_value(normalized):
    """Convert 0-1 to 0-127 integer."""
    return int(round(max(0, min(1, normalized)) * 127))