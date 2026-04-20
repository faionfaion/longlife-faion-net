"""Image prompt editor: optimize, revise, simplify prompts for gpt-image-1.

Three modes:
- optimize(): first pass — take raw scene description and produce an optimized prompt
- revise(): second pass — given QA feedback, rewrite prompt to fix artifacts
- simplify(): final fallback — strip complexity, keep only essential subject
"""

from __future__ import annotations

import logging

from pipeline.config import MODEL_IMAGE
from pipeline.sdk import structured_query

logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = """You are an expert prompt engineer for OpenAI's gpt-image-1 model.

Best practices for this model:
1. ANATOMY EXPLICITLY: "two hands with exactly five fingers each, one head, two eyes, natural proportions". The model often adds extra limbs or fingers — always state the correct count positively.
2. ORDER MATTERS: subject first → pose → environment → lighting → style. Most-important details go first.
3. AVOID AMBIGUITY: no "or", "might be", "maybe", "possibly". Replace with specific choices.
4. POSITIVE FRAMING: the model treats all words as things to include. Instead of "no extra arms", say "a single pair of arms, anatomically correct". Instead of "no text", say "clean illustration with no text overlays".
5. CONCRETE OVER ABSTRACT: "soft afternoon sunlight from the left" beats "nice lighting".
6. SINGLE FOCAL POINT: one clear subject, one clear action.
7. PRESERVE CHARACTER DETAILS: if the input describes a specific character (clothing, hair, tattoos, accessories) — keep them verbatim, don't paraphrase.
8. KEEP LENGTH REASONABLE: 150-300 words. Longer prompts dilute attention.

Output JSON only."""


_SCHEMA = {
    "type": "object",
    "properties": {
        "prompt": {
            "type": "string",
            "description": "The optimized image generation prompt, ready to send to gpt-image-1.",
        },
        "reasoning": {
            "type": "string",
            "description": "Brief note on what was changed and why (1-2 sentences).",
        },
    },
    "required": ["prompt", "reasoning"],
}


def optimize(raw_prompt: str) -> str:
    """First pass: rewrite raw scene prompt with anatomy/composition best practices.

    Input: raw prompt built from scene_description + character + pose etc.
    Output: optimized prompt ready for gpt-image-1.
    """
    user_prompt = (
        "Rewrite the following image prompt applying best practices for gpt-image-1. "
        "Preserve every concrete detail about the character (appearance, clothes, props). "
        "Add explicit anatomy constraints. Tighten composition.\n\n"
        f"INPUT PROMPT:\n{raw_prompt}"
    )

    result = structured_query(
        prompt=user_prompt,
        system_prompt=_SYSTEM_PROMPT,
        schema=_SCHEMA,
        model=MODEL_IMAGE,
    )

    optimized = result.get("prompt", raw_prompt).strip()
    logger.info("Prompt optimized: %s", result.get("reasoning", "")[:100])
    return optimized


def revise(raw_prompt: str, previous_prompt: str, qa_issues: list[str]) -> str:
    """Second pass: revise prompt to fix specific artifacts found by QA.

    Args:
        raw_prompt: Original scene description (source of truth for content).
        previous_prompt: The prompt that produced the flawed image.
        qa_issues: List of specific issues found in the image.
    """
    issues_block = "\n".join(f"- {i}" for i in qa_issues)
    user_prompt = (
        "The previous image had artifacts. Rewrite the prompt to fix them while preserving "
        "the character and scene content. Be MORE explicit about anatomy where artifacts occurred.\n\n"
        f"ORIGINAL SCENE:\n{raw_prompt}\n\n"
        f"PREVIOUS (FLAWED) PROMPT:\n{previous_prompt}\n\n"
        f"ISSUES FOUND IN THE IMAGE:\n{issues_block}\n\n"
        "Produce a revised prompt that directly addresses every issue."
    )

    result = structured_query(
        prompt=user_prompt,
        system_prompt=_SYSTEM_PROMPT,
        schema=_SCHEMA,
        model=MODEL_IMAGE,
    )

    revised = result.get("prompt", previous_prompt).strip()
    logger.info("Prompt revised: %s", result.get("reasoning", "")[:100])
    return revised


def simplify(raw_prompt: str) -> str:
    """Final fallback: produce the simplest possible prompt that still matches the scene.

    Strip optional details (background props, color notes, secondary props).
    Keep only: character essentials + main action + basic setting + anatomy constraints.
    """
    user_prompt = (
        "The previous attempts produced artifacts. Create the SIMPLEST possible prompt that still "
        "depicts this scene. Remove every non-essential detail (secondary props, color notes, "
        "background clutter). Keep only: character essentials (appearance, main clothing), one clear "
        "action, minimal setting, explicit anatomy.\n\n"
        f"ORIGINAL SCENE:\n{raw_prompt}\n\n"
        "Output the simplified prompt. Aim for 80-150 words."
    )

    result = structured_query(
        prompt=user_prompt,
        system_prompt=_SYSTEM_PROMPT,
        schema=_SCHEMA,
        model=MODEL_IMAGE,
    )

    simplified = result.get("prompt", raw_prompt).strip()
    logger.info("Prompt simplified: %s", result.get("reasoning", "")[:100])
    return simplified
