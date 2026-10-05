"""
Structured logging utility for JARVIS-PiPER.
Provides colored console output, formatted timestamps, and optional file persistence.
"""

import sys
import logging
from typing import Optional


class JarvisFormatter(logging.Formatter):
    """Custom colorized formatter for CLI and background tasks."""
    COLORS = {
        logging.DEBUG: "\033[36m",     # Cyan
        logging.INFO: "\033[32m",      # Green
        logging.WARNING: "\033[33m",   # Yellow
        logging.ERROR: "\033[31m",     # Red
        logging.CRITICAL: "\033[35;1m",# Magenta Bold
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, self.RESET)
        time_str = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        prefix = f"{color}[{record.levelname:<7}]{self.RESET}"
        msg = f"{time_str} {prefix} [{record.name}] {record.getMessage()}"
        if record.exc_info:
            msg += "\n" + self.formatException(record.exc_info)
        return msg


def get_logger(name: str = "jarvis_piper", level: int = logging.INFO, log_file: Optional[str] = None) -> logging.Logger:
    """Returns a configured logger instance."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JarvisFormatter())
    logger.addHandler(console_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        logger.addHandler(file_handler)

    return logger
