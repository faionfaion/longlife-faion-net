"""Stage 7b: Deploy site to server.

Pushes git commits and triggers remote build+deploy via SSH.
Called once after all articles are saved in a batch run.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from pipeline.config import CONTENT_DIR
from pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


def run() -> None:
    """Push all commits and deploy site to faion-net server.

    Called once after the entire batch is saved. Performs:
    1. git push origin master
    2. SSH into faion-net: pull, gatsby build, rsync to /var/www/
    """
    root = str(CONTENT_DIR.parent)

    try:
        # Push to GitHub
        subprocess.run(["git", "push", "origin", "master"],
                       cwd=root, capture_output=True, timeout=60)
        logger.info("Git pushed to origin/master")
    except Exception:
        logger.error("Git push failed", exc_info=True)

    try:
        # SSH deploy: pull + build + rsync on server
        logger.info("Deploying to faion-net server...")
        ssh_cmd = [
            "ssh", "-i", str(Path.home() / ".ssh" / "id_ed25519"),
            "-p", "22022", "-o", "StrictHostKeyChecking=no",
            "faion@46.225.58.119",
            "cd ~/longlife && git checkout -- . && git clean -fd && git pull && "
            "cd gatsby && npx gatsby build && "
            "sudo rsync -a --delete public/ /var/www/longlife.faion.net/",
        ]
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=600)
        if result.returncode == 0:
            logger.info("Site deployed to faion-net")
        else:
            logger.error("Server deploy failed: %s", result.stderr[:300])
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
