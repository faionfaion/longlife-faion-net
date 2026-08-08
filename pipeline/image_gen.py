"""Cover image generation.

Two backends, chosen by config.IMAGE_PROVIDER: the Codex CLI (default, bills against the
ChatGPT subscription) and api.openai.com (needs credits, which ran out on 22 July 2026).
Both hand off to the same JPEG conversion, so the site and Telegram see one shape of file
whichever produced it.

The prompt arrives fully built from s_comic_scene; this module does not compose it.
"""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path

import requests

from pipeline.config import IMAGE_PROVIDER, IMAGES_DIR

logger = logging.getLogger(__name__)

def _load_openai_key() -> str:
    """Load OpenAI API key from env or ~/workspace/.env."""
    key = os.environ.get("OPENAI_API_KEY", "")
    if key:
        return key
    env_file = Path.home() / "workspace" / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("OPENAI_API_KEY="):
                return line.split("=", 1)[1].strip()
    return ""

OPENAI_API_KEY = _load_openai_key()

_PARTIALS_DIR = Path(__file__).resolve().parent / "prompts" / "templates" / "_partials"
_STYLE_FILE = _PARTIALS_DIR / "image_style.txt"

# Only reached when a caller passes a bare scene with comic_mode=False. The normal path
# arrives with the style already folded in by s_comic_scene.
_DEFAULT_STYLE = (
    "Editorial photograph for a health publication, no people in frame. Natural light, "
    "muted neutral grade, shallow depth of field. No illustration, no 3D render. No text, "
    "lettering or logos anywhere in frame. "
)


def _load_style_prefix() -> str:
    """Load the still-life style prefix from its editable partial."""
    if _STYLE_FILE.exists():
        return _STYLE_FILE.read_text(encoding="utf-8").strip() + " "
    return _DEFAULT_STYLE


def generate_image(
    prompt: str,
    slug: str,
    comic_mode: bool = False,
    quality: str = "auto",
    reference: Path | None = None,
    expression_reference: Path | None = None,
) -> Path | None:
    """Generate a cover image and save it to the images dir.

    Args:
        prompt: Image description (in English). In comic mode it already carries the
                subject and scene from the s_comic_scene stage.
        slug: Article slug for filename.
        comic_mode: If True, the prompt is complete; otherwise the wellness style prefix
                is prepended.
        quality: gpt-image-1 quality, OpenAI backend only — "auto" (~$0.063), "low"
                (~$0.016), "high" (~$0.25). Codex has no equivalent knob.
        reference: Vita's turnaround sheet, when she is in the frame. Codex backend only.
        expression_reference: her expression sheet, when the face reads. Codex backend only.

    Returns:
        Path to saved image, or None on failure.
    """
    full_prompt = prompt if comic_mode else f"{_load_style_prefix()}{prompt}"

    if IMAGE_PROVIDER == "codex":
        return _generate_via_codex(full_prompt, slug, reference, expression_reference)
    return _generate_via_openai(full_prompt, slug, quality)


def _generate_via_codex(
    full_prompt: str,
    slug: str,
    reference: Path | None,
    expression_reference: Path | None = None,
) -> Path | None:
    """Render through the Codex CLI, which bills against the ChatGPT subscription."""
    from pipeline import codex_image

    try:
        raw = codex_image.render(
            full_prompt,
            reference=reference,
            expression_reference=expression_reference,
        )
    except codex_image.CodexImageError as e:
        logger.error("Codex image generation failed: %s", e)
        return None

    out_path = _save_web_jpeg(raw.read_bytes(), slug)
    raw.unlink(missing_ok=True)
    return out_path


def _save_web_jpeg(img_bytes: bytes, slug: str) -> Path:
    """Convert whatever the backend produced into the web/Telegram cover.

    JPEG at 1200px wide: Telegram rejects photo previews over 5 MB, and the site never
    displays a cover larger than this.
    """
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = IMAGES_DIR / f"{slug}.jpg"

    try:
        import io

        from PIL import Image

        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        if img.width > 1200:
            ratio = 1200 / img.width
            img = img.resize((1200, int(img.height * ratio)), Image.LANCZOS)
        img.save(out_path, "JPEG", quality=85, optimize=True)
    except ImportError:
        out_path = IMAGES_DIR / f"{slug}.png"
        out_path.write_bytes(img_bytes)

    logger.info("Image saved: %s (%d KB)", out_path, out_path.stat().st_size // 1024)
    return out_path


def _generate_via_openai(full_prompt: str, slug: str, quality: str) -> Path | None:
    """Render through api.openai.com. Needs credits on the account."""
    if not OPENAI_API_KEY:
        logger.warning("No OPENAI_API_KEY — skipping image generation")
        return None

    try:
        resp = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-image-1",
                "prompt": full_prompt,
                "n": 1,
                "size": "1536x1024",  # landscape for article headers
                "quality": quality,
            },
            timeout=180,
        )
        resp.raise_for_status()
        data = resp.json()

        # gpt-image-1 returns base64
        image_data = data["data"][0]
        if "b64_json" in image_data:
            img_bytes = base64.b64decode(image_data["b64_json"])
        elif "url" in image_data:
            img_resp = requests.get(image_data["url"], timeout=60)
            img_resp.raise_for_status()
            img_bytes = img_resp.content
        else:
            logger.error("No image data in response")
            return None

        return _save_web_jpeg(img_bytes, slug)

    except requests.exceptions.HTTPError as e:
        logger.error("OpenAI API error: %s — %s", e.response.status_code,
                     e.response.text[:300] if e.response else "")
        return None
    except Exception:
        logger.error("Image generation failed", exc_info=True)
        return None
