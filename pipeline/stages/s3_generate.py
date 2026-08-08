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

    ctx.title = normalize_dashes(result["title"])
    ctx.slug = result["slug"]
    body = normalize_dashes(strip_sources_section(strip_leading_metadata(result["article"])))
    body, urls, names = delink_sources(
        body, result.get("source_urls", []), result.get("source_names", [])
    )
    ctx.article_text = body
    ctx.description = normalize_dashes(result.get("description", ""))
    ctx.tags = result.get("tags", [])
    ctx.hashtags = result.get("hashtags", "")
    ctx.source_urls = urls
    ctx.source_names = names
    ctx.image_prompt = result.get("image_prompt", "")
    ctx.summary = result.get("summary", "")

    logger.info(
        "Generated: '%s' (slug=%s, %d words, %d sources)",
        ctx.title, ctx.slug,
        len(ctx.article_text.split()),
        len(ctx.source_urls),
    )


# Both the English field names and the Ukrainian labels the model reaches for when it
# decides to be helpful, with or without markdown emphasis around the whole line.
_META_WORDS = (
    r"Category|Tags|Title|Type|Hashtags|Slug|Description|Author|Evidence[ _]level"
    r"|Категорі[яї]|Теги|Заголовок|Тип|Опис|Автор|Хештеги"
)
_META_LINE = re.compile(rf"^\s*[*_]{{0,2}}\s*({_META_WORDS})\s*:", re.IGNORECASE)


def normalize_dashes(text: str) -> str:
    """Replace the em-dash with the hyphen a person actually types.

    The em-dash (—) is correct Ukrainian punctuation, but it is not on a keyboard and
    almost nobody types it, so a text dense with them reads as machine-set — a quiet tell to
    a lay reader. We swap the clause dash for the spaced hyphen people use instead. En-dash
    ranges (18–24) and the minus sign (−0.35) are left alone: those are not the long dash,
    and turning them into hyphens would mangle numbers.
    """
    text = re.sub(r"\s*—\s*", " - ", text)     # em-dash → spaced hyphen
    text = re.sub(r"(?m)^\s*-\s+", "- ", text)        # a line that now starts " - " → "- "
    text = re.sub(r"[ \t]{2,}", " ", text)            # collapse the doubled spaces that leaves
    return text


_SOURCES_HEADING = re.compile(
    r"(?im)^\s{0,3}#{1,3}\s*(джерела|джерело|sources|посилання|література|references)\s*:?\s*$"
)


def strip_sources_section(body: str) -> str:
    """Drop a trailing "## Джерела" list.

    Every claim already carries its source as an inline link, so a separate reference list
    at the end repeats every citation a second time. The heading must match exactly - a real
    section like "## Джерела B12 у їжі" (sources of B12 in food) is content, not a citation
    list, so the pattern anchors on the bare word at end of line and leaves it alone. The
    structured source_urls/source_names in the frontmatter stay; only the visible duplicate
    goes.
    """
    m = _SOURCES_HEADING.search(body)
    if not m:
        return body
    # A citation list runs to the end of the article, so cut from the heading onward.
    return body[: m.start()].rstrip() + "\n"


_MD_LINK = re.compile(r"(?<!\!)\[([^\]]+)\]\((https?://[^)\s]+)\)")


def delink_sources(body: str, urls: list, names: list) -> tuple[str, list, list]:
    """Move source links out of the prose and into the consolidated list.

    The blog shows sources as one clean "Джерела" block built from the frontmatter, so the
    body should read as plain prose: a study is named in words, not turned into a link on
    every mention. This harvests every external link into source_urls/source_names (so the
    block is complete) and then unlinks it in the body, keeping just the words. Internal
    cross-links to longlife.media stay as links - those are navigation between posts, not
    citations. Images (![...]) are untouched.
    """
    urls = list(urls or [])
    names = list(names or [])

    def repl(m: "re.Match") -> str:
        text, url = m.group(1), m.group(2)
        if "longlife.media" in url:
            return m.group(0)  # internal cross-reference: keep the link
        if url not in urls:
            urls.append(url)
            names.append(text)
        return text  # citation: drop the link, keep the words

    body = _MD_LINK.sub(repl, body)
    # De-linking a "[PubMed](url)" leaves the bare label "(PubMed)" sitting in the prose.
    # Those are pure link-labels, never Ukrainian content words, so drop the parenthetical.
    # A real journal named in the sentence (The Lancet, JAMA) is untouched.
    body = re.sub(r"[ \t]*\((?:PubMed|DOI|doi|PMID|NCBI|посилання|тут)\)", "", body)
    return body, urls, names


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
