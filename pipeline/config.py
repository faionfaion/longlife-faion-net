"""Pipeline configuration: paths, models, constants."""

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

# Scripts
SEND_POST = SCRIPTS_DIR / "send_post.py"
DEPLOY_SH = GATSBY_DIR / "deploy-gh.sh"

# Site
SITE_BASE_URL = "https://longlife.faion.net"

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
TG_BOT_TOKEN = "8578996384:AAFhkTHh_D40VdCc7em5U9taM5a-o00JzaA"
TG_CHANNEL_ID = "-1003845412300"
TG_CHANNEL_USERNAME = "long_life_media"
TG_BUTTON_LABEL = "Читати повністю \u2192"

# Silent mode: sound ON only during this window (Kyiv time)
SOUND_ON_START = 8
SOUND_ON_END = 22

# Max TG caption length (safe for multi-byte UTF-8)
MAX_TG_CAPTION = 900

# Batch generation: runs once in the morning, generates all articles for the day
GENERATE_HOUR = 7  # UTC, single morning run

# TG publish schedule — mechanical publish of pre-generated articles
TG_PUBLISH_HOURS = [9, 12, 15, 18]

# Digest hour — compile day's best articles into one TG post
DIGEST_HOUR = 20

# Content type configs (word count ranges per type)
CONTENT_TYPES = {
    "research": {"min_words": 400, "max_words": 800},
    "guide": {"min_words": 800, "max_words": 2000},
    "lifehack": {"min_words": 200, "max_words": 400},
    "nutrition": {"min_words": 400, "max_words": 800},
    "fitness": {"min_words": 400, "max_words": 800},
    "digest": {"min_words": 500, "max_words": 1000},
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
