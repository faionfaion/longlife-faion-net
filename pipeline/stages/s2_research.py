"""Stage 2: Research — search for health/longevity information on the assigned topic."""

from __future__ import annotations

import logging

from pipeline.config import MODEL_RESEARCH
from pipeline.context import PipelineContext
from pipeline.prompts.builder import build_research_prompt
from pipeline.sdk import agent_query

logger = logging.getLogger(__name__)


def run(ctx: PipelineContext) -> None:
    headlines_text = _format_headlines(ctx.news_items[:20])
    focus_text = _focus_for_type(ctx.slot_type)

    system, prompt = build_research_prompt(ctx, headlines_text, focus_text)

    ctx.research_text = agent_query(
        prompt=prompt,
        system_prompt=system,
        model=MODEL_RESEARCH,
        allowed_tools=["WebSearch", "WebFetch", "Read", "Glob"],
        timeout=300,
    )

    logger.info("Research complete: %d chars", len(ctx.research_text))


def _format_headlines(items: list[dict]) -> str:
    lines = []
    for item in items:
        lines.append(f"- [{item['source']}] {item['title']}")
        if item.get("description"):
            lines.append(f"  {item['description'][:200]}")
        if item.get("link"):
            lines.append(f"  URL: {item['link']}")
    return "\n".join(lines) if lines else "(no RSS headlines available)"


def _focus_for_type(slot_type: str) -> str:
    focuses = {
        "research": "latest peer-reviewed health research, clinical trials, meta-analyses",
        "guide": "step-by-step practical guide with evidence-based recommendations",
        "nutrition": "nutrition science, dietary research, food quality, supplements",
        "fitness": "exercise science, physical activity research, training methods",
        "mental": "mental health research, stress management, cognitive health",
        "longevity": "longevity science, aging research, biohacking, blue zones",
        "sleep": "sleep science, circadian rhythms, sleep hygiene research",
        "lifehack": "practical health lifehacks backed by scientific evidence",
        "digest": "summary of latest health research and breakthroughs",
    }
    return focuses.get(slot_type, focuses["research"])
