"""Stage comic_scene: Generate comic panel scene description for article illustration.

Runs after article generation (s3) and review loop (s4-s5), before save (s7).
Creates a structured comic scene featuring Vita — the LongLife Media mascot.
"""

from __future__ import annotations

import json
import logging

from pathlib import Path

from pipeline.config import CHARACTER_REFERENCES, MODEL_IMAGE
from pipeline.context import PipelineContext
from pipeline.prompts.builder import build_comic_scene_prompt
from pipeline.schemas import load_schema
from pipeline.sdk import structured_query

logger = logging.getLogger(__name__)

_PARTIALS = Path(__file__).resolve().parent.parent / "prompts" / "templates" / "_partials"

# Repeated in the prompt on top of the reference sheet. The reference carries the face;
# this carries the markers the model most often drops between renders.
_CHARACTER_PHYSICAL = (
    "A 42-year-old woman, 168 cm, lean and trained without being bulky. Brown wavy hair "
    "in a ponytail with loose strands framing the face, hazel eyes, fair skin, minimal "
    "makeup, visible laugh lines. Black rectangular-framed glasses and a black "
    "minimalist watch on the left wrist, both always present."
)

_WARDROBE_LINES = {
    "scientist": (
        "Wearing a cream or pale-blue button shirt with the sleeves rolled to the "
        "forearm, dark charcoal tailored trousers, brown leather belt, brown loafers."
    ),
    "fitness": (
        "Wearing a plain black racerback tank, black full-length leggings and black "
        "trainers, no visible logos."
    ),
}


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

    wardrobe = result.get("wardrobe", "scientist")
    ctx.image_prompt = _build_comic_image_prompt(result)
    ctx.image_reference = CHARACTER_REFERENCES.get(wardrobe)

    logger.info(
        "Cover scene: wardrobe=%s | %s | pose=%s | props=%s",
        wardrobe,
        result.get("scene_description", "")[:60],
        result.get("pose", ""),
        ", ".join(result.get("props", [])),
    )


def _build_comic_image_prompt(scene: dict) -> str:
    """Combine style, wardrobe and scene into a full image generation prompt."""
    wardrobe = scene.get("wardrobe", "scientist")

    if wardrobe == "none":
        style_file = _PARTIALS / "image_style.txt"
        subject = ""
    else:
        style_file = _PARTIALS / "comic_style.txt"
        subject = f"Subject: {_CHARACTER_PHYSICAL} {_WARDROBE_LINES[wardrobe]}"

    style = style_file.read_text(encoding="utf-8").strip() if style_file.exists() else ""

    parts = [
        style,
        subject,
        f"Scene: {scene.get('scene_description', '')}",
        f"Framing: {scene.get('pose', '')}",
        f"Expression: {scene.get('expression', '')}",
        f"Setting: {scene.get('background', '')}",
        f"Objects in frame: {', '.join(scene.get('props', []))}",
        f"Grade: {scene.get('color_notes', '')}",
        "Nothing in the frame carries text, lettering, labels or logos.",
    ]

    # Empty fields still render as a bare label ("Expression: "), which reads to the image
    # model as an instruction it has to satisfy. Still-life covers leave several blank.
    return " ".join(p for p in parts if p and not p.endswith(": "))
