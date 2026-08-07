"""Image rendering through the Codex CLI.

Codex authenticates against the ChatGPT subscription rather than the API credit balance,
which is the whole point of routing covers through it: `api.openai.com/v1/images` has been
answering `insufficient_quota` since 22 July 2026, and every cover since then was lost.

CLI quirks worth knowing:
- `codex exec` reads stdin and blocks on "Reading additional input from stdin..." unless
  stdin is closed, so it is always run with stdin at DEVNULL.
- Generated images land in ~/.codex/generated_images/<uuid>/ and the agent copies them
  where it was told. It will happily report success having written nothing, so the
  destination is verified rather than believed.
"""

from __future__ import annotations

import logging
import random
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)

CODEX_BIN = "codex"
TIMEOUT_S = 900
MIN_USABLE_BYTES = 10_000


class CodexImageError(RuntimeError):
    """Codex produced no usable image."""


def _scratch() -> Path:
    d = Path("/tmp") / "longlife-images"
    d.mkdir(parents=True, exist_ok=True)
    return d


def render(
    prompt: str,
    reference: Path | None = None,
    aspect: str = "landscape, roughly 3:2",
) -> Path:
    """Render one image and return the path to the raw PNG Codex wrote.

    `reference` is Vita's turnaround sheet, passed only when she is actually in the cover.
    Covers that are a still life or an empty room must not get it: handed a character
    reference, the model tends to put the character in anyway.

    Raises CodexImageError if nothing usable landed on disk. Callers convert and resize;
    this function's only job is to get pixels out of Codex.
    """
    if reference is not None and not reference.exists():
        raise CodexImageError(f"reference image missing: {reference}")

    target = _scratch() / f"{int(time.time() * 1000)}_{random.randint(1000, 9999)}.png"
    if target.exists():
        target.unlink()

    if reference is not None:
        opening = (
            f"Use the image at {reference} as a character reference. It is a model sheet "
            f"of one woman shown from several angles. Generate a NEW photograph of that "
            f"same woman — same face, same age, same hair, same glasses, same watch — in "
            f"this scene:"
        )
    else:
        opening = (
            "Generate a photograph of the following scene. There must be no people and no "
            "animals anywhere in the frame:"
        )

    instruction = (
        f"{opening}\n\n{prompt}\n\n"
        f"Do not draw any text, lettering, labels, captions, logos or watermarks anywhere "
        f"in the image. Model-drawn text comes out as garbled pseudo-words, and on a "
        f"Ukrainian-language publication that reads as carelessness. Where a scene would "
        f"naturally carry a label — a bottle, a chart axis, a package — draw it blank or "
        f"leave the lettering out of frame.\n"
        f"{aspect.capitalize()} orientation. "
        f"Save the result to exactly {target}. Do not save it anywhere else and do not "
        f"rename it."
    )

    cmd = [
        CODEX_BIN, "exec", "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        instruction,
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_S,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired as e:
        raise CodexImageError(f"codex image timed out after {TIMEOUT_S}s") from e
    except FileNotFoundError as e:
        raise CodexImageError("codex CLI not found on PATH") from e

    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "")[-400:]
        raise CodexImageError(f"codex exited {proc.returncode}: {tail}")

    if not target.exists() or target.stat().st_size < MIN_USABLE_BYTES:
        raise CodexImageError("codex reported an image but wrote no usable file")

    logger.debug("Codex rendered %s (%d KB)", target, target.stat().st_size // 1024)
    return target
