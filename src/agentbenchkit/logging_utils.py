"""Single-point structured logging setup."""

import json
import logging


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({"level": record.levelname, "logger": record.name,
                           "message": record.getMessage()}, sort_keys=True)


def configure_logging(verbose: bool = False) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.DEBUG if verbose else logging.WARNING,
                        handlers=[handler], force=True)
