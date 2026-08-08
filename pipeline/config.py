"""Pipeline configuration: paths, models, constants."""

import os
from pathlib import Path

# Project root
ROOT = Path(__file__).resolve().parent.parent

# Directories
CONTENT_DIR = ROOT / "content"
STATE_DIR = ROOT / "state"
SCRIPTS_DIR = ROOT / "scripts"
PROMPTS_DIR = ROOT / "pipeline" / "prompts"
GATSBY_DIR = ROOT / "gatsby"
IMAGES_DIR = GATSBY_DIR / "static" / "images"
CHARACTER_DIR = ROOT / "assets" / "character"

# Cover imagery.
#
# "codex" drives the Codex CLI, which bills against the ChatGPT subscription. "openai"
# calls api.openai.com directly and needs credits on the account — that balance ran out on
# 22 July 2026 and took every cover with it, which is why codex is the default.
IMAGE_PROVIDER = os.environ.get("LONGLIFE_IMAGE_PROVIDER", "codex")

# Vita's turnaround sheets, handed to the image model to keep her recognisable between
# covers. Keyed by the `wardrobe` the scene director picks; "none" gets no reference at all.
CHARACTER_REFERENCES = {
    "scientist": CHARACTER_DIR / "vita-scientist-turnaround.png",
    "fitness": CHARACTER_DIR / "vita-fitness-turnaround.jpg",
}

# Her face in twelve moods, handed over as a second reference when the shot is close
# enough for the expression to read. Without it every cover lands in the same absorbed
# register, because that is what the turnaround sheets show her doing.
EXPRESSION_REFERENCE = CHARACTER_DIR / "vita-expressions.png"

# Scripts
SEND_POST = SCRIPTS_DIR / "send_post.py"
DEPLOY_SH = GATSBY_DIR / "deploy-gh.sh"

# Site
# Moved from longlife.faion.net on 8 August 2026. The old host 301s to this one, which
# is what keeps the links in already-sent Telegram posts working.
SITE_BASE_URL = "https://longlife.media"

# Single language — no translation pipeline needed
LANG = "ua"

# Models per stage (all Opus per project convention)
MODEL_COLLECT = "opus"
MODEL_RESEARCH = "opus"
MODEL_GENERATE = "opus"
MODEL_REVIEW = "opus"
MODEL_TG = "opus"
MODEL_IMAGE = "opus"  # image prompt generation
MODEL_VERIFY = "opus"

# Review loop limits
MAX_REVIEW_CYCLES = 3
MAX_TG_REVIEW_CYCLES = 2

# SDK retry config
RETRY_MAX_ATTEMPTS = 3
RETRY_BASE_DELAY = 5.0
RETRY_MAX_DELAY = 60.0

# Telegram
# Shared @nero_open_bot token, loaded from env (~/workspace/.env). The previous
# dedicated bot token was hardcoded here and started returning 401 Unauthorized
# (bot revoked), which silently killed TG publishing from late April 2026.
TG_BOT_TOKEN = os.environ.get("NERO_TG_BOT_TOKEN", "")
TG_CHANNEL_ID = "-1003845412300"
TG_CHANNEL_USERNAME = "long_life_media"
TG_BUTTON_LABEL = "Читати повністю \u2192"

# Silent mode: sound ON only during this window (Kyiv time)
SOUND_ON_START = 8
SOUND_ON_END = 22

# Max TG caption length (safe for multi-byte UTF-8)
MAX_TG_CAPTION = 900

# --- Publishing rhythm ---
#
# One post a day, and only one. This is a blog, not a wire: the previous shape wrote eight
# to ten articles a night and sent four a day to the channel, which reads as a feed no
# matter how the site is styled, and left several hundred pieces queued that nobody will
# ever see.
#
# The day decides what that one post is.

POSTS_PER_DAY = 1

# Python weekday numbers: Monday is 0.
ROUNDUP_WEEKDAY = 4  # Friday — the week's news on one topic, gathered
DIGEST_WEEKDAY = 6   # Sunday — the week in one piece, written long


def post_kind_for(weekday: int) -> str:
    """Which kind of post the given weekday carries."""
    if weekday == DIGEST_WEEKDAY:
        return "digest"
    if weekday == ROUNDUP_WEEKDAY:
        return "roundup"
    return "post"


GENERATE_HOUR = 3   # UTC, single overnight run
TG_PUBLISH_HOURS = [9]  # one send a day, after the site has been rebuilt
DIGEST_HOUR = 6     # UTC Sunday morning, before the day's publish

# Content type configs (word count ranges per type)
CONTENT_TYPES = {
    "research": {"min_words": 400, "max_words": 800},
    "guide": {"min_words": 800, "max_words": 2000},
    "lifehack": {"min_words": 200, "max_words": 400},
    "nutrition": {"min_words": 400, "max_words": 800},
    "fitness": {"min_words": 400, "max_words": 800},
    # The Friday roundup gathers the week on one theme; the Sunday digest retells the whole
    # week as a single piece, several paragraphs per post it covers, so it runs long.
    "roundup": {"min_words": 800, "max_words": 1400},
    "digest": {"min_words": 1500, "max_words": 3000},
}

# Author
AUTHOR_NAME = "\u0412\u0456\u0442\u0430 \u0417\u0435\u043b\u0435\u043d\u043a\u043e"
AUTHOR_NAME_EN = "Vita Zelenko"

# Topic hashtags
TOPIC_TAGS = {
    "nutrition": "#\u0425\u0430\u0440\u0447\u0443\u0432\u0430\u043d\u043d\u044f",
    "fitness": "#\u0424\u0456\u0442\u043d\u0435\u0441",
    "mental-health": "#\u041c\u0435\u043d\u0442\u0430\u043b\u044c\u043d\u0435\u0417\u0434\u043e\u0440\u043e\u0432\u044f",
    "sleep": "#\u0421\u043e\u043d",
    "longevity": "#\u0414\u043e\u0432\u0433\u043e\u043b\u0456\u0442\u0442\u044f",
    "biohacking": "#\u0411\u0456\u043e\u0445\u0430\u043a\u0456\u043d\u0433",
    "research": "#\u0414\u043e\u0441\u043b\u0456\u0434\u0436\u0435\u043d\u043d\u044f",
    "prevention": "#\u041f\u0440\u043e\u0444\u0456\u043b\u0430\u043a\u0442\u0438\u043a\u0430",
    "digest": "#\u0414\u0430\u0439\u0434\u0436\u0435\u0441\u0442",
    "guide": "#\u0413\u0430\u0439\u0434",
    "lifehack": "#\u041b\u0430\u0439\u0444\u0445\u0430\u043a",
}

# Topics list for editorial planning
TOPICS = [
    "nutrition",
    "fitness",
    "mental-health",
    "sleep",
    "longevity",
    "biohacking",
    "research",
    "prevention",
]

# RSS feeds for health news collection
RSS_FEEDS = {
    "moz_news": "https://moz.gov.ua/rss",
    "ukrinform_health": "https://www.ukrinform.ua/rss/block-zdorovja",
    "ukrinform_science": "https://www.ukrinform.ua/rss/block-nauka",
    "unian_health": "https://health.unian.ua/rss/all",
    "nv_health": "https://nv.ua/rss/health.xml",
    "bbc_health": "https://feeds.bbci.co.uk/news/health/rss.xml",
    "medicalnewstoday": "https://www.medicalnewstoday.com/rss",
    "who_news": "https://www.who.int/rss-feeds/news-english.xml",
}
