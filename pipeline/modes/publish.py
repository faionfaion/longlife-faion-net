"""Publish mode: pick best pre-generated article and send to TG.

Mechanical operation -- no LLM calls, just picks the next article
from pre-generated teasers and publishes it.
"""

from __future__ import annotations

import logging

from pipeline.stages import s10_pick_and_publish

logger = logging.getLogger("pipeline")


def run() -> dict | None:
    """Pick the best unpublished article and send its caption to TG.

    Returns a dict with 'slug' and 'msg_id' on success, or None if
    there is nothing to publish.
    """
    logger.info("=== TG Publish mode ===")
    result = s10_pick_and_publish.run()
    if result:
        logger.info("Published to TG: %s (msg %d)", result["slug"], result["msg_id"])
    else:
        logger.info("Nothing to publish to TG")
    return result
