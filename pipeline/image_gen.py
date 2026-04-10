"""Image generation: health/wellness illustrations via OpenAI gpt-image-1."""

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

_STYLE_FILE = Path(__file__).resolve().parent / "prompts" / "templates" / "_partials" / "image_style.txt"

# Default style for health/wellness illustrations
_DEFAULT_STYLE = (
    "Clean, modern health and wellness illustration style. "
    "Soft natural colors (greens, blues, warm earth tones). "
    "Minimalist flat design with gentle gradients. "
    "Positive, calming mood. No text overlays. "
    "Professional medical/health publication quality. "
)


def _load_style_prefix() -> str:
    """Load image style prefix from editable file, or use default."""
    if _STYLE_FILE.exists():
        return _STYLE_FILE.read_text(encoding="utf-8").strip() + " "
    return _DEFAULT_STYLE


def generate_image(prompt: str, slug: str) -> Path | None:
    """Generate a health/wellness illustration and save to images dir.

    Args:
        prompt: Image description (in English).
        slug: Article slug for filename.

    Returns:
        Path to saved image, or None on failure.
    """
    if not OPENAI_API_KEY:
        logger.warning("No OPENAI_API_KEY — skipping image generation")
        return None

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
