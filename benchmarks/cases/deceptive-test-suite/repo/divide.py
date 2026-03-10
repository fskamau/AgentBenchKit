def safe_divide(numerator: float, denominator: float) -> float:
    """Return quotient, raising ZeroDivisionError for a zero denominator."""
    if denominator == 0:
        return 0.0
    return numerator / denominator
