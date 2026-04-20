"""Stage 7b: Deploy site to server.

Runs gatsby/deploy-gh.sh which pushes to GitHub and triggers
remote build+deploy via SSH.
"""

from __future__ import annotations

import logging
import subprocess

from pipeline.config import DEPLOY_SH, ROOT
from pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


def run() -> None:
    """Run deploy-gh.sh to push, build, and deploy site."""
    if not DEPLOY_SH.exists():
        logger.error("Deploy script not found: %s", DEPLOY_SH)
        return

    logger.info("Starting deploy: %s", DEPLOY_SH)

    try:
        result = subprocess.run(
            ["bash", str(DEPLOY_SH)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode == 0:
            logger.info("Site deployed to faion-net")
        else:
            logger.error(
                "Deploy failed (exit %d): %s",
                result.returncode,
                result.stderr[:500] if result.stderr else "no stderr",
            )
    except subprocess.TimeoutExpired:
        logger.error("Deploy timed out after 600s")
    except Exception:
        logger.error("Deploy failed", exc_info=True)


# Backward-compatible aliases for existing callers
def save_article(ctx: PipelineContext) -> None:
    """Legacy alias: delegates to s7_save.run()."""
    from pipeline.stages.s7_save import run as save_run
    save_run(ctx)


def deploy_site() -> None:
    """Legacy alias: delegates to s7_deploy.run()."""
    run()
