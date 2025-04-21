"""Test configuration and fixtures."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from loguru import logger


@pytest.fixture(autouse=True)
def disable_logging() -> Generator[None, None, None]:
    """Disable logging during tests."""
    logger.remove()
    yield
    logger.add(lambda _: None)  # Add a no-op handler
