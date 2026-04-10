"""Pipeline context: shared state passed between stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PipelineContext:
    """Mutable context shared across all pipeline stages."""

    # Slot info
    slot_hour: int = 0
    slot_type: str = "research"  # research, guide, lifehack, nutrition, fitness, digest

    # Research
    news_items: list[dict] = field(default_factory=list)
    selected_topic: str = ""
    research_text: str = ""

    # Editorial plan (assigned topic from editorial plan stage)
    editorial_plan: dict = field(default_factory=dict)

    # Article
    article_text: str = ""
    title: str = ""
    slug: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    hashtags: str = ""
    source_urls: list[str] = field(default_factory=list)
    source_names: list[str] = field(default_factory=list)

    # Summary (for editorial dedup)
    summary: str = ""

    # Review
    review_approved: bool = False
    review_feedback: str = ""

    # TG post
    tg_post: str = ""
    tg_review_approved: bool = False

    # Image
    image_prompt: str = ""
    image_path: Path | None = None

    # Publish
    article_url: str = ""
    msg_id: int | None = None
    site_ok: bool = False

    # State
    posted_slugs: list[str] = field(default_factory=list)
