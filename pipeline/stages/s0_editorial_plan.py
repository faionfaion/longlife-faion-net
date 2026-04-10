"""Stage 0: Editorial planning — create daily article plan.

Runs once per day (first generate run or explicit 'plan' mode).
Analyzes past articles to avoid repetition, considers RSS headlines,
and creates a diverse editorial plan for the day.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pipeline.config import (
    CONTENT_DIR, MODEL_GENERATE, STATE_DIR,
)
from pipeline.feeds import fetch_rss_headlines
from pipeline.prompts.builder import build_editorial_prompt, build_plan_review_prompt
from pipeline.schemas import load_schema
from pipeline.sdk import structured_query

logger = logging.getLogger(__name__)


def run() -> dict:
    """Create editorial plan for today. Returns the plan dict."""
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    # Check if plan already exists for today
    plan_file = STATE_DIR / "plans" / f"{today_str}.json"
    if plan_file.exists():
        plan = json.loads(plan_file.read_text(encoding="utf-8"))
        logger.info("Editorial plan already exists for %s (%d articles)", today_str, len(plan.get("articles", [])))
        return plan

    # Gather context
    recent_summaries = _load_recent_articles(days=30)
    rss_headlines = _format_rss()
    today_articles = _load_today_articles(today_str)
    editor_notes = _load_editor_notes()

    system, prompt = build_editorial_prompt(
        today_str=today_str,
        day_of_week=now.strftime('%A'),
        recent_summaries=recent_summaries,
        today_articles=today_articles,
        rss_headlines=rss_headlines,
        editor_notes=editor_notes,
    )

    plan = structured_query(
        prompt=prompt,
        system_prompt=system,
        schema=load_schema("editorial_plan"),
        model=MODEL_GENERATE,
    )

    # Review & rebalance plan
    plan = _review_plan(plan, today_str, now.strftime('%A'), recent_summaries)

    # Save plan
    plan_dir = STATE_DIR / "plans"
    plan_dir.mkdir(parents=True, exist_ok=True)
    plan["date"] = today_str
    plan["created_at"] = now.isoformat()
    plan_file.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    # Clear editor notes after use
    if editor_notes:
        _clear_editor_notes()

    logger.info("Editorial plan created: %d articles for %s", len(plan.get("articles", [])), today_str)
    return plan


def get_next_topic(plan: dict, written_slugs: set[str]) -> dict | None:
    """Get the next unwritten topic from the plan."""
    written_file = STATE_DIR / "plans" / f"{plan.get('date', 'unknown')}_written.json"
    written_topics: list[str] = []
    if written_file.exists():
        written_topics = json.loads(written_file.read_text(encoding="utf-8"))

    for article in plan.get("articles", []):
        topic = article["topic"]
        if topic not in written_topics:
            # Mark as taken
            written_topics.append(topic)
            written_file.parent.mkdir(parents=True, exist_ok=True)
            written_file.write_text(json.dumps(written_topics, ensure_ascii=False), encoding="utf-8")
            return article

    return None


def _load_recent_articles(days: int = 30) -> str:
    """Load summaries of articles from the last N days, using stored summaries."""
    if not CONTENT_DIR.exists():
        return "(no articles yet)"

    # Load stored summaries
    summaries_file = STATE_DIR / "summaries.json"
    stored: dict = {}
    if summaries_file.exists():
        try:
            stored = json.loads(summaries_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            stored = {}

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    lines = []

    for md in sorted(CONTENT_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        text = md.read_text(encoding="utf-8")
        title = ""
        date = ""
        article_type = ""

        for line in text.split("\n"):
            if line.startswith("title:"):
                title = line.split('"')[1] if '"' in line else line.split(": ", 1)[1]
            elif line.startswith("date:"):
                date = line.split('"')[1] if '"' in line else line.split(": ", 1)[1]
            elif line.startswith("type:"):
                article_type = line.split('"')[1] if '"' in line else line.split(": ", 1)[1]

        if date and date < cutoff:
            continue

        slug = md.stem
        summary = stored.get(slug, {}).get("summary", "")
        if not summary:
            # Fallback: extract first 200 chars of body
            body_lines = text.split("---", 2)
            if len(body_lines) > 2:
                body = body_lines[2].strip().replace("\n", " ")[:200]
                summary = body + "..."

        lines.append(f"[{date}] ({article_type}) {title}\n  Summary: {summary}\n  Slug: {slug}")

        if len(lines) >= 80:
            break

    return "\n".join(lines) if lines else "(no recent articles)"


def _load_today_articles(today_str: str) -> str:
    """Load titles of articles already written today."""
    if not CONTENT_DIR.exists():
        return ""

    today_articles = []
    for md in CONTENT_DIR.glob("*.md"):
        text = md.read_text(encoding="utf-8")
        if f'date: "{today_str}"' in text:
            for line in text.split("\n"):
                if line.startswith("title:"):
                    title = line.split('"')[1] if '"' in line else line.split(": ", 1)[1]
                    today_articles.append(f"- {title}")
                    break

    return "\n".join(today_articles)


def _review_plan(plan: dict, today_str: str, day_of_week: str, recent_summaries: str) -> dict:
    """Review editorial plan for balance and diversity. Returns corrected plan."""
    articles = plan.get("articles", [])
    if len(articles) < 3:
        return plan

    plan_json = json.dumps(articles, ensure_ascii=False, indent=2)

    system, prompt = build_plan_review_prompt(
        plan_json=plan_json,
        today_str=today_str,
        day_of_week=day_of_week,
        recent_summaries=recent_summaries,
    )

    try:
        reviewed = structured_query(
            prompt=prompt,
            system_prompt=system,
            schema=load_schema("editorial_plan"),
            model=MODEL_GENERATE,
        )
        new_articles = reviewed.get("articles", [])
        if len(new_articles) >= 3:
            logger.info("Plan reviewed: %d -> %d articles", len(articles), len(new_articles))
            plan["articles"] = new_articles
        else:
            logger.warning("Plan review returned too few articles (%d), keeping original", len(new_articles))
    except Exception:
        logger.warning("Plan review failed, keeping original plan", exc_info=True)

    return plan


def _load_editor_notes() -> str:
    """Load editor-in-chief notes/wishes from state/editor_notes.md."""
    notes_file = STATE_DIR / "editor_notes.md"
    if not notes_file.exists():
        return ""
    text = notes_file.read_text(encoding="utf-8").strip()
    # Strip the template header (everything before and including "---")
    if "---" in text:
        text = text.split("---", 1)[1].strip()
    return text if text else ""


def _clear_editor_notes() -> None:
    """Clear editor notes after they've been used in the plan."""
    notes_file = STATE_DIR / "editor_notes.md"
    template = (
        "# Editor Notes\n\n"
        "Write your editorial wishes here. These will be prioritized in the next editorial plan.\n\n"
        "You can add:\n"
        "- Specific health topics or themes to cover\n"
        "- Links to research papers or health news\n"
        "- Special instructions for today's content\n"
        "- Topics to avoid or postpone\n\n"
        "---\n\n"
    )
    notes_file.write_text(template, encoding="utf-8")
    logger.info("Editor notes cleared after use")


def _format_rss() -> str:
    """Fetch and format current RSS headlines."""
    items = fetch_rss_headlines()
    lines = []
    for item in items[:30]:
        lines.append(f"- [{item['source']}] {item['title']}")
    return "\n".join(lines) if lines else "(no RSS available)"
