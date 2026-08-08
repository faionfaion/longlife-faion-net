"""Digest mode: write the week as one long post and put it on the site.

Runs Sunday morning. The result is a normal article as far as everything downstream is
concerned, so the day's publish sends it to the channel like any other post — which is why
Sunday needs no separate slot and the blog still puts out exactly one thing a day.
"""

from __future__ import annotations

import logging

from pipeline.stages import s11_digest

logger = logging.getLogger("pipeline")


def run() -> dict | None:
    """Write and publish the week's digest, or None if the week was too thin."""
    logger.info("=== Weekly digest ===")
    result = s11_digest.run()
    if result:
        logger.info(
            "Digest written: %s (%d posts, %d news items) — %s",
            result["slug"], result["post_count"], result["news_count"], result["url"],
        )
    else:
        logger.info("Digest skipped (not enough posts this week)")
    return result
