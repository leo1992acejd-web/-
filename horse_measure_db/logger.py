"""loguru の初期化。"""
from __future__ import annotations

import sys

from loguru import logger

import config


def setup_logger() -> None:
    logger.remove()
    logger.add(sys.stderr, level=config.LOG_LEVEL, colorize=True)
    logger.add(
        config.LOG_DIR / "horse_measure_db_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        rotation="1 day",
        retention="30 days",
        encoding="utf-8",
    )
