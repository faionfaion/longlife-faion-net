"""Image generation: comic-style illustrations via OpenAI gpt-image-1.

Generates character-consistent comic panels featuring Vita — the LongLife Media mascot.
Falls back to generic wellness illustration style when no comic scene is provided.
"""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path

import requests

from pipeline.config import IMAGES_DIR

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get(
    "OPENAI_API_KEY",
    "",
)

_PARTIALS_DIR = Path(__file__).resolve().parent / "prompts" / "templates" / "_partials"
_STYLE_FILE = _PARTIALS_DIR / "image_style.txt"
_COMIC_STYLE_FILE = _PARTIALS_DIR / "comic_style.txt"
_CHARACTER_SHEET_FILE = _PARTIALS_DIR / "character_sheet.md"

# Default style for health/wellness illustrations (fallback)
_DEFAULT_STYLE = (
    "Clean, modern health and wellness illustration style. "
    "Soft natural colors (greens, blues, warm earth tones). "
    "Minimalist flat design with gentle gradients. "
    "Positive, calming mood. No text overlays. "
    "Professional medical/health publication quality. "
)

# Character physical description for prompt consistency
_CHARACTER_PHYSICAL = (
    "Tall athletic muscular woman (178cm), long wavy blonde hair past shoulders "
    "parted on the left, bright green eyes, defined muscles but feminine build, "
    "sun-kissed skin. Small green leaf tattoo on right shoulder. "
    "Black fitness smartwatch on left wrist."
)


def _load_style_prefix() -> str:
    """Load image style prefix from editable file, or use default."""
    if _STYLE_FILE.exists():
        return _STYLE_FILE.read_text(encoding="utf-8").strip() + " "
    return _DEFAULT_STYLE


def _load_comic_style() -> str:
    """Load comic art style from file."""
    if _COMIC_STYLE_FILE.exists():
        return _COMIC_STYLE_FILE.read_text(encoding="utf-8").strip()
    return "Clean-line comic art panel, bold black outlines, cel-shading, vibrant colors."


def _load_character_sheet() -> str:
    """Load character model sheet for reference."""
    if _CHARACTER_SHEET_FILE.exists():
        return _CHARACTER_SHEET_FILE.read_text(encoding="utf-8").strip()
    return ""


def build_comic_prompt(scene_prompt: str) -> str:
    """Build a full image prompt with character consistency enforced.

    Prepends comic style + character physical description to ensure
    the generated image matches Vita's model sheet.

    Args:
        scene_prompt: Scene description from s_comic_scene stage.

    Returns:
        Full prompt with style + character + scene.
    """
    comic_style = _load_comic_style()
    return (
        f"{comic_style} Single panel composition. "
        f"Character: {_CHARACTER_PHYSICAL} "
        f"{scene_prompt}"
    )


def generate_image(prompt: str, slug: str, comic_mode: bool = False) -> Path | None:
    """Generate an illustration and save to images dir.

    Args:
        prompt: Image description (in English). For comic mode, should already
                include character description from s_comic_scene stage.
        slug: Article slug for filename.
        comic_mode: If True, use comic style prefix instead of wellness style.

    Returns:
        Path to saved image, or None on failure.
    """
    if not OPENAI_API_KEY:
        logger.warning("No OPENAI_API_KEY — skipping image generation")
        return None

    if comic_mode:
        # Comic mode: prompt already contains character + scene from s_comic_scene
        full_prompt = prompt
    else:
        full_prompt = f"{_load_style_prefix()}{prompt}"

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
            },
            timeout=120,
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

        IMAGES_DIR.mkdir(parents=True, exist_ok=True)

        # Convert to JPEG for smaller file size (TG needs < 5MB for previews)
        out_path = IMAGES_DIR / f"{slug}.jpg"
        try:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(img_bytes))
            img = img.convert("RGB")
            # Resize if too large (max 1200px wide for web)
            if img.width > 1200:
                ratio = 1200 / img.width
                img = img.resize((1200, int(img.height * ratio)), Image.LANCZOS)
            img.save(out_path, "JPEG", quality=85, optimize=True)
        except ImportError:
            # Fallback: save as PNG if Pillow not installed
            out_path = IMAGES_DIR / f"{slug}.png"
            out_path.write_bytes(img_bytes)

        logger.info("Image saved: %s (%d KB)", out_path, out_path.stat().st_size // 1024)
        return out_path

    except requests.exceptions.HTTPError as e:
        logger.error("OpenAI API error: %s — %s", e.response.status_code,
                     e.response.text[:300] if e.response else "")
        return None
    except Exception:
        logger.error("Image generation failed", exc_info=True)
        return None
