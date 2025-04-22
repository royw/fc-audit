"""Logging configuration for fc-audit."""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from fc_audit.path_valid import is_pathname_valid


def setup_logging(log_file: str | None = None, verbose: bool = False) -> None:
    """Configure logging settings.

    Args:
        log_file: Optional path to log file
        verbose: If True, set log level to DEBUG
    """
    level: str = "DEBUG" if verbose else "INFO"

    # Remove default handler
    logger.remove()

    # Add file handler if specified
    if log_file:
        try:
            # Create parent directory if it doesn't exist
            if not is_pathname_valid(log_file):
                error_msg = f"Invalid log file path: {log_file}"
                raise ValueError(error_msg)
            log_path: Path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            logger.add(log_file, rotation="10 MB", level=level)
        except Exception as e:
            # Print error directly to stderr before setting up logger
            print(f"Failed to set up log file: {e}", file=sys.stderr, flush=True)
            # Add stderr handler after error
            logger.add(sys.stderr, colorize=False, level=level)
            # Log startup message
            logger.debug("Starting fc-audit")
            logger.debug(f"Log level: {level}")
            return

    # Add stderr handler
    logger.add(sys.stderr, colorize=False, level=level)

    # Log startup message
    logger.debug("Starting fc-audit")
    logger.debug(f"Log level: {level}")
