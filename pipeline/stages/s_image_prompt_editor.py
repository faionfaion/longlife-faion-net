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
1. ANATOMY EXPLICITLY: state "exactly two arms, two hands with five fingers each, two legs, one head, two eyes, natural human proportions". The model often adds extra limbs, hands, or fingers — always state the correct count positively.
2. SIMPLE HANDS: describe ONE clear hand action, or both hands doing the SAME thing. NEVER describe one hand pointing/gesturing at something while the other holds a prop — split-hand gestures are the #1 trigger for extra-hand and duplicated-limb artifacts. If the input has such a pose, rewrite it into a single simple action.
3. ENVIRONMENT & ACTION OVER PORTRAIT: place the character fully inside a real, populated environment, doing a real action (walking, cooking, carrying, climbing, stretching). Prefer WIDE or MEDIUM framing with visible surroundings and, when it fits, other people around. Avoid empty centered close-up portraits unless the input explicitly calls for a facial/emotional focus.
4. NO READABLE TEXT: the model cannot render text (especially Cyrillic) and produces garbled glyphs. Strip every request for readable text, numbers, charts, graphs, forest plots, book spines, labels, posters, whiteboards, and screens/tablets/phones showing data. State positively: "a clean illustration with no text, numbers, or charts anywhere". Replace any data-bearing prop with a plain physical object.
5. ORDER MATTERS: subject first → action → environment → lighting → style. Most-important details go first.
6. AVOID AMBIGUITY: no "or", "might be", "maybe", "possibly". Replace with specific choices.
7. POSITIVE FRAMING: the model treats all words as things to include. Instead of "no extra arms", say "a single pair of arms, anatomically correct".
8. CONCRETE OVER ABSTRACT: "soft afternoon sunlight from the left" beats "nice lighting".
9. PRESERVE CHARACTER DETAILS: keep the character's appearance (clothing, hair, tattoos, accessories) verbatim — but you MAY change framing, setting, action, and props to satisfy rules 2-4.
10. KEEP LENGTH REASONABLE: 150-300 words. Longer prompts dilute attention.

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
        "The previous image had artifacts. Before rewriting, DIAGNOSE the prompt: for each issue, identify "
        "which specific phrase or instruction in the PREVIOUS PROMPT most likely caused it. Common causes:\n"
        "- extra/duplicated hands or limbs ← a split-hand pose (one hand points/gestures while the other holds "
        "a prop), a busy pose, or too many simultaneous actions\n"
        "- garbled text/glyphs ← any prop or background element that implies readable text, numbers, charts, "
        "screens, labels, book spines, or posters\n"
        "- duplicated objects (e.g. two smartwatches) ← the accessory described ambiguously or twice\n"
        "- floating/clipping props ← an object described as held but not clearly attached to one hand\n\n"
        "Then rewrite the prompt to REMOVE the root cause, not just to add more anatomy words. Simplify the "
        "pose to one clear action with unambiguous hands, replace any text/data-bearing prop with a plain "
        "physical object, and keep the character's appearance verbatim.\n\n"
        f"ORIGINAL SCENE:\n{raw_prompt}\n\n"
        f"PREVIOUS (FLAWED) PROMPT:\n{previous_prompt}\n\n"
        f"ISSUES FOUND IN THE IMAGE:\n{issues_block}\n\n"
        "Put your root-cause diagnosis in `reasoning`, and the corrected prompt in `prompt`."
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
