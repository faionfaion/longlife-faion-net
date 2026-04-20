"""Image orchestrator: prompt editor -> gen -> QA -> retry loop.

Flow:
1. Optimize the raw scene prompt (s_image_prompt_editor.optimize)
2. Generate image at quality="auto"
3. QA via Claude vision (s_image_qa.analyze)
4. If QA flags artifacts:
   - Attempt 2: revise prompt with QA feedback + quality="high"
   - Attempt 3: simplify prompt + quality="high"
5. Return the last successful image (or last attempt if all failed QA).
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from pipeline.image_gen import generate_image
from pipeline.stages import s_image_prompt_editor as prompt_editor
from pipeline.stages import s_image_qa

logger = logging.getLogger(__name__)


MAX_ATTEMPTS = 3


def generate_with_qa(
    raw_prompt: str,
    slug: str,
    comic_mode: bool = False,
) -> Path | None:
    """Generate an image with QA-driven retry and prompt refinement.

    Args:
        raw_prompt: Scene prompt as built by s_comic_scene or similar.
        slug: Article slug for filename.
        comic_mode: Whether the prompt already includes style (comic style).

    Returns:
        Path to final saved image, or None if generation failed entirely.
    """
    logger.info("[image-orchestrator] Starting for slug=%s", slug)

    # Step 0: optimize prompt
    try:
        current_prompt = prompt_editor.optimize(raw_prompt)
    except Exception as e:
        logger.warning("[image-orchestrator] Editor optimize failed (%s) — using raw prompt", e)
        current_prompt = raw_prompt

    best_image: Path | None = None
    best_severity_rank = -1  # higher = cleaner (none=3, low=2, high=1, missing=0)
    last_issues: list[str] = []

    for attempt in range(1, MAX_ATTEMPTS + 1):
        quality = "auto" if attempt == 1 else "high"
        logger.info("[image-orchestrator] Attempt %d/%d (quality=%s)", attempt, MAX_ATTEMPTS, quality)

        img_path = generate_image(
            prompt=current_prompt,
            slug=f"{slug}_try{attempt}" if attempt > 1 else slug,
            comic_mode=comic_mode,
            quality=quality,
        )

        if img_path is None or not img_path.exists():
            logger.warning("[image-orchestrator] Attempt %d failed to produce image", attempt)
            continue

        qa_result = s_image_qa.analyze(img_path, scene_context=raw_prompt)
        sev_rank = _severity_rank(qa_result)

        # Track best-seen image (prefer cleaner severity)
        if sev_rank > best_severity_rank:
            best_severity_rank = sev_rank
            best_image = img_path

        if qa_result.get("ok") and not qa_result.get("retry_recommended"):
            logger.info("[image-orchestrator] QA passed on attempt %d", attempt)
            _finalize(img_path, slug)
            return Path(str(img_path).replace(f"_try{attempt}", "")) if attempt > 1 else img_path

        last_issues = qa_result.get("issues", [])
        logger.info(
            "[image-orchestrator] Attempt %d failed QA (severity=%s, issues=%d)",
            attempt, qa_result.get("severity"), len(last_issues),
        )

        # Prepare prompt for next attempt
        if attempt == 1:
            try:
                current_prompt = prompt_editor.revise(raw_prompt, current_prompt, last_issues)
            except Exception as e:
                logger.warning("[image-orchestrator] Editor revise failed: %s", e)
        elif attempt == 2:
            try:
                current_prompt = prompt_editor.simplify(raw_prompt)
            except Exception as e:
                logger.warning("[image-orchestrator] Editor simplify failed: %s", e)

    # All attempts exhausted — keep the best we've seen
    if best_image and best_image.exists():
        logger.warning(
            "[image-orchestrator] All %d attempts had QA issues, keeping best (last issues: %s)",
            MAX_ATTEMPTS, "; ".join(last_issues)[:200],
        )
        _finalize(best_image, slug)
        # Return canonical path (without _tryN suffix)
        canonical = best_image.parent / f"{slug}.jpg"
        return canonical if canonical.exists() else best_image

    logger.error("[image-orchestrator] No image produced after %d attempts", MAX_ATTEMPTS)
    return None


def _severity_rank(qa: dict) -> int:
    """Rank QA severity — higher is better (cleaner)."""
    if qa.get("ok") and not qa.get("retry_recommended"):
        return 3
    sev = qa.get("severity", "high")
    return {"none": 3, "low": 2, "high": 1}.get(sev, 1)


def _finalize(img_path: Path, slug: str) -> None:
    """Copy the chosen image to the canonical slug.jpg path."""
    canonical = img_path.parent / f"{slug}.jpg"
    if img_path.resolve() == canonical.resolve():
        return
    try:
        shutil.copy2(img_path, canonical)
        logger.info("[image-orchestrator] Finalized: %s", canonical)
    except Exception:
        logger.warning("[image-orchestrator] Could not copy %s -> %s", img_path, canonical, exc_info=True)
