def slugify(text: str) -> str:
    """Convert human text to a URL slug."""
    return text.lower().replace(" ", "-")
