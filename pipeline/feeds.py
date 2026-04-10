"""RSS feed fetcher for health and wellness news sources."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from urllib.request import Request, urlopen
from urllib.error import URLError

from pipeline.config import RSS_FEEDS

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (compatible; LongLifeBot/1.0; +https://longlife.faion.net)"
)


def fetch_rss_headlines(max_per_feed: int = 10) -> list[dict]:
    """Fetch headlines from all configured RSS feeds."""
    all_items = []

    for name, url in RSS_FEEDS.items():
        try:
            items = _fetch_single_feed(name, url, max_per_feed)
            all_items.extend(items)
            logger.info("Feed %s: %d items", name, len(items))
        except Exception:
            logger.warning("Failed to fetch feed %s: %s", name, url, exc_info=True)

    # Sort by date (newest first), deduplicate by title similarity
    all_items.sort(key=lambda x: x.get("date", ""), reverse=True)
    return _deduplicate(all_items)


def _fetch_single_feed(name: str, url: str, max_items: int) -> list[dict]:
    """Fetch and parse a single RSS feed."""
    req = Request(url, headers={"User-Agent": _USER_AGENT})
    with urlopen(req, timeout=15) as resp:
        data = resp.read()

    root = ET.fromstring(data)
    items = []

    # RSS 2.0 format
    for item in root.findall(".//item")[:max_items]:
        entry = {
            "source": name,
            "title": _text(item, "title"),
            "link": _text(item, "link"),
            "description": _clean_html(_text(item, "description")),
            "date": _text(item, "pubDate"),
        }
        if entry["title"]:
            items.append(entry)

    # Atom format fallback
    if not items:
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry_el in root.findall(".//atom:entry", ns)[:max_items]:
            link_el = entry_el.find("atom:link", ns)
            entry = {
                "source": name,
                "title": _text(entry_el, "atom:title", ns),
                "link": link_el.get("href", "") if link_el is not None else "",
                "description": _clean_html(
                    _text(entry_el, "atom:summary", ns)
                    or _text(entry_el, "atom:content", ns)
                ),
                "date": _text(entry_el, "atom:published", ns)
                        or _text(entry_el, "atom:updated", ns),
            }
            if entry["title"]:
                items.append(entry)

    return items


def _text(el: ET.Element, tag: str, ns: dict | None = None) -> str:
    """Get text content of a child element."""
    child = el.find(tag, ns) if ns else el.find(tag)
    return (child.text or "").strip() if child is not None else ""


def _clean_html(text: str) -> str:
    """Remove HTML tags from text."""
    import re
    return re.sub(r'<[^>]+>', '', text).strip()


def _deduplicate(items: list[dict], threshold: float = 0.7) -> list[dict]:
    """Remove items with very similar titles."""
    seen_titles: list[str] = []
    unique = []

    for item in items:
        title = item["title"].lower()
        is_dup = False
        for seen in seen_titles:
            if _similarity(title, seen) > threshold:
                is_dup = True
                break
        if not is_dup:
            seen_titles.append(title)
            unique.append(item)

    return unique


def _similarity(a: str, b: str) -> float:
    """Simple word-overlap similarity."""
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    return len(intersection) / min(len(words_a), len(words_b))
