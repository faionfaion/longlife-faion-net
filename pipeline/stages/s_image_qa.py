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
  "ok": false,
  "severity": "high",
  "issues": [
    "Left hand has 6 fingers",
    "Text on bottle is garbled"
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
        f"Inspect it for ANY artifact — anatomy errors, distorted faces/hands, garbled text, "
        f"style breaks, object glitches, composition issues. "
        f"Count fingers on every visible hand. Verify limb count.{context_block}\n\n"
        f"Return strict JSON matching this shape:\n{_JSON_SCHEMA_HINT}\n\n"
        f"If the image is perfect, set ok=true, severity='none', issues=[], retry_recommended=false. "
        f"Otherwise list every specific issue."
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
        logger.error("QA agent_query failed: %s", e)
        return {"ok": True, "severity": "none", "issues": [], "retry_recommended": False}

    result = _extract_json(text)
    if result is None:
        logger.warning("QA returned unparseable output, assuming OK: %r", text[:200])
        return {"ok": True, "severity": "none", "issues": [], "retry_recommended": False}

    issues = result.get("issues", [])
    severity = result.get("severity", "none")
    ok = result.get("ok", True)
    retry = result.get("retry_recommended", False)

    logger.info(
        "Image QA: ok=%s, severity=%s, retry=%s, issues=%d — %s",
        ok, severity, retry, len(issues),
        "; ".join(issues)[:200] if issues else "clean",
    )

    return {
        "ok": bool(ok),
        "severity": str(severity),
        "issues": [str(i) for i in issues],
        "retry_recommended": bool(retry),
    }


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
