from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(log_path: str | Path = "history/app.log") -> logging.Logger:
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("locali2v")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
    )
    logger.addHandler(handler)
    return logger
