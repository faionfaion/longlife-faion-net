"""Stage 3: Generate — write the health article in Ukrainian from research."""

from __future__ import annotations

import logging
import re

from pipeline.config import (
    CONTENT_DIR, CONTENT_TYPES, MODEL_GENERATE, SITE_BASE_URL,
)
from pipeline.context import PipelineContext
from pipeline.prompts.builder import build_generate_prompt
from pipeline.schemas import load_schema
from pipeline.sdk import structured_query

logger = logging.getLogger(__name__)


def run(ctx: PipelineContext) -> None:
    type_cfg = CONTENT_TYPES.get(ctx.slot_type, CONTENT_TYPES["research"])

    system, prompt = build_generate_prompt(
        ctx=ctx,
        type_cfg=type_cfg,
        site_base_url=SITE_BASE_URL,
        existing_articles_text=_format_existing_articles(ctx.posted_slugs[-30:]),
    )

    result = structured_query(
        prompt=prompt,
        system_prompt=system,
        schema=load_schema("generation"),
        model=MODEL_GENERATE,
    )

    ctx.title = result["title"]
    ctx.slug = result["slug"]
    ctx.article_text = strip_leading_metadata(result["article"])
    ctx.description = result.get("description", "")
    ctx.tags = result.get("tags", [])
    ctx.hashtags = result.get("hashtags", "")
    ctx.source_urls = result.get("source_urls", [])
    ctx.source_names = result.get("source_names", [])
    ctx.image_prompt = result.get("image_prompt", "")
    ctx.summary = result.get("summary", "")

    logger.info(
        "Generated: '%s' (slug=%s, %d words, %d sources)",
        ctx.title, ctx.slug,
        len(ctx.article_text.split()),
        len(ctx.source_urls),
    )


_META_LINE = re.compile(
    r"^\s*(Category|Tags|Title|Type|Hashtags|Slug|Description|Author|Evidence[ _]level)\s*:",
    re.IGNORECASE,
)


def strip_leading_metadata(body: str) -> str:
    """Drop metadata lines the model sometimes prefixes to the article body.

    The prompt says the `article` field is the body and nothing else, and most of the time
    that holds — but often enough the model opens with "Category: ..." and "Tags: ...",
    which then render as the first two lines of the published page. Those values already
    have their own JSON fields and their own place in the frontmatter, so anything matching
    here is a duplicate rather than content.

    Only strips from the top, and stops at the first real line: a "Type:" further down is
    part of the article.
    """
    lines = body.lstrip().split("\n")
    start = 0
    for line in lines:
        if not line.strip() or _META_LINE.match(line):
            start += 1
            continue
        break
    if start:
        logger.info("Stripped %d metadata line(s) leaked into the body", start)
    return "\n".join(lines[start:]).lstrip()


def _format_existing_articles(slugs: list[str]) -> str:
    """Format existing articles with titles for cross-reference context."""
    lines = []
    for slug in slugs:
        md = CONTENT_DIR / f"{slug}.md"
        if not md.exists():
            continue
        text = md.read_text(encoding="utf-8")
        title = ""
        for line in text.split("\n"):
            if line.startswith("title:"):
                title = line.split('"')[1] if '"' in line else line.split(": ", 1)[1]
                break
        if title:
            lines.append(f"- {slug}: {title} ({SITE_BASE_URL}/{slug}/)")
    return "\n".join(lines) if lines else "(no existing articles)"
