"""Stage 8: Verify — check that the deployed article is accessible."""

from __future__ import annotations

import logging
from urllib.request import urlopen, Request
from urllib.error import URLError

from pipeline.config import SITE_BASE_URL
from pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


def run(ctx: PipelineContext) -> None:
    url = f"{SITE_BASE_URL}/{ctx.slug}/"

    try:
        req = Request(url, headers={"User-Agent": "LongLifeVerify/1.0"})
        with urlopen(req, timeout=30) as resp:
            status = resp.status
            body = resp.read().decode("utf-8", errors="replace")

        if status == 200 and ctx.title[:20] in body:
            ctx.site_ok = True
            logger.info("Site verified: %s (200 OK, title found)", url)
        elif status == 200:
            ctx.site_ok = True
            logger.warning("Site returned 200 but title not found in body: %s", url)
        else:
            ctx.site_ok = False
            logger.error("Site returned status %d: %s", status, url)

    except URLError as e:
        ctx.site_ok = False
        logger.error("Site verification failed: %s — %s", url, e)
    except Exception:
        ctx.site_ok = False
        logger.error("Site verification error", exc_info=True)
