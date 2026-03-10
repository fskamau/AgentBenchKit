def retry_delays(attempts: int, base: float = 1.0, cap: float = 8.0) -> list[float]:
    """Backoff delays for repeated attempts."""
    return [min(base * 2**i, cap) for i in range(attempts)]
