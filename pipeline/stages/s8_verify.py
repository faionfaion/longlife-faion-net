"""Stage 8: Verify — check that the article actually got out of this machine.

What "out" means depends on where the run happened. On the host that serves the site, the
article should be live within the same run, so the check is an HTTP fetch. On the host that
only generates, the site is rebuilt hours later by the web host's own cron, so fetching the
URL would 404 on every single run and train everyone to ignore a failing verify. There the
meaningful check is whether the commit reached GitHub, since that is the only route the
article has to the machine that publishes it.
"""

from __future__ import annotations

import logging
import socket
import subprocess
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from pipeline.config import ROOT, SITE_BASE_URL
from pipeline.context import PipelineContext

logger = logging.getLogger(__name__)

WEBROOT = Path("/var/www/longlife.media")


def run(ctx: PipelineContext) -> None:
    if _serves_the_site():
        _verify_live(ctx)
    else:
        _verify_pushed(ctx)


def _serves_the_site() -> bool:
    return WEBROOT.is_dir() or socket.gethostname() == "faion-net-new"


def _verify_live(ctx: PipelineContext) -> None:
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


def _verify_pushed(ctx: PipelineContext) -> None:
    """Confirm the article's file exists in the commit GitHub now has."""
    expected = f"content/{ctx.slug}.md"

    try:
        proc = subprocess.run(
            ["git", "cat-file", "-e", f"origin/master:{expected}"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (subprocess.SubprocessError, OSError):
        ctx.site_ok = False
        logger.error("Could not check whether the article was pushed", exc_info=True)
        return

    if proc.returncode == 0:
        ctx.site_ok = True
        logger.info(
            "Article pushed: %s is on origin/master; the web host builds it on its own cron",
            expected,
        )
    else:
        ctx.site_ok = False
        logger.error(
            "Article is NOT on origin/master (%s) — it exists only on this machine and "
            "will never reach the site or the channel",
            expected,
        )
