def merge_config(defaults: dict, overrides: dict) -> dict:
    """Combine nested configuration dictionaries."""
    merged = dict(defaults)
    merged.update(overrides)
    return merged
