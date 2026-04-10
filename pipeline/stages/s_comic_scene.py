"""Stage comic_scene: Generate comic panel scene description for article illustration.

Runs after article generation (s3) and review loop (s4-s5), before save (s7).
Creates a structured comic scene featuring Vita — the LongLife Media mascot.
"""

from __future__ import annotations

import json
import logging

from pipeline.config import MODEL_IMAGE
from pipeline.context import PipelineContext
from pipeline.prompts.builder import build_comic_scene_prompt
from pipeline.schemas import load_schema
from pipeline.sdk import structured_query

logger = logging.getLogger(__name__)


def run(ctx: PipelineContext) -> None:
    """Generate a comic scene description based on the article content.

    Populates ctx.comic_scene (dict) and updates ctx.image_prompt with
    a character-consistent comic-style prompt.
    """
    if not ctx.article_text or not ctx.title:
        logger.warning("No article text/title — skipping comic scene generation")
        return

    system, prompt = build_comic_scene_prompt(ctx)

    result = structured_query(
        prompt=prompt,
        system_prompt=system,
        schema=load_schema("comic_scene"),
        model=MODEL_IMAGE,
    )

    ctx.comic_scene = result

    # Build the image prompt from the comic scene + character description
    ctx.image_prompt = _build_comic_image_prompt(result)

    logger.info(
        "Comic scene: %s | pose=%s | expression=%s | props=%s",
        result.get("scene_description", "")[:60],
        result.get("pose", ""),
        result.get("expression", ""),
        ", ".join(result.get("props", [])),
    )


def _build_comic_image_prompt(scene: dict) -> str:
    """Combine character description + scene into a full image generation prompt."""
    from pathlib import Path

    # Load style and character partials
    partials_dir = Path(__file__).resolve().parent.parent / "prompts" / "templates" / "_partials"

    style_file = partials_dir / "comic_style.txt"
    style = style_file.read_text(encoding="utf-8").strip() if style_file.exists() else ""

    # Character physical description (always prepended for consistency)
    character_desc = (
        "Tall athletic muscular woman (178cm), long wavy blonde hair past shoulders "
        "parted on the left, bright green eyes, defined muscles but feminine build, "
        "sun-kissed skin. Small green leaf tattoo on right shoulder. "
        "Black fitness smartwatch on left wrist. "
    )

    parts = [
        style,
        "Single panel composition.",
        f"Character: {character_desc}",
        f"Scene: {scene.get('scene_description', '')}",
        f"Pose: {scene.get('pose', '')}",
        f"Expression: {scene.get('expression', '')}",
        f"Background: {scene.get('background', '')}",
        f"Props: {', '.join(scene.get('props', []))}",
        f"Colors: {scene.get('color_notes', '')}",
        "No text overlays, no speech bubbles in the image, no watermarks.",
    ]

    return " ".join(p for p in parts if p)
