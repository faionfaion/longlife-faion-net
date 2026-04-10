"""Generate mode: batch all articles for the day.

Orchestrates the full pipeline: editorial plan, RSS collection,
per-topic research/generation/review, save, deploy, verify.
"""

from __future__ import annotations

import json
import logging

from pipeline.config import MAX_REVIEW_CYCLES, STATE_DIR
from pipeline.context import PipelineContext
from pipeline.run_report import RunReport, time_stage
from pipeline.stages import (
    s0_editorial_plan,
    s1_collect,
    s2_research,
    s3_generate,
    s4_review,
    s5_revise,
    s6_generate_tg,
    s7_deploy,
    s7_save,
    s8_verify,
)

logger = logging.getLogger("pipeline")


def run(dry_run: bool = False) -> list[PipelineContext]:
    """Generate mode: batch all articles for the day.

    1. Create editorial plan (8-10 topics)
    2. Collect RSS context
    3. For each topic: research -> generate -> review -> save
    4. Deploy site once at the end
    """
    report = RunReport(dry_run=dry_run)
    report.begin()

    # Step 0: Editorial plan
    with time_stage(report, "editorial_plan"):
        plan = s0_editorial_plan.run()
        topics = plan.get("articles", [])
        logger.info("Editorial plan: %d topics", len(topics))

    # Step 1: Collect context (RSS + existing slugs)
    rss_items, posted_slugs = s1_collect.collect_context()

    # Step 2: Generate each article (skip already-written topics)
    completed: list[PipelineContext] = []
    written_topics = _load_written_topics(plan)

    for i, topic in enumerate(topics, 1):
        topic_label = topic.get("topic", "")
        if topic_label in written_topics:
            logger.info("=== Article %d/%d === SKIP (already written): %s", i, len(topics), topic_label[:50])
            continue

        logger.info("=== Article %d/%d ===", i, len(topics))
        ctx = _generate_one_article(
            topic=topic,
            rss_items=rss_items,
            posted_slugs=posted_slugs,
            report=report,
            dry_run=dry_run,
        )
        if ctx:
            completed.append(ctx)
            posted_slugs.append(ctx.slug)
            _mark_topic_written(plan, topic_label)

    logger.info("Generated %d/%d articles", len(completed), len(topics))

    # Step 3: Deploy site once (all articles at once)
    if completed and not dry_run:
        with time_stage(report, "deploy_site"):
            s7_deploy.run()

        # Verify a sample
        with time_stage(report, "verify"):
            s8_verify.run(completed[-1])

    # Report
    report.slug = ", ".join(c.slug for c in completed[:5])
    report.author = "LongLife Media"
    report.image_generated = any(c.image_path for c in completed)
    report.finish("ok" if completed else "empty")
    try:
        path = report.save()
        logger.info("Run report saved: %s", path)
    except Exception:
        logger.exception("Failed to save run report")

    return completed


def _review_loop(ctx: PipelineContext) -> None:
    """Article review loop: min 1 revision, max MAX_REVIEW_CYCLES."""
    for cycle in range(MAX_REVIEW_CYCLES):
        s4_review.run(ctx)
        if ctx.review_approved and cycle >= 1:
            logger.info("Article approved after %d revision(s)", cycle)
            break
        s5_revise.run(ctx)
        logger.info("=== Review cycle %d/%d complete ===", cycle + 1, MAX_REVIEW_CYCLES)
    else:
        logger.warning("Max review cycles (%d) reached, proceeding", MAX_REVIEW_CYCLES)


def _generate_one_article(
    topic: dict,
    rss_items: list[dict],
    posted_slugs: list[str],
    report: RunReport,
    dry_run: bool = False,
) -> PipelineContext | None:
    """Generate a single article for one editorial topic.

    Returns the populated context on success, or None on failure.
    """
    ctx = PipelineContext()
    ctx.editorial_plan = topic
    ctx.slot_type = topic.get("type", "research")
    ctx.news_items = rss_items
    ctx.posted_slugs = posted_slugs

    topic_label = topic.get("topic", "unknown")[:60]

    try:
        logger.info("--- Article: [%s] %s ---", ctx.slot_type, topic_label)

        with time_stage(report, f"research:{topic_label[:30]}"):
            s2_research.run(ctx)

        with time_stage(report, f"generate:{topic_label[:30]}"):
            s3_generate.run(ctx)

        with time_stage(report, f"review:{topic_label[:30]}"):
            _review_loop(ctx)

        with time_stage(report, f"tg_caption:{topic_label[:30]}"):
            s6_generate_tg.run(ctx)

        if not dry_run:
            with time_stage(report, f"save:{topic_label[:30]}"):
                s7_save.run(ctx)

        logger.info("Article ready: %s (%s)", ctx.slug, ctx.title[:50])
        return ctx

    except Exception:
        logger.exception("Failed to generate article: %s", topic_label)
        return None


def _load_written_topics(plan: dict) -> set[str]:
    """Load set of already-written topic labels for today's plan."""
    written_file = STATE_DIR / "plans" / f"{plan.get('date', 'unknown')}_written.json"
    if written_file.exists():
        return set(json.loads(written_file.read_text(encoding="utf-8")))
    return set()


def _mark_topic_written(plan: dict, topic_label: str) -> None:
    """Mark a topic as written in the tracking file."""
    written_file = STATE_DIR / "plans" / f"{plan.get('date', 'unknown')}_written.json"
    written: list[str] = []
    if written_file.exists():
        written = json.loads(written_file.read_text(encoding="utf-8"))
    written.append(topic_label)
    written_file.parent.mkdir(parents=True, exist_ok=True)
    written_file.write_text(json.dumps(written, ensure_ascii=False), encoding="utf-8")
