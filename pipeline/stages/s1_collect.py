"""Stage 1: Collect context — gather RSS headlines and existing article slugs.

Called once before the batch generation loop.
No slot logic — all articles are generated in one batch.
"""

from __future__ import annotations

import logging

from pipeline.config import CONTENT_DIR
from pipeline.feeds import fetch_rss_headlines

logger = logging.getLogger(__name__)


class AllPostedError(Exception):
    """Kept for backward compatibility."""


def collect_context() -> tuple[list[dict], list[str]]:
    """Collect RSS items and existing article slugs.

    Returns:
        (rss_items, posted_slugs)
    """
    rss_items = fetch_rss_headlines()

    posted_slugs: list[str] = []
    if CONTENT_DIR.exists():
        posted_slugs = [p.stem for p in CONTENT_DIR.glob("*.md")]

    logger.info("Context: %d RSS items, %d existing articles", len(rss_items), len(posted_slugs))
    return rss_items, posted_slugs
