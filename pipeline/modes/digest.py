"""Digest mode: compile day's articles into an evening digest and send to TG."""

from __future__ import annotations

import logging

from pipeline.stages import s11_digest

logger = logging.getLogger("pipeline")


def run() -> dict | None:
    """Compile today's published articles into a digest and send to TG.

    Returns a dict with 'msg_id' and 'article_count' on success,
    or None if there are not enough articles for a digest.
    """
    logger.info("=== Digest mode ===")
    result = s11_digest.run()
    if result:
        logger.info("Digest published (msg %d, %d articles)",
                     result["msg_id"], result["article_count"])
    else:
        logger.info("Digest skipped (not enough articles)")
    return result
