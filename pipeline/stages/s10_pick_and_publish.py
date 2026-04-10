"""Stage 10: Pick best unpublished article and publish to TG.

Used in 'publish' mode (9, 12, 15, 18).
Picks from pre-generated articles with ready TG captions (state/teasers/).
No LLM calls — purely mechanical publish.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from pipeline.config import (
    CONTENT_DIR, IMAGES_DIR, SITE_BASE_URL,
    SOUND_ON_END, SOUND_ON_START, STATE_DIR,
    TG_BOT_TOKEN, TG_CHANNEL_ID,
)
from pipeline.telegram import add_reaction, send_photo

logger = logging.getLogger(__name__)


def run() -> dict | None:
    """Pick best unpublished article, send pre-generated caption to TG."""
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    # Load today's TG publish state
    tg_state_file = STATE_DIR / "tg_published" / f"{today_str}.json"
    tg_published: dict = {}
    if tg_state_file.exists():
        tg_published = json.loads(tg_state_file.read_text(encoding="utf-8"))

    already_posted = set()
    for v in tg_published.values():
        if isinstance(v, str):
            already_posted.add(v)
        elif isinstance(v, dict):
            already_posted.add(v.get("slug", ""))

    # Find today's articles with pre-generated TG captions
    candidate = _find_next_candidate(today_str, already_posted)
    if not candidate:
        # Fallback: any article with a teaser not yet posted
        candidate = _find_any_candidate(already_posted)

    if not candidate:
        logger.info("No unpublished articles available for TG")
        return None

    slug, caption, image_path = candidate
    article_url = f"{SITE_BASE_URL}/{slug}/"

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
        _mark_tg_published(today_str, now.hour, slug, msg_id)
        logger.info("TG published: %s -> msg %d", slug, msg_id)
        return {"slug": slug, "msg_id": msg_id, "url": article_url}

    logger.error("Failed to publish %s to TG", slug)
    return None


def _find_next_candidate(today_str: str, exclude: set[str]) -> tuple[str, str, str] | None:
    """Find today's newest article with a pre-generated teaser, not yet posted."""
    teasers_dir = STATE_DIR / "teasers"
    if not teasers_dir.exists():
        return None

    # Get today's articles sorted by mtime (newest first)
    today_articles = []
    for md in sorted(CONTENT_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        text = md.read_text(encoding="utf-8")
        if f'date: "{today_str}"' not in text:
            continue
        slug = md.stem
        if slug in exclude:
            continue
        today_articles.append(slug)

    # Find first with teaser + image
    for slug in today_articles:
        result = _load_teaser_with_image(slug)
        if result:
            return result

    return None


def _find_any_candidate(exclude: set[str]) -> tuple[str, str, str] | None:
    """Fallback: find any article with teaser not yet posted."""
    teasers_dir = STATE_DIR / "teasers"
    if not teasers_dir.exists():
        return None

    for teaser_file in sorted(teasers_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        slug = teaser_file.stem
        if slug in exclude:
            continue
        result = _load_teaser_with_image(slug)
        if result:
            return result

    return None


def _load_teaser_with_image(slug: str) -> tuple[str, str, str] | None:
    """Load pre-generated TG caption and find image. Returns (slug, caption, image_path) or None."""
    teaser_file = STATE_DIR / "teasers" / f"{slug}.json"
    if not teaser_file.exists():
        return None

    teaser = json.loads(teaser_file.read_text(encoding="utf-8"))
    caption = teaser.get("tg_post", "")
    if not caption:
        return None

    image_path = _find_image(slug)
    if not image_path:
        return None

    return slug, caption, image_path


def _find_image(slug: str) -> str | None:
    for ext in (".jpg", ".jpeg", ".png"):
        p = IMAGES_DIR / f"{slug}{ext}"
        if p.exists():
            return str(p)
    return None


def _mark_tg_published(today_str: str, hour: int, slug: str, msg_id: int) -> None:
    tg_dir = STATE_DIR / "tg_published"
    tg_dir.mkdir(parents=True, exist_ok=True)
    state_file = tg_dir / f"{today_str}.json"

    data: dict = {}
    if state_file.exists():
        data = json.loads(state_file.read_text(encoding="utf-8"))

    data[str(hour)] = {"slug": slug, "msg_id": msg_id}
    state_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
