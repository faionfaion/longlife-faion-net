"""Stage 5: Revise — apply editorial feedback to the article."""

from __future__ import annotations

import logging

from pipeline.config import AUTHOR_NAME, MODEL_GENERATE
from pipeline.context import PipelineContext
from pipeline.prompts.builder import build_revise_prompt
from pipeline.schemas import load_schema
from pipeline.sdk import structured_query

logger = logging.getLogger(__name__)


def run(ctx: PipelineContext) -> None:
    system, prompt = build_revise_prompt(ctx, AUTHOR_NAME)

    # Revision returns the whole article back as one JSON string. On a long piece - a
    # material runs to several thousand words - that payload gets big enough that the
    # structured response occasionally comes back truncated and JSON repair gives up. When
    # it does, the right move is to keep the article we already have (it was generated and
    # reviewed) rather than let a polish step destroy the whole post. So a revise failure
    # degrades to "no change this cycle", never to a lost article.
    try:
        result = structured_query(
            prompt=prompt,
            system_prompt=system,
            schema=load_schema("revision"),
            model=MODEL_GENERATE,
        )
    except Exception:
        logger.warning("Revision failed (likely oversized JSON); keeping current article",
                       exc_info=True)
        return

    if result.get("article"):
        ctx.article_text = result["article"]
    if result.get("title"):
        ctx.title = result["title"]
    if result.get("description"):
        ctx.description = result["description"]

    logger.info("Revised article: %d words", len(ctx.article_text.split()))
