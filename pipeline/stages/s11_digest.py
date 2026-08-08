"""Stage 11: the Sunday digest — the past week written as one long post.

It used to be a short evening list of links sent straight to Telegram. It is now a piece
in its own right: a week of news and a week of my own posts woven into one read, published
to the site like anything else, which is what makes Sunday's channel post a post rather
than an index.

Because it comes out of the same generation schema as a normal article, it goes through
the same cover, teaser, save and deploy stages, and the daily publish picks it up without
knowing it is any different.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pipeline.config import (
    CONTENT_DIR, CONTENT_TYPES, MODEL_GENERATE, SITE_BASE_URL, STATE_DIR,
)
from pipeline.context import PipelineContext
from pipeline.prompts.builder import build_digest_prompt
from pipeline.schemas import load_schema
from pipeline.sdk import structured_query

logger = logging.getLogger(__name__)

WEEK_DAYS = 7
MIN_POSTS_FOR_DIGEST = 2

# Three or four paragraphs per post is the whole point of the format, so the digest can
# only carry so many before it stops being a read and becomes an index again. The backlog
# left by the old eight-a-night regime means a week can currently hold seventy-five posts;
# once the cadence settles at one a day this cap will never be reached.
MAX_POSTS_IN_DIGEST = 8


def run() -> dict | None:
    """Write and publish the week's digest. Returns info dict or None if skipped."""
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    posts = _collect_week_posts(now)
    if len(posts) < MIN_POSTS_FOR_DIGEST:
        logger.info(
            "Only %d post(s) this week, not enough to write a digest about", len(posts)
        )
        return None

    news = _collect_week_news()

    ctx = PipelineContext()
    ctx.slot_type = "digest"
    ctx.posted_slugs = [slug for slug, _, _ in posts]

    _write_digest(ctx, posts, news, today_str)
    _illustrate_and_save(ctx)

    logger.info(
        "Weekly digest: %s (%d words, over %d posts and %d news items)",
        ctx.slug, len(ctx.article_text.split()), len(posts), len(news),
    )
    return {
        "type": "digest",
        "slug": ctx.slug,
        "url": f"{SITE_BASE_URL}/{ctx.slug}/",
        "post_count": len(posts),
        "news_count": len(news),
    }


def _write_digest(
    ctx: PipelineContext,
    posts: list[tuple[str, str, str]],
    news: list[dict],
    today_str: str,
) -> None:
    posts_text = "\n\n".join(
        f"slug: {slug}\ntitle: {title}\nwhat it said: {summary}"
        for slug, title, summary in posts
    )
    news_text = "\n".join(
        f"- {item.get('title', '')} ({item.get('source', '')}) {item.get('link', '')}"
        for item in news[:40]
    ) or "(the feeds were quiet this week)"

    system, prompt = build_digest_prompt(
        posts_text=posts_text,
        news_text=news_text,
        today_str=today_str,
        type_cfg=CONTENT_TYPES["digest"],
    )

    result = structured_query(
        prompt=prompt,
        system_prompt=system,
        schema=load_schema("generation"),
        model=MODEL_GENERATE,
    )

    ctx.title = result["title"]
    ctx.slug = result["slug"]
    ctx.article_text = result["article"]
    ctx.description = result.get("description", "")
    ctx.tags = result.get("tags", [])
    ctx.hashtags = result.get("hashtags", "")
    ctx.source_urls = result.get("source_urls", [])
    ctx.source_names = result.get("source_names", [])
    ctx.summary = result.get("summary", "")


def _illustrate_and_save(ctx: PipelineContext) -> None:
    """Same cover, teaser, save and deploy path as any other post."""
    from pipeline.stages import s6_generate_tg, s7_deploy, s7_save, s_comic_scene

    s_comic_scene.run(ctx)
    s6_generate_tg.run(ctx)
    s7_save.run(ctx)
    s7_deploy.run()


def _collect_week_posts(now: datetime) -> list[tuple[str, str, str]]:
    """Return (slug, title, summary) for posts published in the last week, oldest first.

    Summary rather than a body preview: the digest is meant to reflect on the week, and
    the first 300 characters of an article are its opening hook, which tells the model
    what the piece sounded like but not what it found.
    """
    cutoff = (now - timedelta(days=WEEK_DAYS)).strftime("%Y-%m-%d")
    summaries = _load_summaries()

    posts: list[tuple[str, str, str]] = []
    for md in sorted(CONTENT_DIR.glob("*.md")):
        text = md.read_text(encoding="utf-8", errors="replace")
        date = _frontmatter_value(text, "date")
        if not date or date < cutoff:
            continue
        slug = md.stem
        entry = summaries.get(slug, {})
        posts.append((
            slug,
            entry.get("title") or _frontmatter_value(text, "title") or slug,
            entry.get("summary") or _frontmatter_value(text, "description") or "",
        ))

    posts.sort(key=lambda p: p[0])
    if len(posts) > MAX_POSTS_IN_DIGEST:
        logger.warning(
            "%d posts this week — writing the digest about the last %d and leaving %d out",
            len(posts), MAX_POSTS_IN_DIGEST, len(posts) - MAX_POSTS_IN_DIGEST,
        )
        posts = posts[-MAX_POSTS_IN_DIGEST:]
    return posts


def _collect_week_news() -> list[dict]:
    """Headlines currently in the feeds.

    The feeds carry roughly the last week for health publishers, but they are a snapshot
    rather than an archive: an item that appeared and rolled off on Tuesday will not be
    here on Sunday. Good enough to give the digest the week's shape, not a record of it.
    """
    from pipeline.feeds import fetch_rss_headlines

    try:
        return fetch_rss_headlines()
    except Exception:
        logger.warning("Could not read the feeds for the digest", exc_info=True)
        return []


def _load_summaries() -> dict:
    """The per-article summaries the save stage accumulates in state/."""
    path = STATE_DIR / "summaries.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.warning("Could not read %s", path, exc_info=True)
        return {}


def _frontmatter_value(text: str, key: str) -> str:
    """Read one key out of the leading frontmatter block, ignoring the body."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return ""
    for line in lines[1:]:
        if line.strip() == "---":
            return ""
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip().strip('"')
    return ""
