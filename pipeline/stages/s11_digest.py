"""Stage 11: Evening digest — compile today's best articles into one TG post.

Used in 'digest' mode (20:00).
Reads all articles published today, generates a digest caption with links.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from pipeline.config import (
    CONTENT_DIR, IMAGES_DIR, MODEL_TG, SITE_BASE_URL,
    SOUND_ON_END, SOUND_ON_START, STATE_DIR,
    TG_BOT_TOKEN, TG_CHANNEL_ID,
)
from pipeline.prompts.builder import build_digest_prompt
from pipeline.schemas import load_schema
from pipeline.sdk import structured_query
from pipeline.telegram import add_reaction, send_photo

logger = logging.getLogger(__name__)


def run() -> dict | None:
    """Generate and publish evening digest to TG. Returns info dict or None."""
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    # Collect today's articles
    articles = _collect_today_articles(today_str)
    if len(articles) < 3:
        logger.info("Only %d articles today, skipping digest", len(articles))
        return None

    # Generate digest via LLM
    caption = _generate_digest(articles, today_str)

    # Find a representative image (use the newest article's image)
    image_path = None
    for slug, _, _ in articles:
        img = _find_image(slug)
        if img:
            image_path = img
            break

    if not image_path:
        logger.warning("No image found for digest")
        return None

    # Determine silent mode
    kyiv_hour = (now.hour + 3) % 24  # UTC+3 for Kyiv
    silent = not (SOUND_ON_START <= kyiv_hour < SOUND_ON_END)

    # Publish
    msg_id = send_photo(
        chat_id=TG_CHANNEL_ID,
        image_path=image_path,
        caption=caption,
        bot_token=TG_BOT_TOKEN,
        silent=silent,
    )

    if msg_id:
        add_reaction(TG_CHANNEL_ID, msg_id, "\U0001f525", TG_BOT_TOKEN)
        logger.info("Digest published: msg %d (%d articles)", msg_id, len(articles))
        return {"type": "digest", "msg_id": msg_id, "article_count": len(articles)}

    logger.error("Failed to publish digest")
    return None


def _collect_today_articles(today_str: str) -> list[tuple[str, str, str]]:
    """Return (slug, title, body_preview) for today's articles."""
    articles = []
    for md in sorted(CONTENT_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        text = md.read_text(encoding="utf-8")
        if f'date: "{today_str}"' not in text:
            continue
        slug = md.stem
        title = ""
        for line in text.split("\n"):
            if line.startswith("title:"):
                title = line.split('"')[1] if '"' in line else line.split(": ", 1)[1]
                break
        # Get first 300 chars of body
        lines = text.split("\n")
        in_fm = False
        body_start = 0
        for i, line in enumerate(lines):
            if line.strip() == "---":
                if in_fm:
                    body_start = i + 1
                    break
                in_fm = True
        body = "\n".join(lines[body_start:])[:300]
        articles.append((slug, title, body))
    return articles


def _find_image(slug: str) -> str | None:
    for ext in (".jpg", ".jpeg", ".png"):
        p = IMAGES_DIR / f"{slug}{ext}"
        if p.exists():
            return str(p)
    return None


def _generate_digest(articles: list[tuple[str, str, str]], today_str: str) -> str:
    articles_text = "\n".join(
        f"- slug: {slug}\n  title: {title}\n  preview: {body[:150]}"
        for slug, title, body in articles
    )

    system, prompt = build_digest_prompt(articles_text, today_str)

    result = structured_query(
        prompt=prompt,
        system_prompt=system,
        schema=load_schema("digest"),
        model=MODEL_TG,
    )

    intro = result["intro"]
    items = result.get("items", [])
    outro = result.get("outro", "")

    # Build digest caption
    item_lines = []
    for item in items[:10]:
        emoji = item.get("emoji", "\u2022")
        title = item["title"]
        slug = item["slug"]
        url = f"{SITE_BASE_URL}/{slug}/"
        item_lines.append(f'{emoji} <a href="{url}">{title}</a>')

    parts = [
        "<b>\U0001f4f0 Дайджест дня</b>",
        "",
        intro,
        "",
        "\n\n".join(item_lines),
        "",
        outro,
        "",
        '<a href="https://t.me/long_life_media">\U0001f33f LongLife Media</a>',
    ]

    return "\n".join(parts)
