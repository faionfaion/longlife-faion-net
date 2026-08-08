"""Inline illustrations for a material.

A normal post gets a single cover. A material runs long and reads better broken up, so this
stage briefs a couple of extra images tied to specific beats of the piece, renders them, and
drops them into the body at section breaks. It is best-effort: any failure leaves the
material intact with fewer images rather than no material.
"""

from __future__ import annotations

import logging
import re

from pipeline.config import CHARACTER_REFERENCES, EXPRESSION_REFERENCE, MODEL_IMAGE
from pipeline.context import PipelineContext
from pipeline.image_gen import generate_image
from pipeline.schemas import load_schema
from pipeline.sdk import structured_query
from pipeline.stages.s_comic_scene import (
    _build_comic_image_prompt,
    _face_reads,
)

logger = logging.getLogger(__name__)

MAX_INLINE = 2

_SYSTEM = (
    "You are the photo director for Vita's health blog. She is a 42-year-old health "
    "scientist. You brief inline illustrations for a long feature - images that sit between "
    "sections and carry a beat of the piece, not decoration. Photographic, never cartoon; "
    "no text, labels or logos anywhere in frame; the setting is a large unnamed coastal "
    "city read through light and surface, never a landmark. Prefer variety: lean toward "
    "still lifes and empty rooms (wardrobe 'none') so a long piece is not the same face "
    "over and over; use 'scientist' or 'fitness' only when a person genuinely adds meaning."
)


def _schema() -> dict:
    one = load_schema("comic_scene")
    return {
        "type": "object",
        "properties": {"illustrations": {"type": "array", "items": one}},
        "required": ["illustrations"],
    }


def run(ctx: PipelineContext) -> None:
    if not ctx.article_text or not ctx.slug:
        return

    headings = _h2_positions(ctx.article_text)
    if len(headings) < 2:
        logger.info("[material-images] too few sections to place inline images, skipping")
        return

    want = min(MAX_INLINE, len(headings) - 1)
    try:
        result = structured_query(
            prompt=_brief_prompt(ctx, want),
            system_prompt=_SYSTEM,
            schema=_schema(),
            model=MODEL_IMAGE,
        )
    except Exception:
        logger.warning("[material-images] briefing failed, material stays cover-only",
                       exc_info=True)
        return

    scenes = (result.get("illustrations") or [])[:want]
    # Insert from the bottom up so earlier offsets stay valid as we splice text in.
    targets = _insertion_points(headings, len(scenes))
    inserted = 0
    for idx, (scene, pos) in enumerate(sorted(zip(scenes, targets), key=lambda x: -x[1]), 1):
        path = _render(ctx, scene, idx)
        if not path:
            continue
        alt = (scene.get("scene_description") or ctx.title)[:120].replace("]", "").replace("\n", " ")
        md = f"\n\n![{alt}](/images/{path.name})\n\n"
        ctx.article_text = ctx.article_text[:pos] + md + ctx.article_text[pos:]
        inserted += 1

    logger.info("[material-images] inserted %d inline illustration(s)", inserted)


def _render(ctx: PipelineContext, scene: dict, idx: int):
    wardrobe = scene.get("wardrobe", "none")
    prompt = _build_comic_image_prompt(scene)
    reference = CHARACTER_REFERENCES.get(wardrobe)
    expr = EXPRESSION_REFERENCE if reference and _face_reads(scene.get("pose", "")) else None
    try:
        return generate_image(
            prompt, f"{ctx.slug}-img{idx}", comic_mode=True,
            reference=reference, expression_reference=expr,
        )
    except Exception:
        logger.warning("[material-images] render %d failed", idx, exc_info=True)
        return None


def _h2_positions(text: str) -> list[int]:
    """Character offset of the start of every '## ' heading line."""
    return [m.start() for m in re.finditer(r"(?m)^##\s", text)]


def _insertion_points(headings: list[int], n: int) -> list[int]:
    """Pick n heading starts to place an image before, spread through the piece.

    Skips the first heading so an image never lands between the intro and the first section,
    and spaces the rest out rather than clustering them.
    """
    candidates = headings[1:] or headings
    if n >= len(candidates):
        return candidates[:n]
    step = len(candidates) / (n + 1)
    return [candidates[int(step * (i + 1))] for i in range(n)]


def _brief_prompt(ctx: PipelineContext, want: int) -> str:
    return (
        f"Brief exactly {want} inline illustrations for this feature. Each must tie to a "
        f"different part of the piece and, together, vary the setting and the register. "
        f"For each, fill every field of the schema; set wardrobe to 'none' for a still life "
        f"or empty room (preferred here) and leave outfit/pose/expression empty when so.\n\n"
        f"Title: {ctx.title}\n\n{ctx.article_text[:6000]}"
    )
