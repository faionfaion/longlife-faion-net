"""Stage 6: Generate TG — write Telegram photo caption."""

from __future__ import annotations

import logging

from pipeline.config import MAX_TG_CAPTION, MODEL_TG, SITE_BASE_URL
from pipeline.context import PipelineContext
from pipeline.prompts.builder import build_tg_post_prompt
from pipeline.schemas import load_schema
from pipeline.sdk import structured_query

logger = logging.getLogger(__name__)


def run(ctx: PipelineContext) -> None:
    article_url = f"{SITE_BASE_URL}/{ctx.slug}/"

    system, prompt = build_tg_post_prompt(ctx)

    result = structured_query(
        prompt=prompt,
        system_prompt=system,
        schema=load_schema("tg_post"),
        model=MODEL_TG,
    )

    hook = result["hook"]
    body = result["body"]
    tip = result.get("tip", "")

    # Build quick tip block
    tip_block = ""
    if tip:
        tip_block = f"\n\n💡 <b>Швидка порада:</b> {tip}"

    # Assemble caption
    parts = [
        f"<b>{hook}</b>",
        "",
        body,
    ]

    if tip_block:
        parts.append(tip_block)

    parts.extend([
        "",
        f'<a href="{article_url}">Читати повністю →</a>',
        "",
        '<a href="https://t.me/long_life_media">🌿 LongLife Media</a>',
    ])

    ctx.tg_post = "\n".join(parts)
    ctx.article_url = article_url
    logger.info("TG caption: %d chars", len(ctx.tg_post))
