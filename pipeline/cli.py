"""CLI entry point: argparse, logging setup, mode dispatch.

This is what ``__main__.py`` calls to run the pipeline.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

logger = logging.getLogger("pipeline")


def cli() -> None:
    """Parse arguments, configure logging, and dispatch to the requested mode."""
    parser = argparse.ArgumentParser(description="LongLife publishing pipeline")
    parser.add_argument("mode", nargs="?", default="generate",
                        choices=["generate", "publish", "digest"],
                        help="Pipeline mode (default: generate)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run without deploy/publish")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # File logging
    log_dir = Path(__file__).resolve().parent.parent / "state" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(log_dir / "pipeline.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logging.getLogger().addHandler(fh)

    try:
        if args.mode == "generate":
            from pipeline.modes.generate import run as run_generate
            completed = run_generate(dry_run=args.dry_run)
            logger.info("Batch complete: %d articles", len(completed))
            sys.exit(0)
        elif args.mode == "publish":
            from pipeline.modes.publish import run as run_publish
            result = run_publish()
            sys.exit(0 if result else 1)
        elif args.mode == "digest":
            from pipeline.modes.digest import run as run_digest
            result = run_digest()
            sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception:
        logger.exception("Pipeline failed")
        sys.exit(1)
