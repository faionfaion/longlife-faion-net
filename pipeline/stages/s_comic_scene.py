"""Stage comic_scene: Generate comic panel scene description for article illustration.

Runs after article generation (s3) and review loop (s4-s5), before save (s7).
Creates a structured comic scene featuring Vita — the LongLife Media mascot.
"""

from __future__ import annotations

import json
import logging

from pathlib import Path

from pipeline.config import CHARACTER_REFERENCES, EXPRESSION_REFERENCE, MODEL_IMAGE
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

# The base each wardrobe always keeps. The specific look on top comes from the scene
# director's `outfit`, so the covers are not all the same shirt: pinning one outfit here
# reintroduced, one level down, exactly the sameness we removed by retiring the mascot.
_WARDROBE_LINES = {
    "scientist": (
        "Dressed for work, muted and unbranded: dark charcoal tailored trousers, brown "
        "leather belt, brown loafers or black flats."
    ),
    "fitness": (
        "Dressed to train: black full-length leggings, black trainers, no visible logos."
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
    ctx.expression_reference = (
        EXPRESSION_REFERENCE
        if ctx.image_reference and _face_reads(result.get("pose", ""))
        else None
    )

    logger.info(
        "Cover scene: wardrobe=%s | outfit=%s | expr=%s%s | %s",
        wardrobe,
        result.get("outfit", "") or "-",
        result.get("expression", "") or "-",
        " (+sheet)" if ctx.expression_reference else "",
        result.get("scene_description", "")[:60],
    )


def _face_reads(pose: str) -> bool:
    """Whether the face is big enough in frame for an expression to be worth steering.

    On a WIDE shot she is a third of the frame at most and the expression sheet buys
    nothing, while adding a second reference the model can drift towards.
    """
    return "WIDE" not in pose.upper()


def _build_comic_image_prompt(scene: dict) -> str:
    """Combine scene, wardrobe and style into a full image generation prompt.

    Ordering is deliberate: what the picture *is* comes first, how it should look comes
    last. The style partial is a long paragraph of constraints, and leading with it buries
    the actual subject several sentences deep.

    Blocks are newline-separated rather than run together. It costs nothing at render time
    and makes the prompt readable in a log when a cover comes out wrong.
    """
    wardrobe = scene.get("wardrobe", "scientist")
    still_life = wardrobe == "none"

    style_file = _PARTIALS / ("image_style.txt" if still_life else "comic_style.txt")
    style = style_file.read_text(encoding="utf-8").strip() if style_file.exists() else ""

    blocks: list[str] = [f"Scene: {scene.get('scene_description', '')}"]

    if not still_life:
        outfit = (scene.get("outfit") or "").strip()
        subject = f"{_CHARACTER_PHYSICAL} {_WARDROBE_LINES[wardrobe]}"
        if outfit:
            subject = f"{subject} For this shot: {outfit}."
        blocks.append(f"Subject: {subject}")
        blocks.append(f"Framing: {scene.get('pose', '')}")
        blocks.append(f"Expression: {scene.get('expression', '')}")

    blocks += [
        f"Setting: {scene.get('background', '')}",
        f"Objects in frame: {', '.join(scene.get('props', []))}",
        f"Grade: {scene.get('color_notes', '')}",
        f"Style: {style}",
        "Nothing in the frame carries text, lettering, labels or logos.",
    ]

    # A field the director left empty still renders as a bare label ("Expression: "), which
    # reads to the image model as an instruction it is expected to satisfy somehow.
    return "\n".join(b for b in blocks if b and not b.endswith(": "))
