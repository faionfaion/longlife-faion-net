"""Image QA: inspect a generated image for artifacts via Claude vision.

Uses agent_query with Read tool — Claude reads the image file and returns
a structured assessment.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from pipeline.config import MODEL_IMAGE
from pipeline.sdk import agent_query

logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = """You are a strict quality-assurance reviewer for AI-generated illustrations.

Your job: flag actual GENERATION ARTIFACTS — not stylistic choices you personally dislike.

FLAG these (any severity → retry_recommended=true):
- ANATOMY ERRORS: extra limbs, missing limbs, merged limbs, wrong finger count on any visible hand, distorted hands, broken joints, impossible poses, warped bone structure
- FACE ERRORS: asymmetric eyes, merged faces, distorted features, wrong number of eyes/ears/noses
- HAND FINGERS: count fingers on every visible hand — 5 is correct, anything else is a hard fail
- TEXT GLITCHES: garbled letters, nonsensical words, broken symbols that were supposed to be readable
- OBJECT GLITCHES: floating objects, clipping, morphing, accidentally duplicated objects, items bleeding into each other
- RENDER GLITCHES: stray color spots/blobs, visible warping, pixelation artifacts, melted/smeared areas
- COMPOSITION BREAKS: important subject cut off by frame unintentionally

DO NOT flag:
- Body type (muscular, athletic, slender) if not explicitly wrong — that's a character design choice
- Color palette preferences
- Art style opinions (illustration vs realism)
- "Uncanny" feelings that aren't tied to a specific concrete defect
- Anything described in the original scene description as intended

Severity:
- "none" — clean, no actual artifacts
- "low" — one minor defect (small stray spot, slightly warped object)
- "high" — obvious (wrong finger count, extra limb, distorted face)

If ANY actual artifact is present → retry_recommended=true. But do not invent issues.

Output ONLY JSON, no prose."""


_JSON_SCHEMA_HINT = """{
  "counts": {
    "hands": 2,
    "arms": 2,
    "legs": 2,
    "heads": 1,
    "eyes": 2,
    "fingers_right_hand": 5,
    "fingers_left_hand": 5
  },
  "readable_text_present": false,
  "ok": false,
  "severity": "high",
  "issues": [
    "Character has 3 hands — the right arm ends in two separate hands",
    "Text on background poster is garbled"
  ],
  "retry_recommended": true
}"""


def analyze(image_path: Path, scene_context: str = "") -> dict:
    """Analyze an image for artifacts. Returns {ok, severity, issues, retry_recommended}.

    Args:
        image_path: Path to the generated image file.
        scene_context: Optional original scene description for context.

    Returns:
        Dict with keys: ok (bool), severity (str), issues (list[str]), retry_recommended (bool).
    """
    if not image_path.exists():
        logger.error("QA: image not found at %s", image_path)
        return {"ok": False, "severity": "high", "issues": ["Image file missing"], "retry_recommended": True}

    context_block = f"\n\nOriginal scene description (for reference):\n{scene_context[:1500]}" if scene_context else ""

    user_prompt = (
        f"Read the image at: {image_path}\n\n"
        f"FIRST, look carefully at the main character and answer these questions by counting what you "
        f"actually see (fill the `counts` object):\n"
        f"- How many hands does the character have?\n"
        f"- How many arms?\n"
        f"- How many legs?\n"
        f"- How many heads?\n"
        f"- How many eyes?\n"
        f"- How many fingers on the RIGHT hand?\n"
        f"- How many fingers on the LEFT hand?\n"
        f"(If a limb is hidden/cropped by the frame, count only what is visible and say so in issues — do "
        f"not assume.) Also set `readable_text_present` = true if ANY readable text, numbers, chart, label, "
        f"or screen appears in the image.\n\n"
        f"THEN inspect for any other artifact — distorted faces, merged/duplicated objects, garbled text, "
        f"floating props, warping, composition breaks.{context_block}\n\n"
        f"Return strict JSON matching this shape:\n{_JSON_SCHEMA_HINT}\n\n"
        f"A normal human has exactly 2 hands, 2 arms, 2 legs, 1 head, 2 eyes, and 5 fingers per visible hand. "
        f"Any deviation, OR any readable text present, is a hard fail (severity='high', retry_recommended=true). "
        f"If and only if the image is truly clean, set ok=true, severity='none', issues=[], retry_recommended=false."
    )

    try:
        text = agent_query(
            prompt=user_prompt,
            system_prompt=_SYSTEM_PROMPT,
            model=MODEL_IMAGE,
            allowed_tools=["Read"],
            timeout=300,
        )
    except Exception as e:
        # Fail CLOSED: if we cannot inspect the image, do NOT rubber-stamp it — force a retry.
        logger.error("QA agent_query failed: %s — failing closed (retry)", e)
        return {"ok": False, "severity": "high", "issues": [f"QA inspection failed: {e}"], "retry_recommended": True}

    result = _extract_json(text)
    if result is None:
        logger.warning("QA returned unparseable output — failing closed (retry): %r", text[:200])
        return {"ok": False, "severity": "high", "issues": ["QA output unparseable"], "retry_recommended": True}

    issues = [str(i) for i in result.get("issues", [])]
    severity = str(result.get("severity", "none"))
    ok = bool(result.get("ok", True))
    retry = bool(result.get("retry_recommended", False))

    # Cross-check the explicit anatomy counts — override a too-lenient verdict.
    expected = {"hands": 2, "arms": 2, "legs": 2, "heads": 1, "eyes": 2,
                "fingers_right_hand": 5, "fingers_left_hand": 5}
    counts = result.get("counts") or {}
    for key, want in expected.items():
        got = counts.get(key)
        if isinstance(got, int) and got != want:
            issues.append(f"Anatomy count off: {key}={got} (expected {want})")
            ok, retry, severity = False, True, "high"
    if result.get("readable_text_present") is True:
        issues.append("Readable text/labels present in image")
        ok, retry, severity = False, True, "high"

    logger.info(
        "Image QA: ok=%s, severity=%s, retry=%s, counts=%s, issues=%d — %s",
        ok, severity, retry, counts or "n/a", len(issues),
        "; ".join(issues)[:200] if issues else "clean",
    )

    return {"ok": ok, "severity": severity, "issues": issues, "retry_recommended": retry}


def _extract_json(text: str) -> dict | None:
    """Pull JSON object out of agent text output (may have surrounding prose)."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return None
    return None
