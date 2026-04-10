"""Stage 4: Review — editorial review of the generated article."""

from __future__ import annotations

import logging

from pipeline.config import AUTHOR_NAME, MODEL_REVIEW
from pipeline.context import PipelineContext
from pipeline.prompts.builder import build_review_prompt
from pipeline.schemas import load_schema
from pipeline.sdk import structured_query

logger = logging.getLogger(__name__)


def run(ctx: PipelineContext) -> None:
    system, prompt = build_review_prompt(ctx, AUTHOR_NAME)

    result = structured_query(
        prompt=prompt,
        system_prompt=system,
        schema=load_schema("review"),
        model=MODEL_REVIEW,
    )

    ctx.review_approved = result.get("approved", False)
    ctx.review_feedback = result.get("feedback", "")
    score = result.get("score", 0)

    logger.info("Review: score=%d, approved=%s", score, ctx.review_approved)
    if ctx.review_feedback:
        logger.info("Feedback: %s", ctx.review_feedback[:200])
