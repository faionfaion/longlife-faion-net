"""Stage 7a: Save article to disk.

Writes markdown content, copies image, saves TG teaser and summary
to state/, and commits the article to git.
"""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from pipeline.config import (
    AUTHOR_NAME, CONTENT_DIR, IMAGES_DIR,
    SITE_BASE_URL, STATE_DIR,
)
from pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


def run(ctx: PipelineContext) -> None:
    """Save article to content/, generate image, commit to git."""
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")

    # 0. Generate illustration image
    if ctx.image_prompt and not ctx.image_path:
        from pipeline.image_gen import generate_image
        comic_mode = bool(ctx.comic_scene)
        ctx.image_path = generate_image(ctx.image_prompt, ctx.slug, comic_mode=comic_mode)

    # 1. Write markdown article
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    md_path = CONTENT_DIR / f"{ctx.slug}.md"

    frontmatter = {
        "title": ctx.title,
        "slug": ctx.slug,
        "date": date_str,
        "type": ctx.slot_type,
        "lang": "ua",
        "tags": ctx.tags,
        "description": ctx.description,
        "author": AUTHOR_NAME,
        "source_urls": ctx.source_urls,
        "source_names": ctx.source_names,
        "image": f"/images/{ctx.slug}.jpg" if ctx.image_path else "",
        "tg_post": ctx.tg_post,
    }

    md_content = "---\n"
    for key, value in frontmatter.items():
        if isinstance(value, list):
            md_content += f"{key}:\n"
            for item in value:
                md_content += f'  - "{item}"\n'
        elif isinstance(value, str) and ("\n" in value or '"' in value):
            md_content += f"{key}: |\n"
            for line in value.split("\n"):
                md_content += f"  {line}\n"
        else:
            md_content += f'{key}: "{value}"\n'
    md_content += "---\n\n"
    md_content += ctx.article_text

    md_path.write_text(md_content, encoding="utf-8")
    logger.info("Article saved: %s", md_path)

    # 2. Save TG teaser to state
    teasers_dir = STATE_DIR / "teasers"
    teasers_dir.mkdir(parents=True, exist_ok=True)
    teaser_path = teasers_dir / f"{ctx.slug}.json"
    teaser_path.write_text(
        json.dumps({"slug": ctx.slug, "tg_post": ctx.tg_post, "url": f"{SITE_BASE_URL}/{ctx.slug}/"},
                    ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 3. Save summary to state/summaries.json
    summaries_file = STATE_DIR / "summaries.json"
    summaries: dict = {}
    if summaries_file.exists():
        summaries = json.loads(summaries_file.read_text(encoding="utf-8"))
    summaries[ctx.slug] = {
        "date": date_str,
        "title": ctx.title,
        "type": ctx.slot_type,
        "tags": ctx.tags,
        "summary": ctx.summary or ctx.description,
    }
    summaries_file.write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")

    # 4. Copy image if generated
    if ctx.image_path and ctx.image_path.exists():
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        dest = IMAGES_DIR / f"{ctx.slug}.jpg"
        if ctx.image_path.resolve() != dest.resolve():
            import shutil
            shutil.copy2(ctx.image_path, dest)
            logger.info("Image copied to: %s", dest)

    # 5. Git commit this article
    try:
        _git_commit(ctx)
    except Exception:
        logger.warning("Git commit failed for %s, continuing", ctx.slug, exc_info=True)


def _git_commit(ctx: PipelineContext) -> None:
    """Git add and commit the new article."""
    root = str(CONTENT_DIR.parent)
    subprocess.run(
        ["git", "add", "-A"],
        cwd=root, capture_output=True, timeout=30,
    )
    subprocess.run(
        ["git", "commit", "-m", f"content: {ctx.slug}"],
        cwd=root, capture_output=True, timeout=30,
    )
