"""Prompt builder: renders Jinja2 templates into (system, user) prompt pairs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from pipeline.context import PipelineContext

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    keep_trailing_newline=True,
    trim_blocks=False,
    lstrip_blocks=False,
)

SPLIT_MARKER = "===SPLIT==="


def render(template_name: str, **kwargs: Any) -> tuple[str, str]:
    """Render a template and split into (system_prompt, user_prompt).

    The template must contain ===SPLIT=== to separate system from user prompt.
    """
    tmpl = _env.get_template(template_name)
    text = tmpl.render(**kwargs)
    if SPLIT_MARKER not in text:
        raise ValueError(f"Template {template_name} missing {SPLIT_MARKER} marker")
    system_raw, user_raw = text.split(SPLIT_MARKER, 1)

    # Strip outer <system> tags and whitespace
    system = system_raw.strip()
    if system.startswith("<system>"):
        system = system[len("<system>"):]
    if system.endswith("</system>"):
        system = system[:-len("</system>")]
    system = system.strip()

    user = user_raw.strip()
    return system, user


# ---- Convenience functions per stage ----

def build_editorial_prompt(
    today_str: str,
    day_of_week: str,
    recent_summaries: str,
    today_articles: str,
    rss_headlines: str,
    editor_notes: str = "",
    backlog_candidates: str = "",
) -> tuple[str, str]:
    """Build s0 editorial plan prompt."""
    return render(
        "s0_editorial_plan.xml.j2",
        today_str=today_str,
        day_of_week=day_of_week,
        recent_summaries=recent_summaries,
        today_articles=today_articles,
        rss_headlines=rss_headlines,
        editor_notes=editor_notes,
        backlog_candidates=backlog_candidates,
    )


def build_plan_review_prompt(
    plan_json: str,
    today_str: str,
    day_of_week: str,
    recent_summaries: str,
) -> tuple[str, str]:
    """Build s0b plan review prompt."""
    return render(
        "s0b_plan_review.xml.j2",
        plan_json=plan_json,
        today_str=today_str,
        day_of_week=day_of_week,
        recent_summaries=recent_summaries,
    )


def build_prioritize_prompt(
    today_str: str,
    day_of_week: str,
    slot_brief: str,
    topics_text: str,
    recent_summaries: str,
) -> tuple[str, str]:
    """Build s0c topic prioritisation prompt."""
    return render(
        "s0c_prioritize.xml.j2",
        today_str=today_str,
        day_of_week=day_of_week,
        slot_brief=slot_brief,
        topics_text=topics_text,
        recent_summaries=recent_summaries,
    )


def build_research_prompt(ctx: PipelineContext, headlines_text: str, focus_text: str) -> tuple[str, str]:
    """Build s2 research prompt."""
    return render(
        "s2_research.xml.j2",
        ctx=ctx,
        headlines_text=headlines_text,
        focus_text=focus_text,
    )


def build_generate_prompt(
    ctx: PipelineContext,
    type_cfg: dict,
    site_base_url: str,
    existing_articles_text: str,
) -> tuple[str, str]:
    """Build s3 article generation prompt."""
    return render(
        "s3_generate.xml.j2",
        ctx=ctx,
        type_cfg=type_cfg,
        site_base_url=site_base_url,
        existing_articles_text=existing_articles_text,
    )


def build_text_editor_prompt(
    ctx: PipelineContext,
    author_name: str,
    type_cfg: dict,
) -> tuple[str, str]:
    """Build s3b text editor prompt."""
    # The editor gets the citation map so it can keep [n] pointing where it pointed, and the
    # one-line description is the only on-record detail it may pull into the prose. Pad
    # rather than zip straight: the arrays come back ragged often enough, and a short zip
    # would silently hide the tail sources from a pass that must not touch their numbers.
    descriptions = list(ctx.source_descriptions)
    descriptions += [""] * (len(ctx.source_names) - len(descriptions))
    sources_zip = list(zip(ctx.source_names, descriptions))
    return render(
        "s3b_text_editor.xml.j2",
        ctx=ctx,
        author_name=author_name,
        type_cfg=type_cfg,
        sources_zip=sources_zip,
    )


def build_review_prompt(ctx: PipelineContext, author_name: str) -> tuple[str, str]:
    """Build s4 review prompt."""
    sources_zip = list(zip(ctx.source_names, ctx.source_urls))
    return render(
        "s4_review.xml.j2",
        ctx=ctx,
        author_name=author_name,
        sources_zip=sources_zip,
    )


def build_revise_prompt(ctx: PipelineContext, author_name: str) -> tuple[str, str]:
    """Build s5 revision prompt."""
    return render(
        "s5_revise.xml.j2",
        ctx=ctx,
        author_name=author_name,
    )


def build_tg_post_prompt(ctx: PipelineContext) -> tuple[str, str]:
    """Build s6 TG caption prompt."""
    return render(
        "s6_tg_post.xml.j2",
        ctx=ctx,
    )


def build_comic_scene_prompt(ctx: PipelineContext) -> tuple[str, str]:
    """Build comic scene prompt for article illustration."""
    return render(
        "s_comic_scene.xml.j2",
        ctx=ctx,
    )


def build_digest_prompt(
    posts_text: str,
    news_text: str,
    today_str: str,
    type_cfg: dict,
) -> tuple[str, str]:
    """Build the weekly digest prompt."""
    return render(
        "s11_digest.xml.j2",
        posts_text=posts_text,
        news_text=news_text,
        today_str=today_str,
        type_cfg=type_cfg,
    )
