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
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pipeline.config import (
    CONTENT_DIR, IMAGES_DIR, SITE_BASE_URL,
    SOUND_ON_END, SOUND_ON_START, STATE_DIR,
    TG_BOT_TOKEN, TG_CHANNEL_ID,
)
from pipeline.telegram import add_reaction, send_photo

logger = logging.getLogger(__name__)

# How far down the queue to look for an article whose page is live. Deep enough to get past
# a night's worth of freshly written pieces the site has not picked up, shallow enough that
# a genuinely broken site fails fast instead of walking four hundred articles.
MAX_CANDIDATES_CHECKED = 15


def run() -> dict | None:
    """Pick best unpublished article, send pre-generated caption to TG."""
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    already_posted = _all_posted_slugs()

    candidate = _pick_live_candidate(today_str, already_posted)

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


def _pick_live_candidate(
    today_str: str, already_posted: set[str]
) -> tuple[str, str, str] | None:
    """First unposted article whose page is actually live on the site.

    Generation and serving happen on different machines: articles are written overnight on
    one, and the other rebuilds the site on its own schedule. An article can therefore be
    ready to post hours before its page exists, and a post whose "read more" link 404s is
    worse than a quiet slot — especially since there are a hundred older articles that are
    live and have never been sent.

    Checked candidate by candidate rather than up front, because the walk skips a long run
    of articles that have no cover before it reaches anything postable.
    """
    seen: set[str] = set(already_posted)

    for _ in range(MAX_CANDIDATES_CHECKED):
        candidate = _find_next_candidate(today_str, seen) or _find_any_candidate(seen)
        if not candidate:
            return None

        slug = candidate[0]
        if _page_is_live(slug):
            return candidate

        logger.warning(
            "Skipping %s: its page is not on the site yet (the web host has not rebuilt "
            "since it was written)", slug,
        )
        seen.add(slug)

    logger.error(
        "Checked %d candidates and none had a live page — the site build is behind",
        MAX_CANDIDATES_CHECKED,
    )
    return None


def _page_is_live(slug: str) -> bool:
    """Whether the article's page answers on the public site."""
    url = f"{SITE_BASE_URL}/{slug}/"
    req = Request(url, method="HEAD", headers={"User-Agent": "LongLifePublish/1.0"})
    try:
        with urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except HTTPError as e:
        if e.code == 404:
            return False
        # Anything else — a 5xx, a redirect loop — is about the site, not this article.
        # Treat it as live rather than letting an outage silence the channel.
        logger.warning("Liveness check for %s got HTTP %s, assuming live", slug, e.code)
        return True
    except URLError as e:
        logger.warning("Liveness check for %s failed (%s), assuming live", slug, e)
        return True


def _all_posted_slugs() -> set[str]:
    """Every slug ever sent to the channel, across all daily state files.

    Dedup used to read only today's file. The picker walks the teaser list newest-first and
    takes the first entry it has not posted *today*, so every morning it started at the top
    again and re-sent the same four articles. That ran for 17 days — 68 posts, 4 distinct
    articles — because image generation had stalled and the newer teasers were all skipped
    for having no cover, which pinned the walk to the same place in the list every time.
    """
    posted: set[str] = set()
    tg_dir = STATE_DIR / "tg_published"
    if not tg_dir.exists():
        return posted

    for state_file in sorted(tg_dir.glob("*.json")):
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            # A corrupt day costs us a possible repeat, not the whole publish run.
            logger.warning("Unreadable TG publish state, ignoring: %s", state_file.name)
            continue
        entries = data.values() if isinstance(data, dict) else data
        for entry in entries:
            if isinstance(entry, str):
                posted.add(entry)
            elif isinstance(entry, dict) and entry.get("slug"):
                posted.add(entry["slug"])
    return posted


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
